"""
app.py — Training Transcript + LIUNA Certificate Generator
Multi-page Streamlit application.

Pages:
  📤  Upload & Process
  👥  Preview Workers
  📄  Generate PDFs
  🔍  Batch Lookup
  ✏️  Export CSV
  🏆  LIUNA Certificates
  ⚙️  Settings

All shared processing / PDF-building logic lives in utils.py.
LIUNA certificate drawing lives in liuna_cert_generator.py.
"""

import base64
import io
import hashlib
import re

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from utils import (
    COURSE_KEYWORDS,
    build_clean_csv,
    build_person_pdf,
    build_preview_html,
    build_zip,
    merge_pdfs,
    parse_email_list,
    parse_lookup_list,
    lookup_people,
    format_report_title,
    format_span,
    report_filename,
    now_stamp,
    data_date_span,
    process_files,
)
from liuna_cert_generator import (
    load_csv_from_text,
    merge_groups,
    generate_pdfs_to_zip,
    generate_pdfs_merged,
    generate_single_pdf,
    safe_filename,
)
from learners_summary import LearnersReport

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Training & Certificate Generator",
    page_icon="📋",
    layout="wide",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

[data-testid="stSidebar"] {
    background: #1B3A6B !important;
    min-width: 230px !important;
    max-width: 230px !important;
}
[data-testid="stSidebar"] * { color: #fff !important; }

.sidebar-logo {
    padding: 28px 20px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.12);
    margin-bottom: 10px;
}
.sidebar-logo h1 { font-size: 1rem; font-weight: 700; color: #fff !important; margin: 0 0 3px; }
.sidebar-logo p  { font-size: 0.72rem; color: #C9A84C !important; margin: 0; }

.nav-section-label {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; color: rgba(255,255,255,0.35) !important;
    padding: 14px 20px 4px;
}
.nav-item {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 20px; border-radius: 0 8px 8px 0;
    margin: 2px 8px 2px 0; font-size: 0.875rem; font-weight: 500;
    color: rgba(255,255,255,0.7) !important; border-left: 3px solid transparent;
}
.nav-item.active {
    background: rgba(201,168,76,0.18); color: #fff !important;
    border-left-color: #C9A84C; font-weight: 600;
}

.stApp { background: #F7F6F2; }
.block-container { padding-top: 2rem !important; max-width: 960px; }

.page-header {
    background: #1B3A6B; border-radius: 14px;
    padding: 28px 32px 22px; margin-bottom: 24px;
    position: relative; overflow: hidden;
}
.page-header::before {
    content: ''; position: absolute; top: -30px; right: -30px;
    width: 140px; height: 140px;
    background: rgba(201,168,76,0.14); border-radius: 50%;
}
.page-header h2 { color: #fff; font-size: 1.4rem; font-weight: 700; margin: 0 0 4px; }
.page-header p  { color: #C9A84C; font-size: 0.85rem; margin: 0; }

.stat-row { display: flex; gap: 12px; margin: 16px 0; }
.stat-box {
    flex: 1; background: #fff; border-radius: 10px;
    padding: 16px; text-align: center; border: 1px solid #E8E4DB;
}
.stat-num   { font-size: 2rem; font-weight: 700; color: #1B3A6B; font-family: 'DM Mono', monospace; line-height: 1; }
.stat-label { font-size: 0.72rem; color: #999; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }

.worker-row {
    display: flex; align-items: center; border-radius: 8px;
    padding: 9px 14px; margin: 3px 0; font-size: 0.86rem;
    border-left: 4px solid transparent;
}
.worker-row.pass { background: #F0FFF4; border-left-color: #2E7D32; }
.worker-row.prog { background: #FFF8F0; border-left-color: #E65100; }
.worker-name  { font-weight: 600; flex: 1; color: #1a1a1a; }
.worker-email { font-size: 0.78rem; color: #888; margin-left: 6px; }
.worker-ssn   { font-size: 0.76rem; color: #bbb; margin-left: 10px; font-family: 'DM Mono', monospace; }
.badge        { font-size: 0.72rem; font-weight: 700; padding: 2px 9px; border-radius: 20px; margin-left: 10px; white-space: nowrap; }
.badge-pass   { background: #C8E6C9; color: #1B5E20; }
.badge-prog   { background: #FFE0B2; color: #BF360C; }

.section-label {
    font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; color: #999; margin: 20px 0 8px;
}
.upload-hint {
    background: #fff; border: 2px dashed #C9A84C; border-radius: 12px;
    padding: 18px 22px; text-align: center; color: #777;
    font-size: 0.84rem; margin-bottom: 8px;
}
.match-chip {
    display: inline-block; background: #E8F5E9; color: #2E7D32;
    border-radius: 20px; padding: 2px 10px;
    font-size: 0.76rem; font-weight: 600; margin: 3px 4px 3px 0;
}
.nomatch-chip {
    display: inline-block; background: #FFF3E0; color: #E65100;
    border-radius: 20px; padding: 2px 10px;
    font-size: 0.76rem; font-weight: 600; margin: 3px 4px 3px 0;
}
.info-card {
    background: #fff; border: 1px solid #E8E4DB; border-radius: 10px;
    padding: 16px 20px; margin-bottom: 14px;
}
.info-card h4 { margin: 0 0 6px; color: #1B3A6B; font-size: 0.95rem; }
.info-card p  { margin: 0; color: #666; font-size: 0.83rem; line-height: 1.6; }

/* Transcript preview */
.preview-wrap { font-family: 'DM Sans', Arial, sans-serif; border: 1px solid #ddd; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
.preview-hdr  { background: #1B3A6B; padding: 22px 26px; text-align: center; }
.preview-hdr h3 { color: #fff; font-size: 1.1rem; font-weight: 800; margin: 0 0 2px; letter-spacing: 2px; }
.preview-hdr p  { color: #C9A84C; font-size: 0.95rem; margin: 0; }
.preview-meta { display: grid; grid-template-columns: 1.4fr 1.8fr 1fr; border-bottom: 1px solid #e0e0e0; }
.preview-cell { padding: 11px 16px; border-right: 1px solid #e0e0e0; }
.preview-cell:last-child { border-right: none; }
.preview-cell .lbl { font-size: 0.65rem; font-weight: 700; color: #aaa; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 3px; }
.preview-cell .val { font-size: 0.88rem; color: #222; font-weight: 600; word-break: break-all; }
.preview-sec-hdr { background: #1B3A6B; color: #fff; font-size: 0.72rem; font-weight: 700; letter-spacing: 1.5px; padding: 7px 16px; text-transform: uppercase; }
.preview-course-row { display: grid; grid-template-columns: 2fr 0.85fr 1.1fr 1.2fr; padding: 9px 16px; border-bottom: 1px solid #eee; align-items: center; font-size: 0.83rem; }
.preview-course-row.pass-row { background: #F0FFF4; border-left: 3px solid #2E7D32; }
.preview-course-row.prog-row { background: #FFF8F0; border-left: 3px solid #E65100; }
.cname { font-weight: 600; color: #1a1a1a; }
.cpass { color: #2E7D32; font-weight: 700; font-size: 0.78rem; }
.cprog { color: #E65100; font-weight: 700; font-size: 0.78rem; }
.cdate { color: #666; font-size: 0.76rem; line-height: 1.4; }
.preview-footer { text-align: center; padding: 10px; font-size: 0.72rem; color: #bbb; border-top: 1px solid #eee; font-style: italic; background: #fafafa; }
</style>
""", unsafe_allow_html=True)


# ── Navigation items ──────────────────────────────────────────────────────────
NAV_ITEMS = [
    ("📤", "Upload & Process"),
    ("👥", "Preview Workers"),
    ("📄", "Generate PDFs"),
    ("🔍", "Batch Lookup"),
    ("✏️", "Export CSV"),
    ("🏆", "LIUNA Certificates"),
    ("📊", "Learner Summary"),
    ("⚙️", "Settings"),
]

# ── Session state defaults ────────────────────────────────────────────────────
for key, default in [
    ("people",    []),
    ("courses",   []),
    ("use_color", True),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def load_csvs(uploaded_files) -> None:
    """Process uploaded CSVs into session state (only when the file set changes)."""
    sig = tuple((f.name, f.size) for f in uploaded_files)
    if st.session_state.get("loaded_sig") == sig:
        return
    with st.spinner("Processing files…"):
        people, courses = process_files(uploaded_files)
    st.session_state.people      = people
    st.session_state.courses     = courses
    st.session_state.loaded_sig  = sig
    st.session_state.loaded_names = [f.name for f in uploaded_files]
    # Keep the raw files too, so pages with their own parser (LIUNA
    # Certificates) can reuse whatever was dropped on any page.
    shared, seen = [], set()
    for f in uploaded_files:
        data = f.getvalue()
        h = hashlib.md5(data).hexdigest()
        if h not in seen:
            seen.add(h)
            shared.append((f.name, data))
    st.session_state.loaded_files = shared
    # Default report dates = earliest → latest date found in these CSVs
    start, end = data_date_span(people)
    if start:
        st.session_state.report_range = (start, end)
    st.session_state._just_loaded = len(people)
    st.rerun()  # redraw the sidebar (report dates, loaded-data box) right away


def require_data(page_key: str) -> bool:
    """
    Every data page gets its own uploader so you never have to leave the page.
    No data yet  → show the uploader front and centre.
    Data loaded  → show what's loaded, with a collapsed uploader to swap files.
    """
    has_data = bool(st.session_state.people)
    just = st.session_state.pop("_just_loaded", None)
    if just:
        st.success(f"✅ Loaded {just} workers. Report dates were filled in from the CSV — "
                   "check them in the sidebar under **Report Period**.")
    if has_data:
        n_files = len(st.session_state.get("loaded_names", [])) or "?"
        box = st.expander(
            f"📤 {len(st.session_state.people)} workers loaded from {n_files} file(s) "
            "— click to load different CSVs"
        )
    else:
        box = st.container()
        hint = box.empty()
        hint.info("⬆️ No data loaded yet — drop your CSV export(s) here to get started.")

    files = box.file_uploader(
        "Upload CSV files", type=["csv"], accept_multiple_files=True,
        key=f"page_upload_{page_key}", label_visibility="collapsed",
    )
    if files:
        load_csvs(files)
        if not has_data:
            hint.success(f"✅ Loaded {len(st.session_state.people)} workers.")
    return bool(st.session_state.people)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <h1>📋 Transcript Generator</h1>
        <p>Construction Workforce Safety</p>
    </div>
    <div class="nav-section-label">Navigation</div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "nav",
        [label for _, label in NAV_ITEMS],
        label_visibility="collapsed",
        key="nav_radio",
    )

    # Render nav items with active highlight
    nav_html = "".join(
        f'<div class="nav-item {"active" if page == label else ""}">{icon}&nbsp;&nbsp;{label}</div>'
        for icon, label in NAV_ITEMS
    )
    st.markdown(nav_html, unsafe_allow_html=True)

    # Loaded-data summary
    if st.session_state.people:
        ppl      = st.session_state.people
        crs      = st.session_state.courses
        passed_n = sum(1 for p in ppl if any("pass" in c["status"].lower() for c in p["courses"]))
        st.markdown(f"""
        <div style="padding:16px 12px 0;">
          <div style="background:rgba(255,255,255,0.08);border-radius:10px;padding:14px 16px;">
            <div style="font-size:0.62rem;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">Loaded Data</div>
            <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
              <span style="color:rgba(255,255,255,0.6);font-size:0.8rem;">Workers</span>
              <span style="color:#fff;font-weight:700;font-family:'DM Mono',monospace;">{len(ppl)}</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
              <span style="color:rgba(255,255,255,0.6);font-size:0.8rem;">Courses</span>
              <span style="color:#fff;font-weight:700;font-family:'DM Mono',monospace;">{len(crs)}</span>
            </div>
            <div style="display:flex;justify-content:space-between;">
              <span style="color:rgba(255,255,255,0.6);font-size:0.8rem;">Passed</span>
              <span style="color:#C9A84C;font-weight:700;font-family:'DM Mono',monospace;">{passed_n}</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)


# ── Report period (sidebar) ───────────────────────────────────────────────────
def _month_span(d):
    import calendar
    return d.replace(day=1), d.replace(day=calendar.monthrange(d.year, d.month)[1])


with st.sidebar:
    from datetime import date as _date
    st.markdown('<div class="nav-section-label">Report Period</div>', unsafe_allow_html=True)
    st.session_state.setdefault("report_name", "Learners Transcript Report")
    st.text_input("Report name", key="report_name")
    st.session_state.setdefault("report_range", _month_span(_date.today()))
    # One stored range (report_range) drives every date picker. The pickers
    # have no widget key on purpose, so they redraw whenever it changes
    # (new CSVs loaded, or dates typed on another page).
    _rng = st.date_input("Report dates (from – to)", value=st.session_state.report_range,
                         format="MM/DD/YYYY")
    if isinstance(_rng, (tuple, list)) and len(_rng) == 2 and tuple(_rng) != st.session_state.report_range:
        st.session_state.report_range = tuple(_rng)
    st.caption("Printed on transcripts and used as the file name:  \n**"
               + format_report_title(st.session_state.report_name, *st.session_state.report_range) + "**")


def report_title() -> str:
    return format_report_title(st.session_state.get("report_name", ""),
                               *st.session_state.get("report_range", (None, None)))


def report_base() -> str:
    return report_filename(report_title())


def pdf_opts() -> dict:
    """Title + Michigan-time stamp for every transcript PDF built right now."""
    return {"report_title": report_title(), "printed_at": now_stamp()}


# ── Preview modal ─────────────────────────────────────────────────────────────
@st.dialog("Transcript Preview", width="large")
def show_preview_modal(person: dict, use_color: bool) -> None:
    # Flatten to one line: indented/blank lines inside the HTML make Markdown
    # show part of the preview as raw code instead of rendering it.
    preview_html = " ".join(line.strip() for line in build_preview_html(person, report_title()).splitlines())
    st.markdown(preview_html, unsafe_allow_html=True)
    st.markdown("")
    pdf_bytes = build_person_pdf(person, use_color=use_color, **pdf_opts())
    safe_name = re.sub(r"[^\w\-]", "_", person["name"] or "transcript")
    dcol, pcol = st.columns(2)
    with dcol:
        st.download_button(
            "⬇️ Download this transcript as PDF",
            data=pdf_bytes,
            file_name=f"{safe_name}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )
    with pcol:
        print_pdf_button(pdf_bytes, "🖨️ Print this transcript")


def print_pdf_button(pdf_bytes: bytes, label: str = "🖨️ Print") -> None:
    """
    A button that opens the PDF in a new browser tab, ready to print
    (the browser's PDF viewer has a print icon, or press Ctrl+P).
    Nothing is saved anywhere — the PDF lives only in this browser tab.
    """
    b64 = base64.b64encode(pdf_bytes).decode()
    components.html(f"""
    <button id="p" style="width:100%;height:38px;border:1px solid #1B3A6B;border-radius:8px;
            background:#fff;color:#1B3A6B;font:600 14px sans-serif;cursor:pointer;">{label}</button>
    <div id="m" style="font:12px sans-serif;color:#b00;margin-top:4px;"></div>
    <script>
    document.getElementById("p").onclick = function () {{
        const bin = atob("{b64}");
        const buf = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
        const url = URL.createObjectURL(new Blob([buf], {{type: "application/pdf"}}));
        const w = window.open(url, "_blank");
        if (!w) document.getElementById("m").innerText =
            "Your browser blocked the new tab — allow pop-ups for this site, or use Download.";
    }};
    </script>""", height=62)


# ── Worker row renderer ───────────────────────────────────────────────────────
def render_worker_row(person: dict, use_color: bool, key_prefix: str = "") -> None:
    """Render one worker row with an optional 👁 preview button."""
    is_pass   = any("pass" in c["status"].lower() for c in person["courses"])
    row_cls   = "pass" if is_pass else "prog"
    badge_cls = "badge-pass" if is_pass else "badge-prog"
    badge_txt = "PASSED"      if is_pass else "IN PROGRESS"
    ssn_part  = (
        f'<span class="worker-ssn">· ••••{person["ssn4"]}</span>'
        if person.get("ssn4") else ""
    )

    col_card, col_btn = st.columns([7, 1])
    with col_card:
        # Built on one line: a blank line (e.g. no SSN) would make Markdown
        # treat the indented badge HTML as a code block and show raw tags.
        st.markdown(
            f'<div class="worker-row {row_cls}">'
            f'<span class="worker-name">{person["name"]}</span> '
            f'<span class="worker-email">{person["email"]}</span> '
            f'{ssn_part} '
            f'<span class="badge {badge_cls}">{badge_txt}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_btn:
        if st.button("👁", key=f"{key_prefix}prev_{person['email']}",
                     use_container_width=True, help=f"Preview {person['name']}"):
            show_preview_modal(person, use_color)


# ══════════════════════════════════════════════════════════════════════════════
# ── Page: Upload & Process ────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
if page == "Upload & Process":
    st.markdown("""
    <div class="page-header">
        <h2>📤 Upload &amp; Process</h2>
        <p>Drop one or more CSV exports — each file is treated as a separate course</p>
    </div>""", unsafe_allow_html=True)

    st.markdown(
        '<div class="upload-hint">Supported columns: Name · Email · Course result · '
        'Finished · Started · Last 4 digits of Social</div>',
        unsafe_allow_html=True,
    )

    uploaded_files = st.file_uploader(
        "Upload CSV files", type=["csv"],
        accept_multiple_files=True, label_visibility="collapsed",
    )

    if uploaded_files:
        load_csvs(uploaded_files)
        st.session_state.pop("_just_loaded", None)  # this page shows its own summary
        people  = st.session_state.people
        courses = st.session_state.courses

        passed = sum(1 for p in people if any("pass" in c["status"].lower() for c in p["courses"]))
        st.markdown(f"""
        <div class="stat-row">
            <div class="stat-box"><div class="stat-num">{len(people)}</div><div class="stat-label">Workers</div></div>
            <div class="stat-box"><div class="stat-num">{len(courses)}</div><div class="stat-label">Courses</div></div>
            <div class="stat-box"><div class="stat-num">{passed}</div><div class="stat-label">Passed</div></div>
            <div class="stat-box"><div class="stat-num">{len(people) - passed}</div><div class="stat-label">In Progress</div></div>
        </div>""", unsafe_allow_html=True)

        st.success(f"✅ Loaded {len(uploaded_files)} file(s). Use the sidebar to navigate. "
                   "Report dates were filled in from the CSV — check them in the sidebar under **Report Period**.")

        st.markdown('<div class="section-label">Detected Courses</div>', unsafe_allow_html=True)
        for i, c in enumerate(courses, 1):
            st.markdown(f"**{i}.** {c}")
    else:
        st.markdown("""
        <div class="info-card">
            <h4>How it works</h4>
            <p>
                1. Upload one or more CSV files from your training platform.<br>
                2. Each file is auto-detected as a course from its filename or columns.<br>
                3. Workers are matched across files by email address.<br>
                4. Navigate via sidebar to preview, generate PDFs, batch lookup, or export.
            </p>
        </div>
        <div class="info-card">
            <h4>Course keyword detection</h4>
            <p>
                <b>asbestos</b> → Asbestos Awareness &nbsp;·&nbsp;
                <b>covid</b> → COVID-19 for the Construction Workforce<br>
                <b>lead</b> → Lead Awareness Worker &nbsp;·&nbsp;
                <b>hazard</b> → Hazard Communication
            </p>
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ── Page: Preview Workers ─────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Preview Workers":
    st.markdown("""
    <div class="page-header">
        <h2>👥 Preview Workers</h2>
        <p>Green rows = passed · Orange rows = in progress · Click 👁 to preview transcript</p>
    </div>""", unsafe_allow_html=True)

    if not require_data("preview"):
        st.stop()

    people    = st.session_state.people
    use_color = st.session_state.use_color

    col_search, col_filter = st.columns([3, 1])
    with col_search:
        search_q = st.text_input("Search", placeholder="🔎  Search by name or email…",
                                 label_visibility="collapsed")
    with col_filter:
        status_filter = st.selectbox("Status", ["All", "Passed", "In Progress"],
                                     label_visibility="collapsed")

    filtered = people
    if search_q:
        q        = search_q.lower()
        filtered = [p for p in filtered if q in p["name"].lower() or q in p["email"].lower()]
    if status_filter == "Passed":
        filtered = [p for p in filtered if any("pass" in c["status"].lower() for c in p["courses"])]
    elif status_filter == "In Progress":
        filtered = [p for p in filtered if not any("pass" in c["status"].lower() for c in p["courses"])]

    st.markdown(f'<div class="section-label">{len(filtered)} worker(s) shown</div>',
                unsafe_allow_html=True)

    for person in filtered:
        render_worker_row(person, use_color, key_prefix="wp_")


# ══════════════════════════════════════════════════════════════════════════════
# ── Page: Generate PDFs ───────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Generate PDFs":
    st.markdown("""
    <div class="page-header">
        <h2>📄 Generate PDFs</h2>
        <p>Download transcripts for all workers — merged or as individual files in a ZIP</p>
    </div>""", unsafe_allow_html=True)

    if not require_data("generate"):
        st.stop()

    people = st.session_state.people
    total  = len(people)

    st.markdown('<div class="section-label">PDF Color Mode</div>', unsafe_allow_html=True)
    color_toggle = st.checkbox(
        "🖨️ Color PDFs (uncheck for grayscale / print-friendly)",
        value=st.session_state.use_color,
    )
    st.session_state.use_color = color_toggle

    st.markdown('<div class="section-label">Download Options</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""<div class="info-card"><h4>📄 Merged PDF</h4>
        <p>All workers in one multi-page PDF, sorted alphabetically.</p></div>""",
                    unsafe_allow_html=True)
        if st.button(f"Build Merged PDF ({total} workers)", use_container_width=True, type="primary"):
            with st.spinner(f"Building {total} transcripts…"):
                merged = merge_pdfs([build_person_pdf(p, use_color=color_toggle, **pdf_opts()) for p in people])
            st.download_button(
                "⬇️ Download PDF",
                data=merged, file_name=f"{report_base()}.pdf",
                mime="application/pdf", use_container_width=True,
            )

    with col2:
        st.markdown("""<div class="info-card"><h4>🗂 Individual ZIP</h4>
        <p>One PDF per worker, named by employee, packaged into a ZIP.</p></div>""",
                    unsafe_allow_html=True)
        if st.button("Package Individual PDFs (ZIP)", use_container_width=True):
            with st.spinner("Packaging…"):
                zip_bytes = build_zip(people, use_color=color_toggle, **pdf_opts())
            st.download_button(
                "⬇️ Download ZIP",
                data=zip_bytes, file_name=f"{report_base()}.zip",
                mime="application/zip", use_container_width=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# ── Page: Batch Lookup ────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Batch Lookup":
    st.markdown("""
    <div class="page-header">
        <h2>🔍 Batch Lookup</h2>
        <p>Paste or upload emails, names, or last 4 of SSN — only matched workers get transcripts</p>
    </div>""", unsafe_allow_html=True)

    if not require_data("batch"):
        st.stop()

    people    = st.session_state.people
    use_color = st.session_state.use_color

    tab1, tab2    = st.tabs(["✏️ Paste List", "📁 Upload File"])
    batch_entries = []

    with tab1:
        raw_input = st.text_area(
            "Lookup list", height=160,
            placeholder="One per line — mix and match:\njane.doe@example.com\nKevin Clark\n0900",
            label_visibility="collapsed",
        )
        if raw_input.strip():
            batch_entries = parse_lookup_list(raw_input)
            if batch_entries:
                st.caption(f"Looking up **{len(batch_entries)}** entr{'y' if len(batch_entries) == 1 else 'ies'}.")
            else:
                st.warning("Nothing to look up in the pasted text.")

    with tab2:
        list_file = st.file_uploader("Upload .txt or .csv", type=["txt", "csv"],
                                      key="batch_email_file")
        if list_file:
            batch_entries = parse_lookup_list(list_file.getvalue().decode("utf-8-sig", errors="ignore"))
            if batch_entries:
                st.caption(f"Looking up **{len(batch_entries)}** entr{'y' if len(batch_entries) == 1 else 'ies'}.")
            else:
                st.warning("Nothing to look up in that file.")

    if batch_entries:
        results   = lookup_people(batch_entries, people)
        matched, seen = [], set()
        for _, _, hits in results:
            for p in hits:
                if p["email"].lower() not in seen:
                    seen.add(p["email"].lower())
                    matched.append(p)
        unmatched = [(e, k) for e, k, hits in results if not hits]
        multi     = [(e, k, hits) for e, k, hits in results if len(hits) > 1]

        chips = (
            "".join(f'<span class="match-chip">✓ {p["name"] or p["email"]}</span>' for p in matched) +
            "".join(f'<span class="nomatch-chip">✗ {e}</span>' for e, _ in unmatched)
        )
        st.markdown(f"""
        <div style="margin:8px 0 14px;">
            <strong style="font-size:0.85rem;color:#1B3A6B;">
                {len(matched)} matched · {len(unmatched)} not found
            </strong><br><br>{chips}
        </div>""", unsafe_allow_html=True)

        if multi:
            with st.expander(f"⚠️ {len(multi)} entr{'y' if len(multi) == 1 else 'ies'} matched more than one worker — check these", expanded=True):
                for e, k, hits in multi:
                    who = "; ".join(f"{p['name']} ({p['email']})" for p in hits)
                    st.markdown(f"- **{e}** ({k}) → {who}")
                st.caption("All of them are included below. Use an email to pick just one.")

        if unmatched:
            with st.expander(f"⚠️ {len(unmatched)} not found"):
                for e, k in unmatched:
                    st.markdown(f"- `{e}` ({k})")

        if matched:
            st.markdown('<div class="section-label">Matched Workers</div>', unsafe_allow_html=True)
            for person in matched:
                render_worker_row(person, use_color, key_prefix="bl_")

            st.markdown('<div class="section-label">Print or Download Transcripts</div>',
                        unsafe_allow_html=True)
            st.caption("Tip: click 👁 on any row above to preview, print or download just that person.")
            bcol1, bcol2 = st.columns(2)

            with bcol1:
                if st.button(f"🖨️ Print / 📄 Merged PDF ({len(matched)} workers)",
                              use_container_width=True, type="primary"):
                    with st.spinner("Building transcripts…"):
                        batch_merged = merge_pdfs(
                            [build_person_pdf(p, use_color=use_color, **pdf_opts()) for p in matched]
                        )
                    print_pdf_button(batch_merged, f"🖨️ Print all {len(matched)} transcripts")
                    st.download_button(
                        "⬇️ Download PDF",
                        data=batch_merged, file_name=f"{report_base()}_Batch.pdf",
                        mime="application/pdf", use_container_width=True,
                    )

            with bcol2:
                if st.button(f"🗂 Individual ZIP ({len(matched)} PDFs)", use_container_width=True):
                    with st.spinner("Packaging…"):
                        zip_bytes = build_zip(matched, use_color=use_color, **pdf_opts())
                    st.download_button(
                        "⬇️ Download ZIP",
                        data=zip_bytes, file_name=f"{report_base()}_Batch.zip",
                        mime="application/zip", use_container_width=True,
                    )
        else:
            st.warning("Nothing you entered matched any workers in the loaded CSVs.")


# ══════════════════════════════════════════════════════════════════════════════
# ── Page: Export CSV ──────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Export CSV":
    st.markdown("""
    <div class="page-header">
        <h2>✏️ Export CSV</h2>
        <p>A clean, fully-structured export — preview below before downloading</p>
    </div>""", unsafe_allow_html=True)

    if not require_data("export"):
        st.stop()

    people = st.session_state.people

    st.markdown("""<div class="info-card"><h4>Exported Fields</h4>
    <p><b>Name</b> · <b>Email</b> · <b>SSN Last 4</b> · <b>Course</b> · <b>Status</b> ·
    <b>Started Date</b> · <b>Completion Date</b> · <b>Passed</b> (Yes / No)</p>
    </div>""", unsafe_allow_html=True)

    preview_rows = [
        {
            "Name":            p["name"],
            "Email":           p["email"],
            "SSN Last 4":      p.get("ssn4") or "",
            "Course":          c["course"],
            "Status":          c["status"],
            "Started Date":    c.get("started_date") or "",
            "Completion Date": c.get("completion_date") or "",
            "Passed":          "Yes" if "pass" in c["status"].lower() else "No",
        }
        for p in people
        for c in p["courses"]
    ]

    st.markdown('<div class="section-label">Data Preview</div>', unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, height=340)

    total_rows = len(preview_rows)
    st.markdown(
        f'<div class="section-label">{total_rows} rows · {len(people)} workers · '
        f'{len(st.session_state.courses)} courses</div>',
        unsafe_allow_html=True,
    )

    st.download_button(
        "⬇️ Download combined.csv",
        data=build_clean_csv(people),
        file_name="combined.csv",
        mime="text/csv",
        use_container_width=True,
        type="primary",
    )


# ══════════════════════════════════════════════════════════════════════════════
# ── Page: LIUNA Certificates ──────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
elif page == "LIUNA Certificates":
    st.markdown("""
    <div class="page-header">
        <h2>🏆 LIUNA Certificates</h2>
        <p>Upload one or more class CSVs and generate landscape completion certificates</p>
    </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div class="info-card">
        <h4>CSV Format</h4>
        <p>
            Drop in multiple files at once — one per class works well (e.g. an EasyGenerator
            export per course). Each file's class name comes from its filename, and only
            passed students are included, with their real completion date. A student who
            appears in more than one file (matched by email) gets one certificate per class,
            all under their name.<br><br>
            Also supports the older LIUNA class-information CSV format (no header row,
            columns read by position: Col 2 = Class name, Col 7 = Hours, Col 10 = Completion
            date, Col 11 = Member ID, Col 12 = Last name, Col 13 = First name).
        </p>
    </div>""", unsafe_allow_html=True)

    liuna_files = st.file_uploader(
        "Upload LIUNA CSV(s)", type=["csv"], key="liuna_csv",
        label_visibility="collapsed",
        accept_multiple_files=True,
    )

    st.markdown('<div class="section-label">Organization Details</div>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        org_name  = st.text_input("Organization name",  value="LIUNA Training of Michigan")
        org_addr  = st.text_input("Street address",     value="11155 Beardslee Road")
        org_city  = st.text_input("City, State ZIP",    value="Perry, MI 48872")
    with col_b:
        org_phone = st.text_input("Phone",              value="(517) 625-4919")
        dir_name  = st.text_input("Director full name", value="")
        dir_title = st.text_input("Director title",     value="Director")

    # Files dropped here win; otherwise reuse the CSVs already loaded on
    # Upload & Process (or any other page) so you only upload once.
    cert_sources, seen = [], set()
    if liuna_files:
        for f in liuna_files:
            data = f.getvalue()
            h = hashlib.md5(data).hexdigest()
            if h not in seen:                     # skip exact duplicate files
                seen.add(h)
                cert_sources.append((f.name, data))
    elif st.session_state.get("loaded_files"):
        cert_sources = st.session_state.loaded_files
        st.info(
            f"📎 Using the {len(cert_sources)} CSV file(s) you already loaded "
            f"({', '.join(n for n, _ in cert_sources)}). Drop files above to use different ones."
        )

    if cert_sources:
        per_file_groups = []
        for fname, data in cert_sources:
            raw_text = data.decode("utf-8-sig", errors="ignore")
            try:
                per_file_groups.append(load_csv_from_text(raw_text, filename=fname))
            except Exception as exc:
                st.error(f"Failed to parse {fname}: {exc}")
                st.stop()

        groups = merge_groups(*per_file_groups)

        total_students = len(groups)
        total_certs    = sum(len(g["certs"]) for g in groups.values())

        st.markdown(f"""
        <div class="stat-row">
            <div class="stat-box"><div class="stat-num">{total_students}</div><div class="stat-label">Students</div></div>
            <div class="stat-box"><div class="stat-num">{total_certs}</div><div class="stat-label">Certificates</div></div>
        </div>""", unsafe_allow_html=True)

        with st.expander("👥 Preview students"):
            for mid, group in groups.items():
                cert_count = len(group["certs"])
                classes = ", ".join(sorted({c["cls"] for c in group["certs"]}))
                st.markdown(
                    f"**{group['name']}** &nbsp;<span style='color:#999;font-size:0.8em'>"
                    f"· {mid} · {cert_count} cert{'s' if cert_count > 1 else ''} · {classes}</span>",
                    unsafe_allow_html=True,
                )

        st.markdown('<div class="section-label">Download Certificates</div>', unsafe_allow_html=True)
        lcol1, lcol2 = st.columns(2)

        org_kwargs = dict(
            org_name=org_name, org_addr=org_addr,
            org_city=org_city,  org_phone=org_phone,
            dir_name=dir_name,  dir_title=dir_title,
        )

        with lcol1:
            st.markdown("""<div class="info-card"><h4>📄 Merged PDF</h4>
            <p>All students in one PDF, one certificate per page.</p></div>""",
                        unsafe_allow_html=True)
            if st.button(f"Build Merged PDF ({total_certs} certificates)",
                          use_container_width=True, type="primary"):
                with st.spinner("Generating certificates…"):
                    merged_bytes = generate_pdfs_merged(groups, **org_kwargs)
                st.download_button(
                    "⬇️ Download LIUNA_Certificates.pdf",
                    data=merged_bytes, file_name="LIUNA_Certificates.pdf",
                    mime="application/pdf", use_container_width=True,
                )

        with lcol2:
            st.markdown("""<div class="info-card"><h4>🗂 Individual ZIP</h4>
            <p>One PDF per student (multi-page if multiple courses), packaged in a ZIP.</p></div>""",
                        unsafe_allow_html=True)
            if st.button(f"Package Individual PDFs ({total_students} students)",
                          use_container_width=True):
                with st.spinner("Packaging…"):
                    zip_bytes = generate_pdfs_to_zip(groups, **org_kwargs)
                st.download_button(
                    "⬇️ Download LIUNA_Certificates.zip",
                    data=zip_bytes, file_name="LIUNA_Certificates.zip",
                    mime="application/zip", use_container_width=True,
                )

        st.markdown('<div class="section-label">Print One Certificate</div>', unsafe_allow_html=True)
        st.markdown("""<div class="info-card"><h4>🔎 Single Lookup</h4>
        <p>Pick one student and download just their certificate(s) — no batch or ZIP needed.</p></div>""",
                    unsafe_allow_html=True)

        lookup_keys = sorted(groups.keys(), key=lambda k: groups[k]["name"].lower())

        def _lookup_label(k: str) -> str:
            g = groups[k]
            n = len(g["certs"])
            return f"{g['name']}  ·  {g['mid']}  ·  {n} cert{'s' if n != 1 else ''}"

        selected_key = st.selectbox(
            "Student", options=lookup_keys, format_func=_lookup_label,
            label_visibility="collapsed", key="liuna_single_lookup",
        )

        if selected_key:
            selected_group = groups[selected_key]
            single_fname = safe_filename(selected_group["name"], selected_group["mid"])
            if st.button(f"Build Certificate — {selected_group['name']}",
                          use_container_width=True, type="primary"):
                with st.spinner("Generating certificate…"):
                    single_bytes = generate_single_pdf(selected_group, **org_kwargs)
                st.download_button(
                    f"⬇️ Download {single_fname}",
                    data=single_bytes, file_name=single_fname,
                    mime="application/pdf", use_container_width=True,
                )
    else:
        st.markdown("""
        <div class="upload-hint">⬆️ Upload one or more class CSVs above to get started</div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ── Page: Learner Summary ─────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Learner Summary":
    st.markdown("""
    <div class="page-header">
        <h2>📊 Learner Summary</h2>
        <p>Upload a full LMS learner export to see a monthly course-completion summary</p>
    </div>""", unsafe_allow_html=True)

    st.markdown(
        '<div class="upload-hint">Expects a learner CSV export with Name, Email, Last active, '
        'Total number of courses, Passed courses, and one column per course</div>',
        unsafe_allow_html=True,
    )

    summary_file = st.file_uploader(
        "Upload learner CSV", type=["csv"], key="learner_summary_csv",
        label_visibility="collapsed",
    )

    if summary_file:
        try:
            report = LearnersReport(summary_file)
        except Exception as exc:
            st.error(f"Couldn't parse this CSV: {exc}")
            st.stop()

        # New learner export → default the sidebar report dates to its month
        _sig = (summary_file.name, summary_file.size)
        if st.session_state.get("summary_sig") != _sig:
            st.session_state.summary_sig = _sig
            try:
                from datetime import datetime as _dt
                _m = _dt.strptime(report.report_month, "%B %Y").date()
                st.session_state.report_range = _month_span(_m)
                st.rerun()
            except ValueError:
                pass

        # Report period — typed in by hand; starts at the export's month
        st.markdown('<div class="section-label">📅 Report Period</div>', unsafe_allow_html=True)
        _pr = st.date_input(
            "Report period for this learner report (from – to)",
            value=st.session_state.report_range, format="MM/DD/YYYY",
            help="Used on this page, the HTML report, and the transcripts below. "
                 "Also shown in the sidebar under Report Period.",
        )
        if isinstance(_pr, (tuple, list)) and len(_pr) == 2 and tuple(_pr) != st.session_state.report_range:
            st.session_state.report_range = tuple(_pr)
            st.rerun()  # keep the sidebar picker in step
        _span = format_span(*st.session_state.report_range)
        if _span:
            report.report_month = _span   # heading + HTML report use the typed span
        st.caption(f"Transcripts will be titled: **{report_title()}**")

        st.markdown(f"""
        <div class="stat-row">
            <div class="stat-box"><div class="stat-num">{report.total_students}</div><div class="stat-label">Students</div></div>
            <div class="stat-box"><div class="stat-num">{report.students_with_completions}</div><div class="stat-label">With Completions</div></div>
            <div class="stat-box"><div class="stat-num">{report.students_no_completions}</div><div class="stat-label">No Completions</div></div>
            <div class="stat-box"><div class="stat-num">{report.total_completions}</div><div class="stat-label">Total Completions</div></div>
        </div>""", unsafe_allow_html=True)

        st.markdown(
            f'<div class="section-label">{report.report_month} · '
            f'{report.total_courses_with_completions} course(s) with activity</div>',
            unsafe_allow_html=True,
        )

        if report.course_summary:
            summary_rows = [
                {
                    "Course": course,
                    "Completions": count,
                    "% of Class": f"{round(count / report.total_students * 100)}%",
                }
                for course, count in report.course_summary.items()
            ]
            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No completed courses found in this file.")

        st.markdown('<div class="section-label">Student Breakdown</div>', unsafe_allow_html=True)
        student_search = st.text_input(
            "Search students", placeholder="🔎  Search by name or email…",
            label_visibility="collapsed", key="learner_summary_search",
        )

        student_records = report.student_rows
        if student_search:
            q = student_search.lower()
            student_records = [
                s for s in student_records
                if q in s["name"].lower() or q in s["email"].lower()
            ]

        student_table = pd.DataFrame([
            {
                "Name":        s["name"],
                "Email":       s["email"],
                "Passed":      s["passed_count"],
                "Passed Courses": ", ".join(s["passed"]) if s["passed"] else "—",
                "In Progress": ", ".join(s["in_progress"]) if s["in_progress"] else "—",
            }
            for s in student_records
        ])
        st.dataframe(student_table, use_container_width=True, hide_index=True, height=340)
        st.caption(f"{len(student_records)} of {report.total_students} student(s) shown")

        st.download_button(
            "⬇️ Download HTML Report",
            data=report.to_html_string(),
            file_name=f"Learners_Summary_{report_filename(report.report_month)}.html",
            mime="text/html",
            use_container_width=True,
            type="primary",
        )

        st.markdown('<div class="section-label">Generate Transcripts</div>', unsafe_allow_html=True)
        st.caption(
            "Built from this report — email and last-4 SSN aren't in this CSV format, so those "
            "show as a dash, and Completion Date is left blank since this file only has one "
            "overall \"Last active\" date per student, not one per class."
        )
        transcript_color = st.checkbox(
            "🖨️ Color PDFs (uncheck for grayscale / print-friendly)",
            value=st.session_state.use_color, key="learner_summary_color",
        )
        st.session_state.use_color = transcript_color

        transcript_people = [p for p in report.to_transcript_people() if p["courses"]]
        gcol1, gcol2 = st.columns(2)

        with gcol1:
            st.markdown("""<div class="info-card"><h4>📄 Merged PDF</h4>
            <p>One transcript per student who's taken at least one class, sorted alphabetically.</p></div>""",
                        unsafe_allow_html=True)
            if st.button(f"Build Merged PDF ({len(transcript_people)} students)",
                          use_container_width=True, type="primary", key="learner_summary_merged_btn"):
                with st.spinner(f"Building {len(transcript_people)} transcripts…"):
                    merged = merge_pdfs([build_person_pdf(p, use_color=transcript_color, **pdf_opts()) for p in transcript_people])
                st.download_button(
                    "⬇️ Download PDF",
                    data=merged, file_name=f"{report_base()}.pdf",
                    mime="application/pdf", use_container_width=True, key="learner_summary_merged_dl",
                )

        with gcol2:
            st.markdown("""<div class="info-card"><h4>🗂 Individual ZIP</h4>
            <p>One PDF per student, named by student, packaged into a ZIP.</p></div>""",
                        unsafe_allow_html=True)
            if st.button(f"Package Individual PDFs ({len(transcript_people)} students)",
                          use_container_width=True, key="learner_summary_zip_btn"):
                with st.spinner("Packaging…"):
                    zip_bytes = build_zip(transcript_people, use_color=transcript_color, **pdf_opts())
                st.download_button(
                    "⬇️ Download ZIP",
                    data=zip_bytes, file_name=f"{report_base()}.zip",
                    mime="application/zip", use_container_width=True, key="learner_summary_zip_dl",
                )
    else:
        st.markdown("""
        <div class="info-card">
            <h4>How it works</h4>
            <p>
                Upload a full learner export from your LMS (not a per-course file — this expects
                one row per student with a column per course, like the ones the CSV Format note
                above describes). The report shows how many students completed at least one
                course, how many haven't yet, a ranked breakdown of completions per course for
                the reporting month, and a searchable student-by-student table listing exactly
                which courses each person has passed and which are still in progress.
            </p>
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ── Page: Settings ────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Settings":
    st.markdown("""
    <div class="page-header">
        <h2>⚙️ Settings</h2>
        <p>PDF output options, course keyword detection, and app information</p>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-label">PDF Color Mode</div>', unsafe_allow_html=True)
    use_color = st.checkbox(
        "🖨️ Color PDFs (uncheck for grayscale / print-friendly)",
        value=st.session_state.use_color,
    )
    st.session_state.use_color = use_color

    st.markdown('<div class="section-label">Course Keyword Detection</div>', unsafe_allow_html=True)
    st.markdown("""<div class="info-card"><h4>How course names are auto-detected</h4>
    <p>Keywords are matched against the uploaded filename and column headers.
    If no keyword matches, the filename is used as the course name.</p>
    </div>""", unsafe_allow_html=True)

    kw_df = pd.DataFrame([
        {"Keyword (filename / columns)": k, "Detected Course Name": v}
        for k, v in COURSE_KEYWORDS.items()
    ])
    st.dataframe(kw_df, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-label">About</div>', unsafe_allow_html=True)
    st.markdown("""<div class="info-card"><h4>Training &amp; Certificate Generator</h4>
    <p>
        Built for Construction Workforce Safety Training.<br>
        Upload CSV exports → auto-detect courses → generate printable PDF transcripts.<br>
        Workers are matched across multiple course files by email address.<br>
        LIUNA certificates are generated separately from the class-information CSV.<br><br>
        <b>Requires:</b> Streamlit 1.32+ · reportlab · pypdf · pandas
    </p></div>""", unsafe_allow_html=True)
