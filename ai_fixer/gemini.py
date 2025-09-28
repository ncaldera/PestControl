import os
import json
import re
import subprocess
from pathlib import Path
from typing import List, Union, Dict, Any, Tuple
from dotenv import load_dotenv
import google.generativeai as genai

# ----------------------------
# 0) CONFIG & PLACEHOLDERS
# ----------------------------


# NOTE: may need to rearrange this, this is js reading in at the START of the program

code_file_path = Path("./code.txt") # PLACEHOLDER CONTENT
CODE_SNIPPET = code_file_path.read_text(encoding="utf-8").strip()

# array of strings, each string is file path
repo_file_paths = [
    "utils/math_helpers.py",
    "README.md"
    # PLACEHOLDER CONTENT
]
# Build REPO_FILES as a dict {path: content}
REPO_FILES = {}
for fp in repo_file_paths:
    path = Path(fp)
    if path.exists():
        REPO_FILES[str(path)] = path.read_text(encoding="utf-8")
    else:
        REPO_FILES[str(path)] = ""  # or handle missing files differently

# array of strings, each string is file path
# Where your pytest tests live (files or directories).
pytest_file_paths = [
    "tests/test_add.py",
    "tests/test_math.py"
    # PLACEHOLDER CONTENT
]
PYTEST_TARGETS = pytest_file_paths

descript_file_path = Path("bug_reports/description.txt") # PLACEHOLDER CONTENT
DESCRIPTION = descript_file_path.read_text(encoding="utf-8").strip()

FIRST_RUN = True  # (kept: not used here yet, but preserved for future loop logic)

# ----------------------------
# 1) GEMINI SETUP
# ----------------------------
# NOTE: model is created once and reused.
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

def condense_pytest_output(text: str, tail_lines: int = 120) -> str:
    # Keep the prompt compact: include last N lines of the pytest output but show top traceback.
    lines = text.splitlines()
    return "\n".join(lines[-tail_lines:]) if len(lines) > tail_lines else text

# ----------------------------
# 3) PROMPT CONSTRUCTION (pytest-based)
# ----------------------------
def build_prompt_for_pytest(
    code_snippet: str,
    pytest_output_snippet: str,
    repo_files: dict[str, str],
    description: str | None,
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
- A user-provided description of what they think the bug is or what's happening
- A condensed pytest failure report from the current run,
- A small selection of other repository files for context.

Your job:
1) Produce a corrected version of the buggy code so that **pytest passes**.
2) Explain succinctly what was wrong and why your fix is correct.
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

# ----------------------------
# ORCHESTRATOR
# ----------------------------
def running_gemini(original_code_path, context_files, description_path, test_files):
    """
    Orchestrate the full step:
      - read inputs,
      - run pytest & condense,
      - build prompt,
      - call Gemini,
      - parse JSON,
      - write fixed_code.txt, why.txt, patch.txt, code.txt,
      - write combined_patch.json,
      - return combined JSON.
    """
    # --- Read inputs (use args so this function can be reused; placeholders remain at top) ---
    code_snippet = Path(original_code_path).read_text(encoding="utf-8").strip()
    description  = Path(description_path).read_text(encoding="utf-8").strip() if Path(description_path).exists() else ""
    repo_files   = {str(Path(fp)): (Path(fp).read_text(encoding="utf-8") if Path(fp).exists() else "") for fp in (context_files or [])}

    # Normalize pytest targets
    if isinstance(test_files, str):
        pytest_targets = [test_files]
    else:
        pytest_targets = list(test_files or [])

    # --- Run pytest & condense using your functions ---
    exit_code, PYTEST_OUTPUT = run_pytest(pytest_targets)
    PYTEST_OUTPUT_SNIPPET = condense_pytest_output(PYTEST_OUTPUT, tail_lines=160)

    # --- Build prompt using your function ---
    prompt = build_prompt_for_pytest(
        code_snippet=code_snippet,
        pytest_output_snippet=PYTEST_OUTPUT_SNIPPET,
        repo_files=repo_files,
        description=description,
        pytest_targets=pytest_targets,
        exit_code=exit_code,
    )

    # --- Call Gemini (kept: your model instance) ---
    generation_config = {
        "temperature": 0.0,
        "response_mime_type": "application/json",
    }
    response = model.generate_content(prompt, generation_config=generation_config)
    raw_text = response.text or ""

    # --- Parse model JSON using your extractor ---
    data = extract_json(raw_text)
    for key in ["SuggestedFixedCode", "ExplanationOfFix", "LineNumberRangesToEdit"]:
        if key not in data:
            raise ValueError(f"JSON missing required key: {key}")

    fixed_code  = data["SuggestedFixedCode"]
    explanation = data["ExplanationOfFix"]
    ranges      = data["LineNumberRangesToEdit"]  # list[{"start": int, "end": int, "reason": str}]

    # ----------------------------
    # 6) WRITE FILES: fixed_code.txt, why.txt, patch.txt
    # ----------------------------
    out_dir = Path(".")
    fixed_code_path     = out_dir / "fixed_code.txt"
    why_path            = out_dir / "why.txt"
    patch_path          = out_dir / "patch.txt"
    original_copy_path  = out_dir / "code.txt"  # local copy of original snippet (for downstream tools)

    original_copy_path.write_text(code_snippet, encoding="utf-8")
    fixed_code_path.write_text(fixed_code, encoding="utf-8")
    why_path.write_text(explanation, encoding="utf-8")

    # Write patch.txt (all ranges + why). Kept your requested flat format.
    lines = []
    for r in (ranges or []):
        lines.append(f"start line: {r.get('start', '')}")
        lines.append(f"end line: {r.get('end', '')}")
    # end with the why (explanation of the code fix)
    lines.append(f"why: {explanation.strip()}")

    patch_contents = "\n".join(lines)
    patch_path.write_text(patch_contents, encoding="utf-8")

    print("✅ Wrote:")
    print(f" - {fixed_code_path.resolve()}")
    print(f" - {why_path.resolve()}")
    print(f" - {patch_path.resolve()}")

    # ----------------------------
    # 7) COMBINE INTO JSON (paths only)
    # ----------------------------
    combined = { # what to send to the test runner (maya)
        "original_code_path": str(original_copy_path),
        "fixed_code_path": str(fixed_code_path),
        "patch_path": str(patch_path),
        "why_path": str(why_path),
        "context_files": list(repo_files.keys()),   # repo context paths only
        "pytest_test_files": pytest_targets          # the test files you passed to pytest
    }

    combined_json_path = out_dir / "combined_patch.json"
    with combined_json_path.open("w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2)

    print("✅ Wrote combined JSON to", combined_json_path.resolve())
    return combined

""" 
Sample Usage:
running_gemini(
        original_code_path=code_file_path,
        context_files=repo_file_paths,
        description_path=descript_file_path,
        test_files=pytest_file_paths,
    ) """
