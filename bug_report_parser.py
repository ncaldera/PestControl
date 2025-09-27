import json
import re
from pathlib import Path

# Path to the downloaded JSON issue file
json_file = "bug_reports/issue_7.json"

# Output folder for text files
output_dir = Path("extracted_reports")
output_dir.mkdir(exist_ok=True)

# Load the JSON issue file
with open(json_file, "r", encoding="utf-8") as f:
    issue = json.load(f)

body = issue["body"]

# Define the fields we care about (order matters)
fields = [
    "Description of the bug",
    "Test cases",
    "Code with error",
    "Wrong output"
]

# Regex pattern to split by headings (### ...)
pattern = r"### (.+?)\n\n(.*?)(?=\n### |\Z)"
matches = re.findall(pattern, body, re.DOTALL)

# Save matched sections
for heading, content in matches:
    heading = heading.strip()
    if heading in fields:
        # Clean up content (remove placeholder if empty)
        text = content.strip()
        if text == "_No response_":
            text = ""
        
        # Save into a separate .txt file
        filename = output_dir / f"{heading.replace(' ', '_').lower()}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"✅ Saved {heading} -> {filename}")