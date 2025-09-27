from colorama import Fore, Back, Style, init

# Initialize colorama
init(autoreset=True)

print("=== Foreground Colors ===")
print(Fore.BLACK   + "Black")
print(Fore.RED     + "Red")
print(Fore.GREEN   + "Green")
print(Fore.YELLOW  + "Yellow")
print(Fore.BLUE    + "Blue")
print(Fore.MAGENTA + "Magenta")
print(Fore.CYAN    + "Cyan")
print(Fore.WHITE   + "White")

print("\n=== Background Colors ===")
print(Back.RED     + "Red background")
print(Back.GREEN   + "Green background")
print(Back.YELLOW  + "Yellow background")
print(Back.BLUE    + "Blue background")
print(Back.MAGENTA + "Magenta background")
print(Back.CYAN    + "Cyan background")
print(Back.WHITE   + "White background")

print("\n=== Text Styles ===")
print(Style.DIM       + "Dim text")
print(Style.NORMAL    + "Normal text")
print(Style.BRIGHT    + "Bright (bold) text")
print(Style.RESET_ALL + "Back to default")

