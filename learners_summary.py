"""
learners_summary.py
-------------------
Trainscript App — Learners Summary Report
Parses a learner CSV export and produces a monthly course-completion summary.

Usage:
    from learners_summary import LearnersReport
    report = LearnersReport("path/to/learners.csv")
    report.print_summary()
    report.export_html("output/summary.html")

Also used directly by the Streamlit app's "Learner Summary" page — there,
csv_path can be an uploaded-file object (anything with a .read()) instead
of a path, since Streamlit hands us the file in memory rather than on disk.
"""

import re
import pandas as pd
from datetime import datetime
from pathlib import Path


# ── helpers ──────────────────────────────────────────────────────────────────

UUID_PATTERN = re.compile(r"\s*\([a-f0-9]{32}\)$")


def _clean_course_name(col: str) -> str:
    """Strip the trailing UUID from a course column name."""
    return UUID_PATTERN.sub("", col).strip()


def _is_passed(value) -> bool:
    return isinstance(value, str) and value.strip().lower().startswith("passed")


# ── main class ────────────────────────────────────────────────────────────────

class LearnersReport:
    """
    Learners Summary Report for Trainscript.

    Parameters
    ----------
    csv_path : str | Path | file-like
        Path to the LMS learner CSV export, or an already-open file-like
        object (e.g. a Streamlit UploadedFile) with a .read() method.
    """

    COURSE_START_COL = 5  # Columns 0-4 are metadata (Name, Email, etc.)

    def __init__(self, csv_path):
        if hasattr(csv_path, "read"):
            # File-like object (e.g. Streamlit's UploadedFile) — pandas can
            # read it directly; keep its original filename (if any) around
            # for display purposes, since there's no real path on disk.
            self.csv_path = Path(getattr(csv_path, "name", "uploaded.csv"))
            self.df = pd.read_csv(csv_path)
        else:
            self.csv_path = Path(csv_path)
            self.df = pd.read_csv(self.csv_path)
        self._course_cols = self.df.columns[self.COURSE_START_COL:]
        self._parse()

    # ── internal parsing ──────────────────────────────────────────────────────

    def _parse(self):
        """Build summary stats from the raw dataframe."""
        # Detect reporting month from "Last active" column
        if "Last active" in self.df.columns:
            dates = pd.to_datetime(self.df["Last active"], errors="coerce").dropna()
            if not dates.empty:
                most_recent = dates.max()
                self.report_month = most_recent.strftime("%B %Y")
            else:
                self.report_month = "Unknown month"
        else:
            self.report_month = "Unknown month"

        # Count passed completions per course
        course_counts = {}
        for col in self._course_cols:
            name = _clean_course_name(col)
            count = int(self.df[col].apply(_is_passed).sum())
            if count > 0:
                # Merge duplicate course names (same course, different UUIDs)
                course_counts[name] = course_counts.get(name, 0) + count

        # Sort descending by completion count
        self.course_summary = dict(
            sorted(course_counts.items(), key=lambda x: -x[1])
        )

        # Top-level stats
        self.total_students = len(self.df)
        self.total_completions = sum(self.course_summary.values())
        self.students_with_completions = int(
            self.df[self._course_cols]
            .apply(lambda row: row.apply(_is_passed).any(), axis=1)
            .sum()
        )
        self.students_no_completions = (
            self.total_students - self.students_with_completions
        )
        self.total_courses_with_completions = len(self.course_summary)

    # ── public API ────────────────────────────────────────────────────────────

    def summary_dict(self) -> dict:
        """Return the full summary as a plain dictionary."""
        return {
            "report_month": self.report_month,
            "total_students": self.total_students,
            "total_completions": self.total_completions,
            "students_with_completions": self.students_with_completions,
            "students_no_completions": self.students_no_completions,
            "total_courses_with_completions": self.total_courses_with_completions,
            "courses": self.course_summary,
        }

    def print_summary(self):
        """Print a formatted summary to the console."""
        print(f"\n{'='*55}")
        print(f"  LEARNERS SUMMARY REPORT — {self.report_month.upper()}")
        print(f"{'='*55}")
        print(f"  Total students          : {self.total_students}")
        print(f"  With completions        : {self.students_with_completions}")
        print(f"  No completions          : {self.students_no_completions}")
        print(f"  Total completions       : {self.total_completions}")
        print(f"  Courses with activity   : {self.total_courses_with_completions}")
        print(f"\n  {'COURSE':<45} {'COUNT':>5}  {'% OF CLASS':>10}")
        print(f"  {'-'*45} {'-'*5}  {'-'*10}")
        for course, count in self.course_summary.items():
            pct = round(count / self.total_students * 100)
            # Truncate long names for console display
            label = (course[:42] + "...") if len(course) > 45 else course
            print(f"  {label:<45} {count:>5}  {pct:>9}%")
        print(f"{'='*55}\n")

    def export_html(self, output_path: str | Path = "learners_summary.html"):
        """
        Generate a standalone HTML report and save to output_path.

        Parameters
        ----------
        output_path : str | Path
            Where to write the HTML file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self._build_html(), encoding="utf-8")
        print(f"[Trainscript] Report saved → {output_path.resolve()}")
        return output_path

    def to_html_string(self) -> str:
        """
        Return the standalone HTML report as a string, without writing
        anything to disk. Used by the Streamlit app's download button,
        where writing a file as a side effect of viewing a page isn't
        appropriate.
        """
        return self._build_html()

    def _build_html(self) -> str:
        """Build the standalone HTML report and return it as a string."""
        max_count = max(self.course_summary.values()) if self.course_summary else 1
        rows_html = ""
        for course, count in self.course_summary.items():
            pct = round(count / self.total_students * 100)
            bar_w = round(count / max_count * 100)
            rows_html += f"""
            <tr>
              <td class="course-name">{course}</td>
              <td class="bar-cell">
                <div class="bar-bg">
                  <div class="bar-fill" style="width:{bar_w}%"></div>
                </div>
              </td>
              <td class="num">{count}</td>
              <td class="pct">{pct}%</td>
            </tr>"""

        generated = datetime.now().strftime("%Y-%m-%d %H:%M")
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Learners Summary Report — {self.report_month}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'IBM Plex Sans', sans-serif;
    background: #f4f3ef;
    color: #1a1a1a;
    padding: 2rem;
    min-height: 100vh;
  }}
  .page {{ max-width: 820px; margin: 0 auto; }}
  .report-header {{
    border-bottom: 2px solid #1a1a1a;
    padding-bottom: 1rem;
    margin-bottom: 1.5rem;
  }}
  .label {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: #666;
  }}
  h1 {{
    font-size: 26px;
    font-weight: 600;
    margin: 4px 0 2px;
  }}
  .meta {{ font-size: 13px; color: #555; }}
  .stats {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
    margin-bottom: 2rem;
  }}
  .stat {{
    background: #fff;
    border: 0.5px solid #ddd;
    border-radius: 8px;
    padding: 1rem 1.25rem;
  }}
  .stat-label {{ font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px; }}
  .stat-val {{ font-size: 28px; font-weight: 600; font-family: 'IBM Plex Mono', monospace; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border: 0.5px solid #ddd; border-radius: 8px; overflow: hidden; }}
  thead th {{
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: .06em;
    color: #888;
    text-align: left;
    padding: 10px 14px;
    border-bottom: 0.5px solid #e0e0e0;
    background: #fafaf8;
  }}
  tbody tr {{ border-bottom: 0.5px solid #f0f0f0; }}
  tbody tr:last-child {{ border-bottom: none; }}
  tbody tr:hover {{ background: #fafaf8; }}
  td {{ padding: 11px 14px; font-size: 14px; vertical-align: middle; }}
  .course-name {{ font-weight: 400; color: #1a1a1a; width: 38%; }}
  .bar-cell {{ width: 42%; }}
  .bar-bg {{
    height: 7px;
    background: #eeece8;
    border-radius: 999px;
    overflow: hidden;
  }}
  .bar-fill {{
    height: 100%;
    background: #1a6b4a;
    border-radius: 999px;
  }}
  .num {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    font-weight: 500;
    color: #1a6b4a;
    text-align: right;
    width: 8%;
  }}
  .pct {{
    font-size: 12px;
    color: #888;
    text-align: right;
    width: 8%;
  }}
  .footer {{
    margin-top: 1.5rem;
    font-size: 12px;
    color: #aaa;
    font-family: 'IBM Plex Mono', monospace;
  }}
</style>
</head>
<body>
<div class="page">
  <div class="report-header">
    <div class="label">Trainscript — Learners Summary Report</div>
    <h1>{self.report_month}</h1>
    <div class="meta">Source: {self.csv_path.name} &nbsp;·&nbsp; Generated {generated}</div>
  </div>

  <div class="stats">
    <div class="stat">
      <div class="stat-label">Total students</div>
      <div class="stat-val">{self.total_students}</div>
    </div>
    <div class="stat">
      <div class="stat-label">With completions</div>
      <div class="stat-val">{self.students_with_completions}</div>
    </div>
    <div class="stat">
      <div class="stat-label">No completions</div>
      <div class="stat-val">{self.students_no_completions}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Total completions</div>
      <div class="stat-val">{self.total_completions}</div>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Course name</th>
        <th>Completions</th>
        <th style="text-align:right">Count</th>
        <th style="text-align:right">% of class</th>
      </tr>
    </thead>
    <tbody>{rows_html}
    </tbody>
  </table>

  <div class="footer">* Completion date not stored per-course in this CSV format — based on learner last-active date.</div>
</div>
</body>
</html>"""

        return html
