# web_visual.py
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import difflib
from streamlit.components.v1 import html as st_html
import re


st.set_page_config(
    page_title="Pest Control",
    page_icon="🐛",
    layout="wide",
)

# ---------- CSS (autograder.io × vercel) ----------
st.markdown("""
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg: #0b0f19;         /* vercel-ish dark */
  --card: rgba(255,255,255,0.04);
  --card-border: rgba(255,255,255,0.08);
  --text: #e6e8ee;
  --muted: #9aa4b2;
  --accent: #00d1ff;     /* autograder cyan */
  --accent-2: #6366f1;   /* indigo secondary */
  --pass: #22c55e;
  --fail: #ef4444;
  --warn: #f59e0b;
  --chip-bg: rgba(255,255,255,0.06);
  --shadow: 0 8px 30px rgba(0,0,0,.12);
}
@media (prefers-color-scheme: light) {
  :root{
    --bg: #ffffff;
    --card: #ffffff;
    --card-border: #e5e7eb;
    --text: #0b1220;
    --muted: #475569;
    --accent: #06b6d4;
    --accent-2: #4f46e5;
    --shadow: 0 4px 16px rgba(2,6,23,.06);
    --chip-bg: #f1f5f9;
  }
}
html, body, [data-testid="stAppViewContainer"]{
  background: var(--bg);
  color: var(--text);
  font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, "Helvetica Neue", Arial, "Apple Color Emoji", "Segoe UI Emoji";
}
.block-container{padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1200px;}
h1, h2, h3{letter-spacing: -0.015em;}
h1{font-weight: 700;}
/* header bar */
.header{
  display:flex; align-items:center; justify-content:space-between;
  padding:16px 20px; border:1px solid var(--card-border); background:var(--card);
  border-radius:16px; box-shadow: var(--shadow);
}
.brand{
  display:flex; align-items:center; gap:12px; font-weight:700; font-size:1.15rem;
}
.brand .dot{
  width:12px; height:12px; border-radius:999px; background:linear-gradient(135deg,var(--accent),var(--accent-2));
  box-shadow: 0 0 24px rgba(99,102,241,.35);
}
.kbd{
  font-family: ui-monospace, "JetBrains Mono", SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
  border:1px solid var(--card-border); background:var(--chip-bg); padding:4px 8px; border-radius:8px; color:var(--muted);
}
/* stat cards */
.grid{display:grid; grid-template-columns: repeat(12,minmax(0,1fr)); gap:16px; margin-top:16px;}
.card{
  grid-column: span 4 / span 4; padding:16px; border:1px solid var(--card-border); background:var(--card);
  border-radius:16px; box-shadow: var(--shadow);
}
.card h3{font-size:0.9rem; color:var(--muted); margin:0 0 6px 0; font-weight:600;}
.card .big{font-size:1.6rem; font-weight:700;}
/* chips */
.chip{
  display:inline-flex; align-items:center; gap:8px; padding:4px 10px; border-radius:999px; background:var(--chip-bg);
  font-size:0.85rem; font-weight:600; border:1px solid var(--card-border);
}
.chip.pass{ color: var(--pass);}
.chip.fail{ color: var(--fail);}
.chip.warn{ color: var(--warn);}
.badge{
  width:8px; height:8px; border-radius:999px; background: currentColor; display:inline-block;
}
/* code boxes */
.code-box, .raw-box {
  font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
  white-space: pre-wrap; border:1px solid var(--card-border); border-radius:14px; padding:14px;
  background: var(--bg);
}
.section{
  border:1px solid var(--card-border); background:var(--card); border-radius:16px; padding:16px; box-shadow: var(--shadow);
}
hr{border: none; border-top:1px solid var(--card-border); margin: 16px 0;}
/* html diff polish */
.diff table.diff { width: 100%; border-collapse: collapse; border: 1px solid var(--card-border); background: var(--card); border-radius: 12px; overflow: hidden; }
.diff .diff_header { background: rgba(255,255,255,.04); color: var(--muted); }
.diff td, .diff th { border: 1px solid var(--card-border); padding: 6px 8px; vertical-align: top; }
.diff tr:nth-child(even) td { background: rgba(255,255,255,.02); }
.diff .diff_add { background: rgba(34,197,94,.12); }
.diff .diff_sub { background: rgba(239,68,68,.12); }
.diff .diff_chg { background: rgba(99,102,241,.12); }
</style>
""", unsafe_allow_html=True)


LINE_HDR_RE = re.compile(r'^\s*[Ll]ine\s+(\d+)\s*-{3,}')
DIFF_HEADER_OLD = re.compile(r"^---\s+(?P<old>.+)")
DIFF_HEADER_NEW = re.compile(r"^\+\+\+\s+(?P<new>.+)")
HUNK_RE = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@")
SUCCESS_PATTERNS = ("generated fix successful", "fix successful", "tests passed")
FAIL_PATTERNS = ("all generated fixes failed", "tests failed")

def _strip_triple_fences(s: str) -> str:
    return s.replace("```", "")

def parse_unified_diff_paths(diff_text: str) -> tuple[str | None, str | None]:
    old_path = new_path = None
    for line in diff_text.splitlines():
        m1 = DIFF_HEADER_OLD.match(line)
        if m1 and not old_path:
            old_path = m1.group("old").strip()
            continue
        m2 = DIFF_HEADER_NEW.match(line)
        if m2 and not new_path:
            new_path = m2.group("new").strip()
            continue
        if old_path and new_path:
            break
    if old_path and old_path.startswith("a/"): old_path = old_path[2:]
    if new_path and new_path.startswith("b/"): new_path = new_path[2:]
    return old_path, new_path

def parse_hunk_range(diff_text: str) -> tuple[int | None, int | None]:
    for line in diff_text.splitlines():
        m = HUNK_RE.match(line)
        if m:
            new_start = int(m.group(3))
            new_len = int(m.group(4) or "1")
            new_end = new_start + max(new_len - 1, 0)
            return new_start, new_end
    return None, None

def parse_proposed_fix_file(file_path: Path) -> dict:
    """
    Parse a single proposed_fixes/issue_*.txt into our report dict.
    Tolerant to minor format drift. Always defines 'why'.
    """
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    # --- defaults so we never hit NameError ---
    status = "Unknown"
    start_line: int | None = None
    end_line:   int | None = None
    why: str | None = None
    patch_block: str | None = None

    # status from text (loose)
    low = text.lower()
    if any(p in low for p in FAIL_PATTERNS):
        status = "Fail"
    elif any(p in low for p in SUCCESS_PATTERNS):
        status = "Success"

    # find "Line N-----" banners (optional)
    first_marker_idx = second_marker_idx = None
    for idx, ln in enumerate(lines):
        m = LINE_HDR_RE.match(ln)
        if m and first_marker_idx is None:
            first_marker_idx = idx
            try:
                start_line = int(m.group(1))
            except Exception:
                start_line = None
        elif m and first_marker_idx is not None and second_marker_idx is None:
            second_marker_idx = idx
            break

    # locate "Original buggy code description:" (optional)
    desc_idx = None
    for idx, ln in enumerate(lines):
        if ln.strip().lower().startswith("original buggy code description"):
            desc_idx = idx
            break

    # patch/code block between first banner and next banner/desc/EoF
    if first_marker_idx is not None:
        start = first_marker_idx + 1
        end = second_marker_idx if second_marker_idx is not None else (desc_idx if desc_idx is not None else len(lines))
        patch_block = "\n".join(lines[start:end]).rstrip() or None

    # why text after the description label
    if desc_idx is not None:
        why = "\n".join(lines[desc_idx + 1:]).strip() or None

    # attach sibling .diff if present; use it to enrich status/lines/paths
    diff_path = file_path.with_suffix(".diff")
    diff_text = None
    orig_path_in_diff = None
    new_path_in_diff = None
    if diff_path.exists():
        raw_diff = diff_path.read_text(encoding="utf-8", errors="ignore")
        diff_text = _strip_triple_fences(raw_diff)
        orig_path_in_diff, new_path_in_diff = parse_unified_diff_paths(diff_text)
        # if no explicit status but we have a diff, call it Proposed
        if status == "Unknown":
            status = "Proposed"
        # derive line range from first hunk if missing
        if start_line is None:
            s, e = parse_hunk_range(diff_text)
            start_line, end_line = s, e

    return {
        "file": file_path.name,
        "status": status,
        "start_line": start_line,
        "end_line": end_line,
        "why": why,  # guaranteed key (may be None)
        "timestamp": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
        "patch": patch_block,
        "raw": text,
        # diff fields
        "diff_path": str(diff_path) if diff_path.exists() else None,
        "diff_text": diff_text,
        # code paths hinted by diff headers
        "original_code_path": orig_path_in_diff,
        "fixed_code_path": new_path_in_diff,
    }



def load_proposed_fixes(dir_path: Path) -> list[dict]:
    files = sorted(dir_path.glob("*.txt"))
    reports = []
    for f in files:
        try:
            reports.append(parse_proposed_fix_file(f))
        except Exception as e:
            # best-effort: still surface file with minimal info
            reports.append({
                "file": f.name, "status": "Unknown",
                "start_line": None, "end_line": None,
                "why": f"Parse error: {e}",
                "timestamp": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                "patch": None, "raw": f.read_text(encoding='utf-8', errors='ignore')
            })
    return reports

# ---------- header ----------
st.markdown("""
<div class="header">
  <div class="brand">
    <div class="dot"></div>
    Pest Control
  </div>
  <div class="kbd">Shift + R to rerun</div>
</div>
""", unsafe_allow_html=True)

# ---------- load proposed_fixes ----------
PROPOSED_DIR = Path("proposed_fixes")
if not PROPOSED_DIR.exists():
    st.warning("`proposed_fixes/` not found. Create it or adjust PROPOSED_DIR.")
    reports = []
else:
    candidates = sorted(PROPOSED_DIR.glob("*.txt"))
    with st.sidebar:
        st.markdown("### Data source")
        mode = st.radio("Show", ["All issues", "One issue"], index=0)
        if mode == "One issue":
            picked = st.selectbox("Pick an issue", options=candidates, format_func=lambda p: p.name)
            reports = load_proposed_fixes(PROPOSED_DIR) if picked is None else [parse_proposed_fix_file(picked)]
        else:
            reports = load_proposed_fixes(PROPOSED_DIR)

# ---------- summary ----------
st.subheader("Summary")

colf1, colf2, colf3 = st.columns([1,1,2])
with colf1:
    status_filter = st.selectbox("Filter status", options=["All", "Success", "Fail", "Unknown"], index=0)
with colf2:
    sort_by = st.selectbox("Sort by", options=["timestamp", "file", "status"], index=0)
with colf3:
    query = st.text_input("Search (file / why)")

table_rows = []
for r in reports:
    status = (r.get("status") or "Unknown").strip()
    if status_filter != "All" and status != status_filter:
        continue
    text = f"{r.get('file','')} {r.get('why','')}".lower()
    if query and query.lower() not in text:
        continue
    table_rows.append(r)

reverse = sort_by == "timestamp"
table_rows.sort(key=lambda x: (x.get(sort_by) or ""), reverse=reverse)

def chip_html(status: str) -> str:
    s = (status or "Unknown").lower()
    if s.startswith(("success","pass")):
        cls = "pass"
    elif s.startswith(("fail","error")):
        cls = "fail"
    elif s.startswith("proposed"):
        cls = "warn"
    else:
        cls = "warn"
    return f"<span class='chip {cls}'><span class='badge'></span>{status or 'Unknown'}</span>"


summary_html = [
    "<div class='section' style='padding:0;'>",
    "<table style='width:100%; border-collapse:separate; border-spacing:0;'>",
    "<thead>",
    "<tr style='background:var(--card);'>",
    "<th style='text-align:left; padding:12px 16px;'>file</th>",
    "<th style='text-align:left; padding:12px 16px;'>status</th>",
    "<th style='text-align:left; padding:12px 16px;'>lines</th>",
    "<th style='text-align:left; padding:12px 16px;'>why</th>",
    "<th style='text-align:right; padding:12px 16px;'>timestamp</th>",
    "</tr>",
    "</thead>",
    "<tbody>"
]
for i, r in enumerate(table_rows):
    zebra = "background:rgba(255,255,255,0.02);" if i % 2 else ""
    lines = "—"
    if r.get("start_line") is not None and r.get("end_line") is not None:
        lines = f"{r['start_line']}–{r['end_line']}"
    summary_html.append(
        f"<tr style='{zebra}'>"
        f"<td style='padding:12px 16px; font-weight:600'>{r.get('file','')}</td>"
        f"<td style='padding:12px 16px;'>{chip_html(r.get('status'))}</td>"
        f"<td style='padding:12px 16px; font-family:JetBrains Mono, ui-monospace;'>{lines}</td>"
        f"<td style='padding:12px 16px; color:var(--muted); max-width: 520px;'>{r.get('why','')}</td>"
        f"<td style='padding:12px 16px; text-align:right;'>{r.get('timestamp','')}</td>"
        f"</tr>"
    )
summary_html += ["</tbody></table></div>"]
st.markdown("\n".join(summary_html), unsafe_allow_html=True)

# ---------- details ----------
st.subheader("Details")

for idx, r in enumerate(table_rows):
    status = (r.get("status") or "Unknown")
    s = status.lower()
    cls = "pass" if s.startswith("success") or s.startswith("pass") else "fail" if s.startswith("fail") else "warn"
    chip = f"<span class='chip {cls}'><span class='badge'></span>{status}</span>"

    with st.expander(f"{r.get('file','')}"):
        col1, col2, col3 = st.columns([1,1,2])
        with col1:
            st.markdown(chip, unsafe_allow_html=True)
        with col2:
            lines = "—"
            if r.get("start_line") is not None and r.get("end_line") is not None:
                lines = f"{r['start_line']}–{r['end_line']}"
            st.markdown(f"**Lines**<br><span class='kbd'>{lines}</span>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"**Timestamp**<br><span class='kbd'>{r.get('timestamp','')}</span>", unsafe_allow_html=True)

        st.markdown("<hr/>", unsafe_allow_html=True)
        st.markdown("**Why**")
        st.markdown(f"{r.get('why','—') or '—'}")

        # Suggested patch (as code)
        if r.get("patch"):
            st.markdown("<br/>**Suggested Patch**", unsafe_allow_html=True)
            st.code(r["patch"], language="python")

        # -------- Diff panel --------
        # 1) If we have a unified diff file next to the report, show it directly.
        if r.get("diff_text"):
            st.markdown("<br/>**Diff (from .diff file)**", unsafe_allow_html=True)
            st.code(r["diff_text"], language="diff")
        else:
            # 2) Otherwise, try to render a computed diff from files
            orig_path = r.get("original_code_path") or "code.txt"
            fixed_path = r.get("fixed_code_path") or "fixed_code.txt"
            orig_exists, fixed_exists = Path(orig_path).exists(), Path(fixed_path).exists()

            if orig_exists and fixed_exists:
                st.markdown("<br/>**Diff**", unsafe_allow_html=True)
                diff_mode = st.radio(
                    "View", ["Unified", "Side-by-side"],
                    key=f"diff_mode_{idx}",
                    horizontal=True
                )
                orig_lines = Path(orig_path).read_text(encoding="utf-8").splitlines()
                new_lines  = Path(fixed_path).read_text(encoding="utf-8").splitlines()
                if diff_mode == "Unified":
                    udiff = "\n".join(difflib.unified_diff(
                        orig_lines, new_lines,
                        fromfile=f"{Path(orig_path).name} (original)",
                        tofile=f"{Path(fixed_path).name} (fixed)",
                        lineterm=""
                    ))
                    st.code(udiff or "# (no changes)", language="diff")
                else:
                    hdiff = difflib.HtmlDiff(wrapcolumn=90).make_table(
                        orig_lines, new_lines,
                        fromdesc=f"{Path(orig_path).name} (original)",
                        todesc=f"{Path(fixed_path).name} (fixed)",
                        context=True, numlines=2
                    )
                    st_html(f"<div class='diff'>{hdiff}</div>", height=520, scrolling=True)
            else:
                st.info("Diff unavailable: .diff not found and code files not found.")


        # Raw report
        with st.expander("Raw Report"):
            st.code(r.get('raw', "") or "", language=None)
