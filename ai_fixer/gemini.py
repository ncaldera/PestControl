import os
import json
import re
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# ----------------------------
# 0) CONFIG & PLACEHOLDERS
# ----------------------------
# You will replace these with real values pulled from your other method.
CODE_SNIPPET = """
def add(a, b):
    # BUG: returns a - b
    return a - b
""".strip()

# Overall repo files. Represent as "path => content". Keep short; large repos should be summarized upstream.
REPO_FILES = {
    "utils/math_helpers.py": "def clamp(x, lo, hi):\n    return min(max(x, lo), hi)\n",
    "README.md": "# Example project\n\nSimple demo.",
}

# Where your pytest tests live (files or directories).
# You can leave this empty to run default discovery.
PYTEST_TARGETS = ["tests"]  # e.g., ["tests/test_add.py"] or ["tests", "more_tests"]

DESCRIPTION = "All tests should pass. Currently some pytest tests fail with assertion errors."
NUM_TRIES = 4
WRONG_OUTPUT = ""  # optional free-form note; can be left empty

# ----------------------------
# 1) GEMINI SETUP
# ----------------------------
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("❌ No GEMINI_API_KEY found in .env file")

genai.configure(api_key=api_key)
MODEL_NAME = "gemini-2.5-flash"  # good balance for free tier
model = genai.GenerativeModel(MODEL_NAME)

# ----------------------------
# 2) PYTEST EXECUTION (get failure context)
# ----------------------------
def run_pytest(pytest_targets: list[str] | None = None, extra_args: list[str] | None = None) -> tuple[int, str]:
    """
    Run pytest and return (exit_code, combined_output).
    Writes a JUnit XML for structured parsing if you want later.
    """
    args = ["pytest", "-q", "--disable-warnings", "--maxfail=1", "--color=no", f"--junitxml=pytest_report.xml"]
    if extra_args:
        args.extend(extra_args)
    if pytest_targets:
        args.extend(pytest_targets)

    proc = subprocess.run(args, capture_output=True, text=True)
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return proc.returncode, output.strip()

exit_code, PYTEST_OUTPUT = run_pytest(PYTEST_TARGETS)

# Keep the prompt compact: include last N lines of the pytest output but show top traceback.
def condense_pytest_output(text: str, tail_lines: int = 120) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-tail_lines:]) if len(lines) > tail_lines else text

PYTEST_OUTPUT_SNIPPET = condense_pytest_output(PYTEST_OUTPUT, tail_lines=160)

# ----------------------------
# 3) PROMPT CONSTRUCTION (pytest-based)
# ----------------------------
def build_prompt_for_pytest(
    code_snippet: str,
    pytest_output_snippet: str,
    repo_files: dict[str, str],
    description: str | None,
    num_tries: int,
    pytest_targets: list[str] | None,
    exit_code: int,
) -> str:
    repo_blob = "\n".join(
        f"- PATH: {path}\n<FILE>\n{content}\n</FILE>"
        for path, content in (repo_files or {}).items()
    )

    return f"""
You are an automated code repair agent working with a Python project that uses pytest.
You will receive:
- The buggy code snippet (one focal file),
- A condensed pytest failure report from the current run,
- A small selection of other repository files for context.

Your job:
1) Produce a corrected version of the buggy code so that **pytest passes**.
2) Explain *succinctly* what was wrong and why your fix is correct.
3) Identify the line-number range(s) to edit in the ORIGINAL buggy snippet (1-based, inclusive).
4) Return JSON ONLY, using EXACTLY these keys:
   - "SuggestedFixedCode": string (the full fixed file contents)
   - "ExplanationOfFix": string (≤ 10 bullet points or a short paragraph)
   - "LineNumberRangesToEdit": array of objects, each with:
        {{"start": <int>, "end": <int>, "reason": <short string>}}

DO NOT include markdown fences, commentary, or any fields other than those keys.

===== CONTEXT START =====
[BUGGY_CODE_SNIPPET]
{code_snippet}
[/BUGGY_CODE_SNIPPET]

[PYTEST_TARGETS]
{', '.join(pytest_targets or ['<default discovery>'])}
[/PYTEST_TARGETS]

[PYTEST_EXIT_CODE]
{exit_code}
[/PYTEST_EXIT_CODE]

[PYTEST_FAILURE_REPORT_SNIPPET]
{pytest_output_snippet}
[/PYTEST_FAILURE_REPORT_SNIPPET]

[DESCRIPTION]
{description or ""}
[/DESCRIPTION]

[REPO_FILES]
{repo_blob}
[/REPO_FILES]

===== CONTEXT END =====
""".strip()

prompt = build_prompt_for_pytest(
    code_snippet=CODE_SNIPPET,
    pytest_output_snippet=PYTEST_OUTPUT_SNIPPET,
    repo_files=REPO_FILES,
    description=DESCRIPTION,
    wrong_output=WRONG_OUTPUT,
    num_tries=NUM_TRIES,
    pytest_targets=PYTEST_TARGETS,
    exit_code=exit_code,
)

# ----------------------------
# 4) CALL GEMINI FOR JSON
# ----------------------------
generation_config = {
    "temperature": 0.0,
    "response_mime_type": "application/json",
}
response = model.generate_content(prompt, generation_config=generation_config)
raw_text = response.text or ""

# ----------------------------
# 5) ROBUST JSON EXTRACTION
# ----------------------------
def extract_json(text: str) -> dict:
    def strict_load(t: str):
        return json.loads(t)
    try:
        return strict_load(text)
    except Exception:
        pass
    fence = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.S)
    if fence:
        return json.loads(fence.group(1))
    brace = re.search(r"(\{.*\})", text, flags=re.S)
    if brace:
        candidate = brace.group(1)
        candidate = candidate[: candidate.rfind("}") + 1]
        return json.loads(candidate)
    raise ValueError("Model did not return JSON or JSON could not be parsed.")

data = extract_json(raw_text)

for key in ["SuggestedFixedCode", "ExplanationOfFix", "LineNumberRangesToEdit"]:
    if key not in data:
        raise ValueError(f"JSON missing required key: {key}")

# ----------------------------
# 6) WRITE FILES: fixed_code.txt, why.txt, patch.txt
# ----------------------------
out_dir = Path(".")
fixed_code_path = out_dir / "fixed_code.txt"
why_path = out_dir / "why.txt"
patch_path = out_dir / "patch.txt"

fixed_code = data["SuggestedFixedCode"]
explanation = data["ExplanationOfFix"]
ranges = data["LineNumberRangesToEdit"]  # list[{"start": int, "end": int, "reason": str}]

fixed_code_path.write_text(fixed_code, encoding="utf-8")
why_path.write_text(explanation, encoding="utf-8")

def format_ranges(rs: list[dict]) -> str:
    if not isinstance(rs, list):
        return "[]"
    lines = []
    for r in rs:
        start = r.get("start")
        end = r.get("end")
        reason = r.get("reason", "")
        lines.append(f"- lines {start}–{end}: {reason}".rstrip())
    return "\n".join(lines) if lines else "[]"

patch_contents = f"""# Patch Summary
Attempts (max): {NUM_TRIES}

## Line Number Ranges To Edit
{format_ranges(ranges)}

## Why (LLM Explanation)
{explanation}

## Pytest Failure Context (before fix, condensed) idk if you want this btw
{PYTEST_OUTPUT_SNIPPET}
""".strip()

patch_path.write_text(patch_contents, encoding="utf-8")

print("✅ Wrote:")
print(f" - {fixed_code_path.resolve()}")
print(f" - {why_path.resolve()}")
print(f" - {patch_path.resolve()}")


# ----------------------------
# 7) COMBINE INTO JSON (paths only)
# ----------------------------
out_dir = Path("bug_reports")
out_dir.mkdir(parents=True, exist_ok=True)

fixed_code_path = out_dir / "fixed_code.txt"
patch_path = out_dir / "patch.txt"
original_code_path = out_dir / "code.txt"

# (You’d write CODE_SNIPPET into code.txt earlier in your pipeline)
original_code_path.write_text(CODE_SNIPPET, encoding="utf-8")

combined = { #what to send to the test runner (maya)
    "original_code_path": str(original_code_path),
    "fixed_code_path": str(fixed_code_path),
    "patch_path": str(patch_path),
    "why_path": str(why_path),
    "context_files": list(REPO_FILES.keys()),   # repo context paths only
    "pytest_test_files": PYTEST_TARGETS          # the test files you passed to pytest
}

combined_json_path = out_dir / "combined_patch.json"
with combined_json_path.open("w", encoding="utf-8") as f:
    json.dump(combined, f, indent=2)

print("✅ Wrote combined JSON to", combined_json_path.resolve())

