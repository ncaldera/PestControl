import os
import glob
import yaml
import shutil
from bug_report_extractor.bug_report_parser import extract_bug_report
from ai_fixer.run_tests import tester

CONFIG_FILE = "config.yaml"
BUG_REPORTS_DIR = "bug_reports"
PROPOSED_FIXES_DIR = "proposed_fixes"

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return yaml.safe_load(f)

def process_bug_report(file_path, config):
    print(f"📄 Processing bug report: {file_path}")
    
    extracted_dir = extract_bug_report(file_path)

    # Safety checks: decide how to run depending on fields
    test_cases_path = os.path.join(extracted_dir, "test_cases.txt")
    code_with_error_path = os.path.join(extracted_dir, "code_with_error.txt")

    # Load contents
    with open(test_cases_path, "r") as f:
        tests = f.read().strip()
    with open(code_with_error_path, "r") as f:
        code = f.read().strip()

    if not code or code.startswith("# No code"):
        print("❌ No code snippet provided. Cannot run repair agent.")
        return

    skip_tests = not tests or tests.startswith("# No tests")
    if skip_tests:
        print("⚠️ No test cases provided. Running in patch-only mode.")

    patch_path = tester(
        extracted_dir,
        manual= config.get("mode", "manual") == "manual",
        retries=config.get("max_retries", 3),
        skip_tests=skip_tests
    )

    #Save patch in proposed_fixes/
    os.makedirs(PROPOSED_FIXES_DIR, exist_ok=True)
    dest = os.path.join(PROPOSED_FIXES_DIR, os.path.basename(patch_path))
    shutil.move(patch_path, dest)

    # Remove original JSON so it's not processed again
    os.remove(file_path)
    print(f"✅ Finished {file_path}. Patch saved to {dest}")

def main():
    config = load_config()
    mode = config.get("mode", "manual")

    bug_reports = glob.glob(os.path.join(BUG_REPORTS_DIR, "*.json"))

    if not bug_reports:
        print("No bug reports found.")
        return

    if mode == "manual":
        print("Manual mode. Run extractor + repair manually.")
        print(f"Available reports: {bug_reports}")
    else:
        # Process the first available JSON file
        process_bug_report(bug_reports[0], config)

if __name__ == "__main__":
    main()