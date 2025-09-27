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

def tester(num_loops, manual, file_path): # int num loops, bool manual y/n, file_path dir
    success = False

    #! SAVE ORIGINAL CODE FOR FOLLOWING INPUTS
    with open("combined.json") as f:
            input_data = json.load(f)
    
    original_code_path = input_data["original_code_path"]
    context_files = input_data["context_files"]

    #! RUN TESTS
    for i in range(num_loops):
        if i > 0:
            #TODO run gemini (args: file path) and get new input
            pass #TODO delete
        
        with open("combined.json") as f:
            input_data = json.load(f)
        
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

        #TODO make copy of original

        #TODO apply fixed_code
        #TODO run tests, get result
        #TODO if manual -> print in terminal, if not

        if result.returncode == 0: # all tests passed
            success = True
            break




    #!PRINTING
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