"""
LIUNA Certificate Generator
============================
Reads a CSV (no header row), generates one PDF per student containing
all their course certificates. Certificates are grouped by Member ID.

CSV column layout (0-indexed):
  2  = Class name
  7  = Hours completed
  10 = Completion date
  11 = Member ID
  12 = Last name
  13 = First name

Online-only classes receive 4 hours credit; all others receive 2 hours.

ONLINE_4HR_CLASSES (case-insensitive match):
  - Asbestos Awareness
  - Silica Awareness
  - Lead Awareness

Usage:
  python liuna_cert_generator.py --csv ClassInformation.csv \\
      --director "Jeff Smrz" \\
      --title "Director" \\
      --org "LIUNA Training of Michigan" \\
      --address "11155 Beardslee Road" \\
      --city "Perry, MI 48872" \\
      --phone "(517) 625-4919" \\
      --output ./certificates
"""

import argparse
import csv
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas as rl_canvas


# ── Column indices (0-based) ────────────────────────────────────────────────
COL_CLASS_NAME = 2
COL_HOURS      = 7
COL_DATE_END   = 10
COL_MEMBER_ID  = 11
COL_LAST_NAME  = 12
COL_FIRST_NAME = 13

# ── Classes that earn 4 hours of online credit ───────────────────────────────
ONLINE_4HR_CLASSES = {
    "asbestos awareness",
    "silica awareness",
    "lead awareness",
}

# ── Page dimensions ──────────────────────────────────────────────────────────
PAGE_W, PAGE_H = landscape(letter)   # 792 x 612 pt

# ── Colours ──────────────────────────────────────────────────────────────────
BLACK      = colors.HexColor("#1A1A1A")
DARK_GRAY  = colors.HexColor("#444444")
MID_GRAY   = colors.HexColor("#666666")
LIGHT_GRAY = colors.HexColor("#888888")
RULE_GRAY  = colors.HexColor("#CCCCCC")
WHITE      = colors.white


# ── Helpers ──────────────────────────────────────────────────────────────────

def fmt_date(raw: str) -> str:
    if not raw:
        return ""
    cleaned = re.sub(r"^[A-Za-z]+,\s*", "", raw.strip())
    for fmt in ("%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(cleaned, fmt).strftime("%B %d, %Y").upper()
        except ValueError:
            continue
    return raw.upper()


def get_name(row: list) -> str:
    first = row[COL_FIRST_NAME].strip() if len(row) > COL_FIRST_NAME else ""
    last  = row[COL_LAST_NAME].strip()  if len(row) > COL_LAST_NAME  else ""
    full  = f"{first} {last}".strip()
    return full.upper() if full else "UNKNOWN"


def safe_filename(name: str, member_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_\-]", "_", f"{name}_{member_id}")
    return f"cert_{safe}.pdf"


def online_hours(class_name: str) -> str:
    return "4.00" if class_name.lower() in ONLINE_4HR_CLASSES else "2.00"


def wrap_text(c, text: str, font: str, size: float, max_width: float) -> list:
    words = text.split()
    lines, line = [], ""
    for word in words:
        test = f"{line} {word}".strip()
        if c.stringWidth(test, font, size) > max_width and line:
            lines.append(line)
            line = word
        else:
            line = test
    if line:
        lines.append(line)
    return lines


# ── CSV loading ──────────────────────────────────────────────────────────────

def load_csv(filepath: str) -> dict:
    groups = defaultdict(lambda: {"name": "", "mid": "", "certs": []})

    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            while len(row) <= max(COL_CLASS_NAME, COL_HOURS, COL_DATE_END,
                                   COL_MEMBER_ID, COL_LAST_NAME, COL_FIRST_NAME):
                row.append("")

            mid = row[COL_MEMBER_ID].strip()
            if not mid:
                continue

            name = get_name(row)
            cls  = row[COL_CLASS_NAME].strip()
            date = row[COL_DATE_END].strip()

            groups[mid]["name"] = name
            groups[mid]["mid"]  = mid
            groups[mid]["certs"].append({
                "name": name,
                "cls":  cls,
                "date": date,
                "mid":  mid,
            })

    return dict(groups)


# ── Certificate drawing ──────────────────────────────────────────────────────

def draw_cert(c: rl_canvas.Canvas,
              name: str, cls: str, date: str, member_id: str,
              dir_name: str, dir_title: str,
              org_name: str, org_addr: str, org_city: str, org_phone: str):

    W, H = PAGE_W, PAGE_H
    cx   = W / 2

    # Background
    c.setFillColor(WHITE)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Double border
    c.setStrokeColor(BLACK)
    c.setLineWidth(2.5)
    c.rect(14, 14, W - 28, H - 28, fill=0, stroke=1)
    c.setLineWidth(0.75)
    c.rect(23, 23, W - 46, H - 46, fill=0, stroke=1)

    # Org title — 32pt bold
    c.setFillColor(BLACK)
    c.setFont("Times-Bold", 32)
    c.drawCentredString(cx, H - 60, (org_name or "LIUNA Training of Michigan").upper())

    # Address block — 11pt
    c.setFont("Helvetica", 11)
    c.setFillColor(DARK_GRAY)
    c.drawCentredString(cx, H - 80, (org_addr or "").upper())
    c.drawCentredString(cx, H - 94, (org_city or "").upper())
    c.drawCentredString(cx, H - 108, org_phone or "")

    # DECLARES THAT — 13pt italic
    c.setFont("Times-Italic", 13)
    c.setFillColor(LIGHT_GRAY)
    c.drawCentredString(cx, H - 150, "DECLARES THAT")

    # Student name — 26pt bold
    c.setFont("Times-Bold", 26)
    c.setFillColor(BLACK)
    c.drawCentredString(cx, H - 190, name or "STUDENT NAME")

    # Date — 13pt
    c.setFont("Helvetica", 13)
    c.setFillColor(DARK_GRAY)
    c.drawCentredString(cx, H - 220, f"ON {fmt_date(date)}")

    # Hours — 13pt
    hrs = online_hours(cls)
    c.drawCentredString(cx, H - 244, f"COMPLETED {hrs} HOURS OF")

    # Class name — 22pt bold
    c.setFont("Times-Bold", 22)
    c.setFillColor(BLACK)
    c.drawCentredString(cx, H - 278, cls.upper())

    # ONLINE TRAINING — 13pt
    c.setFont("Helvetica", 13)
    c.setFillColor(DARK_GRAY)
    c.drawCentredString(cx, H - 306, "ONLINE TRAINING")

    # Light rule
    c.setStrokeColor(RULE_GRAY)
    c.setLineWidth(0.75)
    c.line(55, H - 323, W - 55, H - 323)

    # Disclosure — 11pt italic, word-wrapped
    disclosure = (
        f"The {org_name or 'LIUNA Training of Michigan'} is not, and should not be construed as, "
        "a substitute for an employer's obligation under OSHA or EPA to provide employees with "
        "safety training specific to the nature of the employee's job and pertinent to the actual "
        "equipment and machinery with which the employee will be working while in the contractor's employment."
    )
    disc_lines = wrap_text(c, disclosure, "Times-Italic", 11, W - 140)
    c.setFont("Times-Italic", 11)
    c.setFillColor(MID_GRAY)
    disc_start = H - 350
    for i, ln in enumerate(disc_lines):
        c.drawCentredString(cx, disc_start - i * 15, ln)

    # Director — bottom right, 16pt italic
    c.setFont("Times-Italic", 16)
    c.setFillColor(BLACK)
    c.drawCentredString(W - 200, 110, dir_name or "Director")

    c.setStrokeColor(BLACK)
    c.setLineWidth(0.75)
    c.line(W - 330, 90, W - 70, 90)

    c.setFont("Helvetica", 11)
    c.setFillColor(DARK_GRAY)
    c.drawString(W - 330, 75, (dir_title or "DIRECTOR").upper())

    # EasyGenerator logo — bottom left
    c.setFillColor(colors.HexColor("#F26522"))
    c.ellipse(60, 54, 100, 86, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(80, 73, "easy")
    c.setFont("Helvetica", 8)
    c.drawCentredString(80, 62, "gen")
    c.setFillColor(LIGHT_GRAY)
    c.setFont("Helvetica", 10)
    c.drawString(106, 66, "easygenerator")


# ── PDF generation ───────────────────────────────────────────────────────────

def generate_pdfs(groups: dict, output_dir: str,
                  dir_name: str, dir_title: str,
                  org_name: str, org_addr: str, org_city: str, org_phone: str):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    total = len(groups)

    for i, (mid, group) in enumerate(groups.items(), 1):
        fname    = safe_filename(group["name"], mid)
        out_path = os.path.join(output_dir, fname)

        c = rl_canvas.Canvas(out_path, pagesize=landscape(letter))

        for j, cert in enumerate(group["certs"]):
            if j > 0:
                c.showPage()
            draw_cert(
                c,
                name      = cert["name"],
                cls       = cert["cls"],
                date      = cert["date"],
                member_id = cert["mid"],
                dir_name  = dir_name,
                dir_title = dir_title,
                org_name  = org_name,
                org_addr  = org_addr,
                org_city  = org_city,
                org_phone = org_phone,
            )

        c.save()
        print(f"  [{i}/{total}] {fname}  ({len(group['certs'])} cert{'s' if len(group['certs']) > 1 else ''})")

    print(f"\nDone — {total} PDF{'s' if total != 1 else ''} saved to: {output_dir}")


# ── CLI entry point ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate LIUNA completion certificates from a CSV file."
    )
    parser.add_argument("--csv",      required=True,                              help="Path to CSV file (no header row)")
    parser.add_argument("--director", default="Jeff Smrz",                        help="Director's full name")
    parser.add_argument("--title",    default="Director",                         help="Director's title")
    parser.add_argument("--org",      default="LIUNA Training of Michigan",       help="Organization name")
    parser.add_argument("--address",  default="11155 Beardslee Road",             help="Street address")
    parser.add_argument("--city",     default="Perry, MI 48872",                  help="City, State ZIP")
    parser.add_argument("--phone",    default="(517) 625-4919",                   help="Phone number")
    parser.add_argument("--output",   default="./certificates",                   help="Output directory")
    args = parser.parse_args()

    if not os.path.isfile(args.csv):
        print(f"Error: CSV file not found: {args.csv}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading CSV: {args.csv}")
    groups = load_csv(args.csv)
    total_certs = sum(len(g["certs"]) for g in groups.values())
    print(f"Found {len(groups)} unique student(s) across {total_certs} row(s)\n")
    print(f"Generating PDFs into: {args.output}")

    generate_pdfs(
        groups,
        output_dir = args.output,
        dir_name   = args.director,
        dir_title  = args.title,
        org_name   = args.org,
        org_addr   = args.address,
        org_city   = args.city,
        org_phone  = args.phone,
    )


if __name__ == "__main__":
    main()


# ── Streamlit-compatible API ─────────────────────────────────────────────────
# These functions are imported by app.py and work entirely in memory
# (no file I/O) so they work cleanly inside Streamlit Cloud.

import io
import zipfile


def _class_name_from_filename(filename: str) -> str:
    """
    Derive a human-readable class name from an EasyGenerator filename.
    e.g. 'Silica-Awareness_2026-04-29T14_18_39_588Z_ea00e496.csv'
         -> 'Silica Awareness'
    Strips the timestamp/UUID suffix after the first underscore+date pattern.
    """
    stem = filename.rsplit(".", 1)[0]           # drop .csv
    stem = re.sub(r"_\d{4}-\d{2}-\d{2}.*$", "", stem)  # drop _YYYY-MM-DD...
    stem = stem.replace("-", " ").replace("_", " ")
    return stem.strip().title()


def _is_easygenerator_csv(header_row: list) -> bool:
    """Return True if the CSV looks like an EasyGenerator export."""
    joined = " ".join(header_row).lower()
    return "course result" in joined or "course score" in joined


def load_csv_from_text(raw_text: str, filename: str = "") -> dict:
    """
    Parse CSV from a raw string (already read from an uploaded file).

    Supports two formats:
      • LIUNA class-information CSV (no header, columns by position)
      • EasyGenerator export (has header row: Name, Email, Course result, Finished …)

    Groups rows by Member ID (LIUNA) or Email (EasyGenerator).
    Returns dict: { key: { 'name': str, 'mid': str, 'certs': [...] } }
    """
    import csv as _csv
    groups = defaultdict(lambda: {"name": "", "mid": "", "certs": []})
    lines  = raw_text.splitlines()

    if not lines:
        return {}

    # Peek at first row to detect format
    first_row = next(_csv.reader([lines[0]]))

    if _is_easygenerator_csv(first_row):
        # ── EasyGenerator format ─────────────────────────────────────────────
        cls_name = _class_name_from_filename(filename) if filename else "Online Course"
        reader   = _csv.reader(lines[1:])   # skip header

        for row in reader:
            if not row:
                continue
            # pad row
            while len(row) < 7:
                row.append("")

            full_name = row[0].strip()
            result    = row[3].strip().lower()
            date      = row[6].strip()

            if not full_name or result != "passed":
                continue

            # Use email as unique key; fall back to name
            email = row[1].strip() if len(row) > 1 else ""
            key   = email or full_name

            groups[key]["name"] = full_name.upper()
            groups[key]["mid"]  = email
            groups[key]["certs"].append({
                "name": full_name.upper(),
                "cls":  cls_name,
                "date": date,
                "mid":  email,
            })

    else:
        # ── LIUNA class-information CSV (no header, columns by position) ─────
        reader = _csv.reader(lines)
        for row in reader:
            if not row:
                continue
            while len(row) <= max(COL_CLASS_NAME, COL_HOURS, COL_DATE_END,
                                   COL_MEMBER_ID, COL_LAST_NAME, COL_FIRST_NAME):
                row.append("")

            mid = row[COL_MEMBER_ID].strip()
            if not mid:
                continue

            name = get_name(row)
            cls  = row[COL_CLASS_NAME].strip()
            date = row[COL_DATE_END].strip()

            groups[mid]["name"] = name
            groups[mid]["mid"]  = mid
            groups[mid]["certs"].append({
                "name": name,
                "cls":  cls,
                "date": date,
                "mid":  mid,
            })

    return dict(groups)


def _build_pdf_bytes(group: dict,
                     org_name: str, org_addr: str, org_city: str, org_phone: str,
                     dir_name: str, dir_title: str) -> bytes:
    """Render all certs for one student into a PDF and return raw bytes."""
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=landscape(letter))
    for j, cert in enumerate(group["certs"]):
        if j > 0:
            c.showPage()
        draw_cert(
            c,
            name      = cert["name"],
            cls       = cert["cls"],
            date      = cert["date"],
            member_id = cert["mid"],
            dir_name  = dir_name,
            dir_title = dir_title,
            org_name  = org_name,
            org_addr  = org_addr,
            org_city  = org_city,
            org_phone = org_phone,
        )
    c.save()
    return buf.getvalue()


def generate_pdfs_to_zip(groups: dict,
                         org_name: str = "LIUNA Training of Michigan",
                         org_addr: str = "11155 Beardslee Road",
                         org_city: str = "Perry, MI 48872",
                         org_phone: str = "(517) 625-4919",
                         dir_name: str = "Jeff Smrz",
                         dir_title: str = "Director") -> bytes:
    """
    Generate one PDF per student and return a ZIP archive as bytes.
    Called by the Streamlit app's LIUNA Certificates page.
    """
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for mid, group in groups.items():
            pdf_bytes = _build_pdf_bytes(
                group, org_name, org_addr, org_city, org_phone, dir_name, dir_title
            )
            fname = safe_filename(group["name"], mid)
            zf.writestr(fname, pdf_bytes)
    return zip_buf.getvalue()


def generate_pdfs_merged(groups: dict,
                         org_name: str = "LIUNA Training of Michigan",
                         org_addr: str = "11155 Beardslee Road",
                         org_city: str = "Perry, MI 48872",
                         org_phone: str = "(517) 625-4919",
                         dir_name: str = "Jeff Smrz",
                         dir_title: str = "Director") -> bytes:
    """
    Generate all certificates merged into a single PDF and return as bytes.
    Called by the Streamlit app's LIUNA Certificates page.
    """
    from pypdf import PdfWriter

    writer = PdfWriter()
    for mid, group in groups.items():
        pdf_bytes = _build_pdf_bytes(
            group, org_name, org_addr, org_city, org_phone, dir_name, dir_title
        )
        reader_buf = io.BytesIO(pdf_bytes)
        from pypdf import PdfReader
        reader = PdfReader(reader_buf)
        for page in reader.pages:
            writer.add_page(page)

    out_buf = io.BytesIO()
    writer.write(out_buf)
    return out_buf.getvalue()
