# ai_fixer/gemini.py
import os
import json
import re
import subprocess
from pathlib import Path
from typing import List, Union, Dict, Any, Tuple
from dotenv import load_dotenv
import google.generativeai as genai


# ----------------------------
# Helpers (no I/O at import time)
# ----------------------------

def load_model(model_name: str = "gemini-2.5-flash") -> genai.GenerativeModel:
    """Configure the API from environment and return a Gemini model instance."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("❌ No GEMINI_API_KEY found in environment/.env")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


def run_pytest(pytest_targets: List[str] | None = None,
               extra_args: List[str] | None = None) -> Tuple[int, str]:
    """
    Run pytest and return (exit_code, combined_output).
    Writes a JUnit XML for structured parsing if you want later.
    """
    args = ["pytest", "-q", "--disable-warnings", "--maxfail=1", "--color=no", "--junitxml=pytest_report.xml"]
    if extra_args:
        args.extend(extra_args)
    if pytest_targets:
        args.extend(pytest_targets)

    proc = subprocess.run(args, capture_output=True, text=True)
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return proc.returncode, output.strip()


def condense_pytest_output(text: str, tail_lines: int = 160) -> str:
    # Keep the prompt compact: include last N lines of the pytest output but show top traceback.
    lines = (text or "").splitlines()
    return "\n".join(lines[-tail_lines:]) if len(lines) > tail_lines else (text or "")


def build_prompt_for_pytest(
    code_snippet: str,
    pytest_output_snippet: str,
    repo_files: Dict[str, str],
    description: str | None,
    pytest_targets: List[str] | None,
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
{(description or "").strip()}
[/DESCRIPTION]

[REPO_FILES]
{repo_blob}
[/REPO_FILES]

===== CONTEXT END =====
""".strip()


def extract_json(text: str) -> Dict[str, Any]:
    """Robust JSON extraction from model output."""
    try:
        return json.loads(text)
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
# Orchestrator (parameters only)
# ----------------------------

def running_gemini(
    original_code_path: Union[str, Path],
    context_files: List[str],
    description_path: Union[str, Path],
    test_files: Union[str, List[str]],
    *,
    model_name: str = "gemini-2.5-flash",
    temperature: float = 0.0,
) -> Dict[str, Any]:
    """
    Orchestrate the full step:
      - read inputs (from parameters only),
      - run pytest & condense,
      - build prompt,
      - call Gemini,
      - parse JSON,
      - write fixed_code.txt, why.txt, patch.txt, code.txt,
      - write combined_patch.json,
      - return combined JSON.
    """
    # ---- Validate & read inputs ----
    original_code_path = Path(original_code_path)
    if not original_code_path.exists():
        raise FileNotFoundError(f"original_code_path not found: {original_code_path.resolve()}")
    code_snippet = original_code_path.read_text(encoding="utf-8").strip()

    description = ""
    description_path = Path(description_path)
    if description_path.exists():
        description = description_path.read_text(encoding="utf-8").strip()

    repo_files: Dict[str, str] = {}
    for fp in (context_files or []):
        p = Path(fp)
        repo_files[str(p)] = p.read_text(encoding="utf-8") if p.exists() else ""

    if isinstance(test_files, str):
        pytest_targets = [test_files]
    else:
        pytest_targets = list(test_files or [])

    # ---- Run pytest & condense ----
    exit_code, pytest_output = run_pytest(pytest_targets)
    pytest_output_snippet = condense_pytest_output(pytest_output, tail_lines=160)

    # ---- Build prompt & call model ----
    prompt = build_prompt_for_pytest(
        code_snippet=code_snippet,
        pytest_output_snippet=pytest_output_snippet,
        repo_files=repo_files,
        description=description,
        pytest_targets=pytest_targets,
        exit_code=exit_code,
    )

    model = load_model(model_name=model_name)
    generation_config = {
        "temperature": temperature,
        "response_mime_type": "application/json",
    }
    response = model.generate_content(prompt, generation_config=generation_config)
    raw_text = response.text or ""

    # ---- Parse JSON from model ----
    data = extract_json(raw_text)
    for key in ["SuggestedFixedCode", "ExplanationOfFix", "LineNumberRangesToEdit"]:
        if key not in data:
            raise ValueError(f"JSON missing required key: {key}")

    fixed_code = data["SuggestedFixedCode"]
    explanation = data["ExplanationOfFix"]
    ranges = data["LineNumberRangesToEdit"]  # list[{start,end,reason}]

    # ---- Write artifacts to "." ----
    out_dir = Path(".")

    code_copy_path = out_dir / "code.txt"          # local copy for downstream tools
    fixed_code_path = out_dir / "fixed_code.txt"
    why_path = out_dir / "why.txt"
    patch_path = out_dir / "patch.txt"

    code_copy_path.write_text(code_snippet, encoding="utf-8")
    fixed_code_path.write_text(fixed_code, encoding="utf-8")
    why_path.write_text(explanation, encoding="utf-8")

    patch_lines = []
    for r in (ranges or []):
        patch_lines.append(f"start line: {r.get('start', '')}")
        patch_lines.append(f"end line: {r.get('end', '')}")
    patch_lines.append(f"why: {explanation.strip()}")
    patch_path.write_text("\n".join(patch_lines), encoding="utf-8")

    # ---- Combined JSON (paths only) ----
    combined = {
        "original_code_path": str(code_copy_path),
        "fixed_code_path": str(fixed_code_path),
        "patch_path": str(patch_path),
        "why_path": str(why_path),
        "context_files": list(repo_files.keys()),     # paths only
        "pytest_test_files": pytest_targets,          # tests passed in
    }

    combined_json_path = out_dir / "combined_patch.json"
    combined_json_path.write_text(json.dumps(combined, indent=2), encoding="utf-8")

    return combined

