import json
import re
from pathlib import Path
import os

def safe_write(out_dir: str, filename: str, content: str, default: str = ""):
    """Safely write content to file, using default if empty."""
    text = content.strip() if content else default
    path = Path(out_dir) / filename
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path

def extract_bug_report(json_file: str) -> str:
    """
    Extracts sections from a GitHub issue JSON into separate text files.
    
    Args:
        json_file (str): Path to the bug report JSON file.
    
    Returns:
        str: Path to the directory with extracted text files.
    """
    base_name = os.path.splitext(os.path.basename(json_file))[0]
    out_dir = os.path.join("extracted_reports", base_name)
    os.makedirs(out_dir, exist_ok=True)

    # Load the JSON
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    body = data.get("body", "")

    # Use regex to capture "### Heading" and its text
    sections = re.split(r"(?m)^### ", body)
    parsed = {}

    for section in sections:
        if not section.strip():
            continue
        lines = section.strip().splitlines()
        heading = lines[0].strip().lower().replace(" ", "_")
        content = "\n".join(lines[1:]).strip()
        parsed[heading] = content

    # Map headings to file names we care about
    mapping = {
        "description_of_the_bug": ("description.txt", "No description provided."),
        "test_cases": ("test_cases.txt", "# No tests provided"),
        "code_with_error": ("code_with_error.txt", "# No code snippet given"),
        "code_with_error_path": ("code_with_error_path.txt", "# No code snippet given"),
        "context_files": ("context_files.txt", "# No context files listed"),
    }

    for key, (filename, default) in mapping.items():
        content = parsed.get(key, "")
        safe_write(out_dir, filename, content, default)

    print(f"✅ Extracted fields saved to {out_dir}")
    return out_dir