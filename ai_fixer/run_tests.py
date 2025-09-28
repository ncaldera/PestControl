'''
input: all .txt
- patch
- why (for output, why we applied the patch we did)  
- line nums patch starts and ends at
- num loops (if not specified, default 4)

- original code 
- test files 

loop: 
1. copy original code
2. apply patch (exchange buggy code with patch) 
3. run tests
4. if passes -> output
   if fails -> loop - call gemini again


output: in terminal
- if successful: suggested patch, why works
- if unsuccessful: failure message

run again option? [did it work y/n -> rerun prompt]

'''
from colorama import Fore, Back, Style, init
import json, shutil, subprocess, os, tempfile, sys
from pathlib import Path
from ai_fixer.gemini import running_gemini
import json

#! helper functions
def create__copy(path):
    fd, temp_path = tempfile.mkstemp(suffix='.py')  # unique temp file
    os.close(fd)  # close file descriptor
    shutil.copy2(path, temp_path)
    return temp_path

def apply_patch(temp_file_path, fixed_code_path, start, end):
    # read original into a list of lines
    with open(temp_file_path, "r", encoding="utf-8") as f:
        original_lines = f.readlines()

    # read fixed code as lines (preserve newlines)
    with open(fixed_code_path, "r", encoding="utf-8") as f:
        fixed_lines = f.read().splitlines(keepends=True)

    # splice: replace [start:end] with fixed_lines
    original_lines[start:end] = fixed_lines

    with open(temp_file_path, "w", encoding="utf-8") as f:
        f.writelines(original_lines)

def file(success, num_runs, why, start_line, end_line, patch_contents, skip):
    output_path = "output.txt"

    with open(output_path, "a", encoding="utf-8") as f:
        if success: 
            if skip:
                f.write(f"No test cases provided. Running in patch-only mode.")
            else: 
                f.write(f'''Generated fix successful!
                    Tested {num_runs} patches.''')

            f.write("Suggested patch:\n")
            width = shutil.get_terminal_size().columns
            f.write(f"line {start_line}" + "-" * (width - 8) + "\n")
            f.write(f"{patch_contents}\n")
            f.write(f"line {end_line}" + "-" * (width - 8) + "\n")
            f.write(f"Original buggy code description:\n{why}\n")
            f.write("Good luck with your fix!")

        else: 
            f.write(f'''All generated fixes failed. 
                    Tested {num_runs - 1} patches.''')
        
    return output_path

#! main func
def tester(num_loops, manual, folder_path, skip_tests): # int num loops, bool manual y/n, file_path dir
    success = False

    #! saving original code path, first gemini run
    original_code_path = os.path.join(folder_path, "code_with_error.txt")
    context_files_path = os.path.join(folder_path, "context_files.txt")
    description_path = os.path.join(folder_path, "description_of_the_bug.txt")
    test_cases_path = os.path.join(folder_path, "test_cases.txt")

    with open(test_cases_path, "r", encoding="utf-8") as f:
        test_cases = [line.strip() for line in f if line.strip()]
    print(f"[DEBUG] Test cases: {test_cases}")

    with open(context_files_path, "r", encoding="utf-8") as f:
        context_files = [line.strip() for line in f if line.strip()]
    print(f"[DEBUG] Context files: {context_files}")

    combined_json = running_gemini(original_code_path, context_files, description_path, test_cases)
    print(f"[DEBUG] Gemini output: {json.dumps(combined_json, indent=2)}")
    input_data = combined_json

    num_runs = 1
    for i in range(num_loops):
        if i > 0:
            combined_json = running_gemini(original_code_path, context_files, description_path, test_cases)
            input_data = combined_json
        
        tests = input_data["pytest_test_files"]
        fixed_code = input_data["fixed_code_path"] # just fixed code snippet
        patch_path = input_data["patch_path"]

        patch_data = {}
        with open(patch_path, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    key, value = line.split(":", 1)
                    patch_data[key.strip()] = value.strip()
        print(f"[DEBUG] Patch data: {patch_data}")

        raw_start = patch_data.get("start_line", patch_data.get("start_line"))
        raw_end   = patch_data.get("end_line",   patch_data.get("end_line"))

        if raw_start is None or raw_end is None:
            raise ValueError(f"patch.txt missing start/end lines. Got keys: {list(patch_data.keys())}")

        start_line = int(raw_start) - 1  # 0-based
        end_line   = int(raw_end)   - 1
        why = patch_data.get("why", "")

        print(f"[DEBUG] Applying patch: start_line={start_line}, end_line={end_line}")
        temp_fixed_code = create__copy(original_code_path)
        print(f"[DEBUG] Temp fixed code path: {temp_fixed_code}")

        apply_patch(temp_fixed_code, fixed_code, start_line, end_line)
        with open(temp_fixed_code, "r", encoding="utf-8") as f:
            temp_contents = f.read()
        print(f"[DEBUG] Applied patch to temp file: {temp_fixed_code}\n{temp_contents}")

        if skip_tests:
            if manual:
                print(f"{Fore.YELLOW} No test cases provided. Running in patch-only mode.{Style.RESET_ALL}")

            patch_contents = ""
            with open(fixed_code, "r", encoding="utf-8") as f:
                patch_contents = f.read()
            patch_contents = Path(fixed_code).read_text(encoding="utf-8")
            return file(success, 1, why, start_line, end_line, patch_contents, skip_tests)


        try:
            sys.path.insert(0, os.path.dirname(temp_fixed_code))
            print(f"[DEBUG] sys.path: {sys.path}")
            print(f"[DEBUG] Running pytest with args: ['pytest', *tests, '--tb=short']")
            result = subprocess.run(
                ["pytest", *tests, "--tb=short"],
                capture_output = True,
                text = True)
            print(f"[DEBUG] Pytest stdout:\n{result.stdout}")
            print(f"[DEBUG] Pytest stderr:\n{result.stderr}")
            print(f"[DEBUG] Pytest returncode: {result.returncode}")

            if result.returncode == 0: # all tests passed
                success = True
                break
            pass

        finally:
            print(f"[DEBUG] Removing temp file: {temp_fixed_code}")
            os.remove(temp_fixed_code)
            num_runs += 1

    with open(fixed_code, "r", encoding="utf-8") as f:
            patch_contents = f.read()
    
    if manual:
        if success: 
            print(f'''{Fore.GREEN}Generated fix successful!{Style.RESET_ALL}
                    Tested {num_runs} patches.
                    
                    Suggested patch:''')
            width = shutil.get_terminal_size().columns
            print(Fore.CYAN + f"line {start_line}" + "-" * (width - 8) + "\n")
            print(f"{patch_contents}\n")
            print(Fore.CYAN + f"line {end_line}" + "-" * (width - 8) + "\n")
            print(f"Original buggy code description:\n{why}\n")
            print(Fore.MAGENTA + "Good luck with your fix!")

        else: 
            print(f'''{Fore.RED}All generated fixes failed.{Style.RESET_ALL} 
                    Tested {num_runs - 1} patches.''')
    return file(success, num_runs, why, start_line, end_line, patch_contents, skip_tests)
