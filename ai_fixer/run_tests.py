from colorama import Fore, Back, Style, init
import json, shutil, subprocess, os, tempfile, sys
from pathlib import Path
from ai_fixer.gemini import running_gemini
import json
from datetime import datetime

#! takes gemini input, runs tests, delivers correct output
def tester(num_loops, manual, folder_path, skip_tests): # int num loops, bool manual y/n, file_path dir
    success = False

    #! opening gemini input, first call
    original_code_path = os.path.join(folder_path, "code_with_error.txt")
    context_files_path = os.path.join(folder_path, "context_files.txt")
    description_path = os.path.join(folder_path, "description_of_the_bug.txt")
    test_cases_path = os.path.join(folder_path, "test_cases.txt")
    original_file = os.path.join(folder_path, "code_with_error_path.txt")

    with open(test_cases_path, "r", encoding="utf-8") as f:
        test_cases = [line.strip() for line in f if line.strip()]

    with open(context_files_path, "r", encoding="utf-8") as f:
        context_files = [line.strip() for line in f if line.strip()]

    with open(original_file, "r", encoding="utf-8") as f:
        original_file_path = f.readline().strip()

    combined_json = running_gemini(original_code_path, context_files, description_path, test_cases)
    input_data = combined_json

    #! begin looping the patch iterations
    num_runs = 1
    for i in range(num_loops):
        #! get new gemini input on following runs
        if i > 0:
            combined_json = running_gemini(original_code_path, context_files, description_path, test_cases)
            input_data = combined_json
        
        tests = input_data["pytest_test_files"]
        fixed_code = input_data["fixed_code_path"] #whole fixed code
        patch_path = input_data["patch_path"]

        patch_data = {}
        with open(patch_path, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    key, value = line.split(":", 1)
                    patch_data[key.strip()] = value.strip()

        raw_start = patch_data.get("start_line", patch_data.get("start_line"))
        raw_end   = patch_data.get("end_line",   patch_data.get("end_line"))

        if raw_start is None or raw_end is None:
            raise ValueError(f"patch.txt missing start/end lines. Got keys: {list(patch_data.keys())}")

        start_line = int(raw_start) - 1  # 0-based
        end_line   = int(raw_end)   - 1
        why = patch_data.get("why", "")

        #! if not given tests to run code with, suggest patch anyways
        try:
            result = subprocess.run(
                ["git", "diff", "--no-index", orig_file, fixed_code],
                capture_output=True,
                text=True
            )
            patch_text = result.stdout
        except Exception:
            patch_text = None

        if not patch_text:
            patch_text = Path(fixed_code).read_text(encoding="utf-8") if Path(fixed_code).exists() else ""
            
        if skip_tests:
            if manual:
                print(f"{Fore.YELLOW} No test cases provided. Running in patch-only mode.{Style.RESET_ALL}")

            break

        #! save original file, temporaily overwrite with fixed code to run tests, restore
        with open(fixed_code, "r", encoding="utf-8") as f:
            fixed_code_out = f.read()
        
        orig_file = original_file_path # relative path from repo root

        shutil.copy(orig_file, orig_file + ".bak")
        with open(orig_file, "w", encoding="utf-8") as f:
            f.write(fixed_code_out)

        result = subprocess.run(
            ["pytest", *tests, "--tb=short"],
            capture_output = True,
            text = True)
        shutil.move(orig_file + ".bak", orig_file)

        #! if the test suite passes, success -> go to output
        if result.returncode == 0:
            success = True
            break
        pass
        num_runs += 1

    #! output files: success or fail, tested num patches, patch contents, original code, fixed code, and why buggy
    output_path = os.path.basename(folder_path) + ".txt"

    patch_text = ""
    with open(fixed_code, "r", encoding="utf-8") as f:
        patch_text = f.read()
    patch_text = Path(fixed_code).read_text(encoding="utf-8")

    report = {
        "original_file": orig_file,                     # just path
        "fixed_file": fixed_code if Path(fixed_code).exists() else "",
        "status": "Success" if success else ("Skipped tests" if skip_tests else "Fail"),
        "start_line": start_line,
        "why": why,
        "patch": patch_text,
        "timestamp": datetime.now().isoformat()
    }

    with open(output_path, "a", encoding="utf-8") as f:
        f.write("=== REPORT START ===\n")
        f.write(f"Original: {report['original_file']}\n")
        f.write(f"Fixed: {report['fixed_file']}\n")
        f.write(f"Status: {report['status']}\n")
        f.write(f"Line: {report['start_line']}\n")
        f.write(f"Why: {report['why']}\n")
        f.write("Patch:\n")
        f.write(f"{report['patch']}\n")
        f.write(f"Timestamp: {report['timestamp']}\n")
        f.write("=== REPORT END ===\n\n")

    #! prints to terminal if manual selected
    if manual:
        if success: 
            print(Fore.GREEN + Style.BRIGHT + "Generated fix successful!" + Style.RESET_ALL)
            print(Fore.YELLOW + f"Tested {num_runs} patches." + Style.RESET_ALL)
            print(Fore.CYAN + Style.BRIGHT + "Suggested patch:" + Style.RESET_ALL)
            width = shutil.get_terminal_size().columns
            print(Fore.CYAN + f"line {start_line}" + "-" * (width - 8) + Style.RESET_ALL + "\n")
            print(Fore.LIGHTCYAN_EX + patch_text + Style.RESET_ALL + "\n")
            print(Fore.CYAN + "-" * (width - 6) + Style.RESET_ALL + "\n")
            print(Fore.MAGENTA + "Original buggy code description:" + Style.RESET_ALL)
            print(why + "\n")
            print(Fore.BLUE + Style.BRIGHT + "Good luck with your fix!" + Style.RESET_ALL)

        else: 
            print(Fore.RED + Style.BRIGHT + "All generated fixes failed. :(" + Style.RESET_ALL)
            print(Fore.YELLOW + f"Tested {num_runs} patches." + Style.RESET_ALL)
            
    return output_path
