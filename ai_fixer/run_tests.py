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
import json, shutil, subprocess, os, tempfile

def tester(num_loops, manual, folder_path): # int num loops, bool manual y/n, file_path dir
    success = False

    #! SAVE ORIGINAL CODE FOR FOLLOWING INPUTS
    original_code_path = os.path.join(folder_path, "code_with_error.txt")
    context_files_path = os.path.join(folder_path, "context_files.txt")
    description_path = os.path.join(folder_path, "description_of_the_bug.txt")
    test_cases_path = os.path.join(folder_path, "test_cases.txt")

    with open(test_cases_path, "r", encoding="utf-8") as f:
        test_cases = [line.strip() for line in f if line.strip()]
    
    with open(context_files_path, "r", encoding="utf-8") as f:
        context_files = [line.strip() for line in f if line.strip()]
    
    combined_json = running_gemini(original_code_path, context_files, description_path, test_cases_path)
    input_data = json.loads(combined_json)

    #! RUN TESTS
    for i in range(num_loops):
        if i > 0:
            combined_json = running_gemini(original_code_path, context_files, description_path, test_cases_path)
            input_data = json.loads(combined_json)
        
        tests = input_data["tests"]
        fixed_code = input_data["fixed_code_path"] # just fixed code
        patch_path = input_data["patch_path"]

        patch_data = {}
        with open(patch_path, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    key, value = line.split(":", 1)
                    patch_data[key.strip()] = value.strip()

        start_line = int(patch_data.get("start_line"))
        end_line = int(patch_data.get("end_line"))
        why = patch_data.get("why", "")

        temp_fixed_code = create__copy(original_code_path)

        apply_patch(temp_fixed_code, fixed_code, start_line, end_line)

        try:
            #TODO run tests, if tests pass -> success = True
            if result.returncode == 0: # all tests passed
                success = True
                break
            pass
        finally:
            os.remove(temp_fixed_code)
            

def create__copy(path):
    fd, temp_path = tempfile.mkstemp(suffix='.py')  # unique temp file
    os.close(fd)  # close file descriptor
    shutil.copy2(path, temp_path)
    return temp_path

def apply_path()



'''
    #!PRINTING FIX!!! - if need be put in tester func
    if success:
        print(Fore.GREEN + "Generated fix successful!")

        print()
        #TODO parse patch and break up in order to print better

        print(Style.BRIGHT + "Suggested patch: ")
        width = shutil.get_terminal_size().columns
        print(Style.RESET_ALL + f"line {start_line}" + "-" * (width - 8))
        print(Fore.CYAN + patch)
        print(f"line {end_line}" + "-" * (width - 8))

        print()

        print(Style.BRIGHT + "Patch description: ")
        print(Style.RESET_ALL + why)
    else:
        print(Fore.RED + "All generated patches failed :")

    again = input(Back.WHITE + "Run again? [y/n]: ")
    if again.lower().startswith("y"):
        tester()
'''