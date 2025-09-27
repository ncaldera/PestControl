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
import json, shuntil, subprocess, os

def main():

    for i in range(num_loops):
        #TODO run gemini and get input
        
        with open("combined.json") as f:
            input_data = json.load(f)


        original_code_path = input_data["original_code_path"] #for next input
        patch = input_data["patch_path"] #why, line nums, num trys, context files

        tests = input_data["tests"]

        patched_code = input_data["fixed_code_path"] # just fixed code
        path_to_txt = Path(patched_code)
        patched_code_py = path_to_txt.with_suffix(".py") #path to executable 
        
        # copy text from txt to executabe
        with open(path_to_txt, "r", encoding="utf-8") as f:
            code = f.read()

        with open(patched_code_py, "w", encoding="utf-8") as f:
            f.write(code)

        # run tests
        workdir = str(patched_code_py.parent)
        result = subprocess.run(["pytest"] + tests, cwd = workdir)

        if result.returncode == 0 # all tests passed
            success = True
            break




    success = False

    #!FIRST ITERATION
    with open("combined.json") as f:
            input_data = json.load(f)
    
    original_code_path = input_data["original_code_path"] #for next input
    context_files = input_data["context_files"]

    

    #!NEXT ITERATIONS (LOOP)

    for i in range(num_loops):
        #TODO run gemini and get new input
        
        with open("combined.json") as f:
            input_data = json.load(f)




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
        print(Fore.RED + "All generated patches failed :(")

    again = input(Back.WHITE + "Run again? [y/n]: ")
    if again.lower().startswith("y"):
        main()
    else:
        sys.exit()