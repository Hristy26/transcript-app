"""
run_learners_summary.py
-----------------------
Trainscript — run the Learners Summary Report from the command line.

Usage:
    python run_learners_summary.py <csv_file> [--html]

Examples:
    python run_learners_summary.py data/learners.csv
    python run_learners_summary.py data/learners.csv --html
"""

import sys
import argparse
from pathlib import Path

# Allow running from the trainscript root
sys.path.insert(0, str(Path(__file__).parent))
from reports.learners_summary import LearnersReport


def main():
    parser = argparse.ArgumentParser(
        description="Trainscript — Learners Summary Report"
    )
    parser.add_argument("csv", help="Path to the learner CSV export")
    parser.add_argument(
        "--html",
        action="store_true",
        help="Also export an HTML report to output/learners_summary.html",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"[ERROR] File not found: {csv_path}")
        sys.exit(1)

    report = LearnersReport(csv_path)
    report.print_summary()

    if args.html:
        out = Path("output") / "learners_summary.html"
        report.export_html(out)


if __name__ == "__main__":
    main()
