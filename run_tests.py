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
import json, shuntil

def main()

    success = False

    #TODO figure out num loops

    for i in range(num_loops)
        #TODO run gemini and get input -> json: fixed code, patch, why (string), line nums(int)
        with open("input.json") as f:
        input_data = json.load(f)

        patch = input_data["patch"]
        why = input_data["why"]

        tests = input_data["tests"]#TODO change? 
        target_file = input_data["target_file"], num loops(int) #TODO change? 

        #TODO make fixed code -> executable
        #TODO run tests

        if #TODO test passes
            success = True
            break


    if success
        print(Fore.green + "Generated fix successful!")
        print()
        print("Suggested patch: ")
        width = shutil.get_terminal_size().columns
        print(f"line {start_line}" + "-" * (width - 8))
        print(patch)
        print(f"line {end_line}" + "-" * (width - 8))
        print()
        print("Patch description: ")
        print(why)

    else:
        print(Fore.red + "All generated patches failed :(")

    again = input("Run again? [y/n]: ")

    if again.lower().startswith("y"):
        main()
    else:
        sys.exit()