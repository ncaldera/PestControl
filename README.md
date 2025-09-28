# MHacks2025
🐛 Pest Control

AI-powered bug fixing with test-driven validation and visual reports

## 📖 Overview
Pest Control is a workflow for automatically detecting and repairing bugs in Python projects using LLMs (Gemini). It integrates with pytest to validate candidate fixes and generates human-readable reports. A Streamlit-based frontend allows you to browse and inspect results, including diffs between buggy and fixed code.

## ✨ Features

### Bug Fixing Agent
- Takes in buggy code, context files, and test cases.
- Calls Gemini to propose fixes.
- Applies patches iteratively until tests pass (or loop limit reached).

### Test Runner
- Executes pytest on generated fixes.
- Records whether tests passed/failed per iteration.

### Report System
- Each issue generates `.txt` and `.diff` files in `proposed_fixes/`.
- Reports include suggested patches, explanations, and test results.

### Streamlit Dashboard (`web_visual.py`)
- Summarizes all issues in a clean, Vercel/autograder.io–styled UI.
- Filters, search, and sort across issues.
- Drill-down details: suggested patch, explanation, raw report, and code diffs.
- Supports both unified and side-by-side diff views.

### 🚀 Getting Started
1. Clone repo & install deps
git clone https://github.com/<your-username>/PestControl.git
cd PestControl
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

2. Submit an issue report to this GitHub. Check the box for AI help.

3. View results in the Streamlit UI. Run: streamlit run web_visual.py

4. Select All issues or a specific issue in the sidebar. Inspect summaries, suggested patches, and diffs interactively.
