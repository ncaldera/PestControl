import re
import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import datetime

st.set_page_config(
    page_title="Pest Control",
    layout="wide",
    page_icon="🐞"
)

# css styling
st.markdown(
    """
    <style>
    /* background + font colors */
    .stApp {
        background-color: #001f3f;
        color: #ffffff;
    }
    /* headers in light blue */
    h1, h2, h3, h4, h5 {
        color: #00d1ff;
    }
    /* section boxes */
    .stFrame, .stContainer {
        border-radius: 15px;
        padding: 20px;
        background-color: #002b5c;
        margin-bottom: 20px;
    }
    /* table */
    .dataframe th, .dataframe td {
        color: #ffffff !important;
    }
    /* code boxes */
    .code-box {
        background-color: #003366;
        border-radius: 10px;
        padding: 10px;
        font-family: monospace;
        color: #00d1ff;
        white-space: pre-wrap;
    }
    /* raw box */ 
    .raw-box {
        background-color: #111111;
        color: #00d1ff;
        font-family: Monaco, monospace;
        white-space: pre-wrap;
        border-radius: 10px;
        padding: 10px;
        overflow-x: auto; /* horizontal scroll for long lines */
    }
    </style>
    """,
    unsafe_allow_html=True
)

def parse_report_txt(file_path: Path):
    data = {
        "file": file_path.name,
        "status": "Unknown",
        "patch": None,
        "start_line": None,
        "end_line": None,
        "why": None,
        "timestamp": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
        "raw": None,
    }
    
    with open(file_path, "r") as fh:
        content = fh.read()
        data["raw"] = content

    # Status
    if "Generated fix successful!" in content:
        data["status"] = "Success"
    elif "All generated fixes failed" in content:
        data["status"] = "Fail"

    # Extract line numbers
    line_matches = re.findall(r"line (\d+)-+", content)
    if line_matches:
        data["start_line"] = int(line_matches[0])
        if len(line_matches) > 1:
            data["end_line"] = int(line_matches[-1])

    # Extract patch
    patch_match = re.search(r"Suggested patch:\n(.*?)line \d+", content, re.S)
    if patch_match:
        data["patch"] = patch_match.group(1).strip()

    # Extract "why"
    why_match = re.search(r"Original buggy code description:\n(.*?)\nGood luck", content, re.S)
    if why_match:
        data["why"] = why_match.group(1).strip()

    return data

st.title("Pest Control")

REPORTS_DIR = Path("proposed_fixes")  # adjust to your repo’s output folder
report_files = sorted(REPORTS_DIR.glob("*.txt"), key=lambda f: f.stat().st_mtime, reverse=True)

if not report_files:
    st.warning(f"No reports found in {REPORTS_DIR}. Run the tool to generate bug reports.")
else:
    all_reports = [parse_report_txt(f) for f in report_files]

    # Summary table
    df = pd.DataFrame([{
        "file": r["file"],
        "status": r["status"],
        "start": r["start_line"],
        "end": r["end_line"],
        "why": r["why"],
        "timestamp": r["timestamp"]
    } for r in all_reports])
    
    st.subheader("Summary of Bug Fixes")
    st.dataframe(df)
    st.subheader("Detailed Reports")

    for idx, r in enumerate(all_reports):
        # Unique key per report for session state
        key = f"show_report_{idx}"
        if key not in st.session_state:
            st.session_state[key] = False

        # Button acts as the "header" that can be clicked
        if st.button(f"{r['file']} — {r['status']}", key=f"btn_{idx}"):
            st.session_state[key] = not st.session_state[key]

        # Expanded content
        if st.session_state[key]:
            st.markdown(
                f"""
                <div style="
                    background-color: #002b5c;
                    color: #00d1ff;
                    font-family: Monaco, monospace;
                    padding: 10px;
                    border-radius: 8px;
                    margin-bottom: 10px;
                ">
                <p><strong>Lines:</strong> {r['start_line']}–{r['end_line']}</p>
                <p><strong>Why:</strong> {r['why']}</p>
                <p><strong>Timestamp:</strong> {r['timestamp']}</p>
                """
                + (f"<p><strong>Suggested Patch:</strong><br><div class='code-box'>{r['patch']}</div></p>"
                if r["patch"] else "")
                + f"""
                <details style="color:#ffffff;">
                    <summary>Raw Report Text</summary>
                    <div class='raw-box'>{r['raw']}</div>
                </details>
                </div>
                """,
                unsafe_allow_html=True
            )
