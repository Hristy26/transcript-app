# Transcript App

A Streamlit app for managing construction-workforce safety training records: turning raw LMS/CSV exports into clean, printable training transcripts and LIUNA completion certificates. Runs entirely on your own machine (or Streamlit Cloud) — nothing is saved between sessions unless you download it.

Repository: [github.com/Hristy26/transcript-app](https://github.com/Hristy26/transcript-app)

---

## What it does

The app has eight pages, in the left-hand nav:

- **Upload & Process** — drop one or more CSV exports; each file is treated as a separate course. Courses are auto-detected from the filename or column headers (see Course Keyword Detection in Settings), and workers are matched across files by email address.
- **Preview Workers** — search/filter the loaded workers by name, email, or pass/in-progress status, and preview any worker's transcript before downloading it.
- **Generate PDFs** — build one merged PDF (all workers, alphabetical) or a ZIP of individual PDFs, one per worker.
- **Batch Lookup** — paste or upload a list of emails; only the workers that match get pulled out for their own merged PDF or ZIP.
- **Export CSV** — a clean, combined CSV export of every worker/course/status row, previewed on-screen before downloading.
- **LIUNA Certificates** — upload a LIUNA class-information CSV (or an EasyGenerator export) and generate landscape completion certificates, either merged into one PDF or as an individual ZIP per student.
- **Learner Summary** — upload a full LMS learner export (one row per student, one column per course) and get a monthly course-completion summary: total students, how many completed at least one course, and a ranked breakdown of completions per course. Can also be run from the command line — see below.
- **Settings** — toggle color vs. grayscale PDFs, see how course-name auto-detection works, and read about the app.

---

## Setup

### Requirements
- Python 3.10+
- Conda (recommended)

### Install with Conda

```bash
conda create -n transcript-app python=3.11
conda activate transcript-app
pip install -r requirements.txt
```

### Run the app

```bash
streamlit run app.py
```

This opens the app in your browser at `http://localhost:8501`. Data you upload only lives in that browser session's memory — closing the tab or restarting the app clears it, so download anything you want to keep.

---

## Learner Summary from the command line

Outside the Streamlit UI, the same report can be run directly against a CSV file:

```bash
# Print summary to console
python run_learners_summary.py path/to/learners.csv

# Print + export an HTML report to output/learners_summary.html
python run_learners_summary.py path/to/learners.csv --html
```

Or from your own Python code:

```python
from learners_summary import LearnersReport

report = LearnersReport("path/to/learners.csv")
report.print_summary()
report.export_html("output/learners_summary.html")
data = report.summary_dict()
print(data["courses"])
```

### Learner Summary CSV format

This is a different shape of file than the per-course CSVs used on Upload & Process — it expects one full LMS learner export, with one row per student:

| Column | Description |
|---|---|
| `Name` | Student full name |
| `Email` | Student email address |
| `Last active` | Last activity timestamp (used to derive the report month) |
| `Total number of courses` | Enrolled course count |
| `Passed courses` | Number of passed courses |
| `[Course Name] (uuid)` | One column per course, value is `Passed (X%)` or `In progress (X%)` |

> **Note:** Per-course completion dates aren't included in this CSV format — the report month is derived from the most recent "Last active" date across all students. To get exact completion dates per course, export a course-activity report from your LMS instead.

---

## Project structure

```
transcript-app/
├── app.py                    # the Streamlit multi-page app (entry point)
├── utils.py                  # shared CSV-parsing / PDF-building logic for transcripts
├── liuna_cert_generator.py   # LIUNA certificate drawing (CLI + Streamlit-compatible API)
├── learners_summary.py       # LearnersReport — monthly course-completion summary
├── run_learners_summary.py   # CLI runner for the Learner Summary report
├── requirements.txt          # pip dependencies
├── .streamlit/
│   └── config.toml           # Streamlit theme (navy/gold) + server settings
├── .devcontainer/
│   └── devcontainer.json     # GitHub Codespaces config — runs `streamlit run app.py` on attach
└── README.md
```

---

## Known issues / Roadmap

**LIUNA certificate appearance** (in progress):
- The block of text below "DECLARES THAT" should be vertically centered on the certificate page rather than anchored from a fixed top offset.
- The director's name should sit as an actual signature resting on the signature line, not plain text floating above it.
- Support printing one certificate at a time (individual lookup) in addition to the existing batch/merged/ZIP options.

**Other ideas:**
- [ ] Per-course completion date tracking on Learner Summary (requires an LMS course-activity export, since the learner export only has one "Last active" date)
- [ ] Filter Learner Summary by month when a CSV spans multiple months
- [ ] GitHub Actions — auto-generate a Learner Summary report on CSV upload

---

## Push changes to GitHub

```bash
git add -A
git commit -m "describe what you changed"
git push origin main
```

`git status` any time to see what's changed but not yet committed.

---

## Security Notes

- Never paste API keys, tokens, or passwords into a chat or commit them to your repo
- Use a `.env` file for secrets and add it to `.gitignore` if this app ever needs one
- GitHub Personal Access Tokens should have the minimum scope needed (`repo` only)
- Revoke and rotate any token that is accidentally exposed
- Worker data (names, emails, last-4 SSNs) only ever lives in memory during a session — nothing is written to disk by the app itself

---

## Learning Stack

This project is being built as a hands-on learning exercise covering:

| Tool | Purpose |
|---|---|
| **Python** | Core language |
| **Conda** | Environment management |
| **Streamlit** | Web UI — runs the same app on any PC, no install beyond Python |
| **pandas** | CSV parsing and data analysis |
| **reportlab / pypdf** | PDF generation and merging |
| **Claude** | AI-assisted development |
| **GitHub** | Version control and collaboration |
