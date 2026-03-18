import streamlit as st
import pandas as pd
import re
import io
import zipfile
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from pypdf import PdfWriter, PdfReader

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Training Transcript Generator",
    page_icon="📋",
    layout="wide"
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
    width: 140px; height: 140px; background: rgba(201,168,76,0.14); border-radius: 50%;
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
.badge { font-size: 0.72rem; font-weight: 700; padding: 2px 9px; border-radius: 20px; margin-left: 10px; white-space: nowrap; }
.badge-pass { background: #C8E6C9; color: #1B5E20; }
.badge-prog { background: #FFE0B2; color: #BF360C; }

.section-label {
    font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; color: #999; margin: 20px 0 8px;
}
.upload-hint {
    background: #fff; border: 2px dashed #C9A84C; border-radius: 12px;
    padding: 18px 22px; text-align: center; color: #777; font-size: 0.84rem; margin-bottom: 8px;
}
.match-chip {
    display: inline-block; background: #E8F5E9; color: #2E7D32;
    border-radius: 20px; padding: 2px 10px; font-size: 0.76rem; font-weight: 600; margin: 3px 4px 3px 0;
}
.nomatch-chip {
    display: inline-block; background: #FFF3E0; color: #E65100;
    border-radius: 20px; padding: 2px 10px; font-size: 0.76rem; font-weight: 600; margin: 3px 4px 3px 0;
}
.info-card {
    background: #fff; border: 1px solid #E8E4DB; border-radius: 10px;
    padding: 16px 20px; margin-bottom: 14px;
}
.info-card h4 { margin: 0 0 6px; color: #1B3A6B; font-size: 0.95rem; }
.info-card p  { margin: 0; color: #666; font-size: 0.83rem; line-height: 1.6; }

/* Preview modal */
.preview-wrap { font-family: 'DM Sans', Arial, sans-serif; border: 1px solid #ddd; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
.preview-hdr  { background: #1B3A6B; padding: 22px 26px; text-align: center; }
.preview-hdr h3 { color: #fff; font-size: 1.1rem; font-weight: 800; margin: 0 0 2px; letter-spacing: 2px; }
.preview-hdr p  { color: #C9A84C; font-size: 0.78rem; margin: 0; }
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

# ── Course keywords ───────────────────────────────────────────────────────────
COURSE_KEYWORDS = {
    "asbestos": "Asbestos Awareness",
    "covid":    "COVID-19 for the Construction Workforce",
    "lead":     "Lead Awareness Worker",
    "hazard":   "Hazard Communication",
}

def detect_course(filename, df):
    fn = filename.lower()
    for kw, name in COURSE_KEYWORDS.items():
        if kw in fn: return name
    cols = " ".join(df.columns).lower()
    for kw, name in COURSE_KEYWORDS.items():
        if kw in cols: return name
    return filename.replace(".csv", "").replace("_", " ").strip()

# ── Data processing ───────────────────────────────────────────────────────────
def process_files(uploaded_files):
    people = {}
    course_names_seen = []
    for uf in uploaded_files:
        df = pd.read_csv(uf, encoding='utf-8-sig')
        course_name = detect_course(uf.name, df)
        if course_name not in course_names_seen:
            course_names_seen.append(course_name)
        cols    = list(df.columns)
        ssn_col = None
        for i, c in enumerate(cols):
            if 'last 4 digits' in c.lower() and 'social' in c.lower():
                if i + 1 < len(cols):
                    ssn_col = cols[i + 1]
                break
        for _, row in df.iterrows():
            name  = str(row.get('Name',  '')).strip()
            email = str(row.get('Email', '')).strip()
            if not email or email == 'nan': continue
            key      = email.lower()
            result   = str(row.get('Course result', '')).strip()
            finished = str(row.get('Finished', '')).strip()
            started  = str(row.get('Started',  '')).strip()
            def clean_date(d):
                if d in ('', '-', 'nan', 'Not finished yet'): return None
                try:    return pd.to_datetime(d).strftime('%m/%d/%Y')
                except: return d
            ssn = None
            if ssn_col:
                raw = str(row.get(ssn_col, '')).strip()
                if raw and raw not in ('-', 'nan', ''):
                    ssn = raw
            if key not in people:
                people[key] = {'name': name, 'email': email, 'ssn4': None, 'courses': []}
            if name and name != '-':
                people[key]['name'] = name
            if ssn and not people[key]['ssn4']:
                people[key]['ssn4'] = ssn
            people[key]['courses'].append({
                'course':          course_name,
                'status':          result,
                'completion_date': clean_date(finished),
                'started_date':    clean_date(started),
            })
    return sorted(people.values(), key=lambda x: x['name'].lower()), course_names_seen

# ── PDF builder ───────────────────────────────────────────────────────────────
def build_person_pdf(person, use_color=True) -> bytes:
    if use_color:
        NAVY      = colors.HexColor('#1B3A6B')
        GOLD      = colors.HexColor('#C9A84C')
        GREEN_DK  = colors.HexColor('#2E7D32')
        GREEN_LT  = colors.HexColor('#E8F5E9')
        ORANGE_DK = colors.HexColor('#E65100')
        ORANGE_LT = colors.HexColor('#FFF3E0')
    else:
        NAVY      = colors.black
        GOLD      = colors.HexColor('#888888')
        GREEN_DK  = colors.black
        GREEN_LT  = colors.HexColor('#F5F5F5')
        ORANGE_DK = colors.black
        ORANGE_LT = colors.HexColor('#EEEEEE')

    GRAY_LT = colors.HexColor('#F5F5F5')
    GRAY_BD = colors.HexColor('#DDDDDD')
    WHITE   = colors.white
    TEXT    = colors.HexColor('#2C2C2C')

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
        leftMargin=0.65*inch, rightMargin=0.65*inch,
        topMargin=0.5*inch, bottomMargin=0.65*inch)

    S = lambda n, **kw: ParagraphStyle(n, **kw)
    title_s       = S('t',  fontName='Helvetica-Bold',    fontSize=20, textColor=WHITE,    alignment=TA_CENTER)
    sub_s         = S('s',  fontName='Helvetica-Oblique', fontSize=10, textColor=GOLD,     alignment=TA_CENTER)
    label_s       = S('l',  fontName='Helvetica-Bold',    fontSize=8,  textColor=NAVY)
    value_s       = S('v',  fontName='Helvetica',         fontSize=9,  textColor=TEXT)
    sec_s         = S('se', fontName='Helvetica-Bold',    fontSize=10, textColor=WHITE,    alignment=TA_LEFT)
    course_s      = S('c',  fontName='Helvetica-Bold',    fontSize=10, textColor=TEXT)
    status_pass_s = S('sp', fontName='Helvetica-Bold',    fontSize=9,  textColor=GREEN_DK)
    status_prog_s = S('so', fontName='Helvetica-Bold',    fontSize=9,  textColor=ORANGE_DK)
    date_s        = S('d',  fontName='Helvetica',         fontSize=9,  textColor=colors.HexColor('#666666'))

    story = []

    # Header
    header_table = Table(
        [[Paragraph("TRAINING TRANSCRIPT", title_s)],
         [Paragraph("Construction Workforce Safety Training", sub_s)]],
        colWidths=[7.2*inch]
    )
    header_table.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), NAVY),
        ('TOPPADDING',    (0,0), (-1,-1), 18),
        ('BOTTOMPADDING', (0,-1), (-1,-1), 18),
        ('LEFTPADDING',   (0,0), (-1,-1), 20),
        ('RIGHTPADDING',  (0,0), (-1,-1), 20),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 16))

    # Worker info — 3 columns, SSN gets dedicated full-width cell
    name_display = person['name'] or person['email']
    ssn_val      = f"\u2022\u2022\u2022\u2022 {person['ssn4']}" if person.get('ssn4') else "\u2014"
    info_data = [
        [Paragraph("EMPLOYEE",      label_s), Paragraph("EMAIL ADDRESS",  label_s), Paragraph("SSN \u2014 LAST 4", label_s)],
        [Paragraph(name_display,    value_s), Paragraph(person['email'],  value_s), Paragraph(ssn_val,             value_s)],
    ]
    info_table = Table(info_data, colWidths=[2.2*inch, 3.3*inch, 1.7*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), GRAY_LT),
        ('BACKGROUND',    (0,1), (-1,1), WHITE),
        ('BOX',           (0,0), (-1,-1), 0.5, GRAY_BD),
        ('INNERGRID',     (0,0), (-1,-1), 0.5, GRAY_BD),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('RIGHTPADDING',  (0,0), (-1,-1), 10),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 18))

    # Section header
    sec_table = Table([[Paragraph("COURSE COMPLETIONS", sec_s)]], colWidths=[7.2*inch])
    sec_table.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), NAVY),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING',   (0,0), (-1,-1), 12),
    ]))
    story.append(sec_table)
    story.append(Spacer(1, 4))

    # Course rows — full row colored by pass/fail
    for c in person['courses']:
        is_pass      = 'pass' in c['status'].lower()
        row_bg       = GREEN_LT if is_pass else ORANGE_LT
        status_s     = status_pass_s if is_pass else status_prog_s
        status_label = c['status'] if c['status'] else '\u2014'
        comp_date    = c['completion_date'] or '\u2014'
        start_date   = c['started_date'] or '\u2014'

        row_data = [[
            Paragraph(c['course'], course_s),
            Paragraph(status_label, status_s),
            Paragraph(f"Started: {start_date}", date_s),
            Paragraph(f"Completed: {comp_date}", date_s),
        ]]
        row_table = Table(row_data, colWidths=[2.9*inch, 1.1*inch, 1.5*inch, 1.7*inch])
        row_table.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), row_bg),
            ('TOPPADDING',    (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('LEFTPADDING',   (0,0), (-1,-1), 10),
            ('RIGHTPADDING',  (0,0), (-1,-1), 6),
            ('BOX',           (0,0), (-1,-1), 0.3, GRAY_BD),
        ]))
        story.append(row_table)
        story.append(Spacer(1, 2))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GOLD))
    story.append(Spacer(1, 6))
    footer_s = S('f', fontName='Helvetica-Oblique', fontSize=8,
                 textColor=colors.HexColor('#999999'), alignment=TA_CENTER)
    story.append(Paragraph(
        "Generated by Training Transcript Generator \u00b7 Construction Workforce Safety Training",
        footer_s
    ))
    doc.build(story)
    buf.seek(0)
    return buf.read()

# ── PDF merger ────────────────────────────────────────────────────────────────
def merge_pdfs(pdf_bytes_list):
    writer = PdfWriter()
    for pdf_bytes in pdf_bytes_list:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.read()

# ── Email parser ──────────────────────────────────────────────────────────────
def parse_email_list(raw_text):
    raw    = raw_text.replace(',', '\n')
    emails = [e.strip().lower() for e in raw.splitlines() if e.strip()]
    valid  = [e for e in emails if re.match(r'^[\w\.\+\-]+@[\w\-]+\.[a-z]{2,}$', e)]
    return list(dict.fromkeys(valid))

# ── HTML preview ──────────────────────────────────────────────────────────────
def build_preview_html(person):
    name_display = person['name'] or person['email']
    ssn_display  = f"\u2022\u2022\u2022\u2022 {person['ssn4']}" if person.get('ssn4') else "\u2014"
    rows = ""
    for c in person['courses']:
        status   = c['status'] if c['status'] else '\u2014'
        comp     = c['completion_date'] or '\u2014'
        start    = c['started_date'] or '\u2014'
        is_pass  = 'pass' in status.lower()
        row_cls  = 'pass-row' if is_pass else 'prog-row'
        stat_cls = 'cpass' if is_pass else 'cprog'
        rows += f"""
        <div class="preview-course-row {row_cls}">
            <div class="cname">{c['course']}</div>
            <div class="{stat_cls}">{status}</div>
            <div class="cdate">Started<br>{start}</div>
            <div class="cdate">Completed<br>{comp}</div>
        </div>"""
    return f"""
    <div class="preview-wrap">
        <div class="preview-hdr">
            <h3>TRAINING TRANSCRIPT</h3>
            <p>Construction Workforce Safety Training</p>
        </div>
        <div class="preview-meta">
            <div class="preview-cell"><div class="lbl">Employee</div><div class="val">{name_display}</div></div>
            <div class="preview-cell"><div class="lbl">Email</div><div class="val">{person['email']}</div></div>
            <div class="preview-cell"><div class="lbl">SSN Last 4</div><div class="val">{ssn_display}</div></div>
        </div>
        <div class="preview-sec-hdr">Course Completions</div>
        {rows}
        <div class="preview-footer">Generated by Training Transcript Generator \u00b7 Construction Workforce Safety Training</div>
    </div>"""

# ── Preview modal ─────────────────────────────────────────────────────────────
@st.dialog("Transcript Preview", width="large")
def show_preview_modal(person, use_color):
    st.markdown(build_preview_html(person), unsafe_allow_html=True)
    st.markdown("")
    pdf_bytes = build_person_pdf(person, use_color=use_color)
    safe_name = re.sub(r'[^\w\-]', '_', person['name'] or 'transcript')
    st.download_button(
        "\u2b07\ufe0f Download this transcript as PDF",
        data=pdf_bytes, file_name=f"{safe_name}.pdf",
        mime="application/pdf", use_container_width=True, type="primary",
    )

# ── CSV builder ───────────────────────────────────────────────────────────────
def build_clean_csv(people):
    rows = []
    for p in people:
        for c in p['courses']:
            rows.append({
                'Name':            p['name'],
                'Email':           p['email'],
                'SSN Last 4':      p.get('ssn4') or '',
                'Course':          c['course'],
                'Status':          c['status'],
                'Started Date':    c.get('started_date') or '',
                'Completion Date': c.get('completion_date') or '',
                'Passed':          'Yes' if 'pass' in c['status'].lower() else 'No',
            })
    df = pd.DataFrame(rows, columns=[
        'Name','Email','SSN Last 4','Course','Status',
        'Started Date','Completion Date','Passed'
    ])
    return df.to_csv(index=False)

# ══════════════════════════════════════════════════════════════════════════════
# ── Session state ─────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
if 'people'    not in st.session_state: st.session_state.people    = []
if 'courses'   not in st.session_state: st.session_state.courses   = []
if 'use_color' not in st.session_state: st.session_state.use_color = True

def require_data():
    if not st.session_state.people:
        st.warning("⬆️ No data loaded yet — go to **Upload & Process** first.")
        return False
    return True

# ══════════════════════════════════════════════════════════════════════════════
# ── Sidebar ───────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
NAV_ITEMS = [
    ("📤", "Upload & Process"),
    ("👥", "Preview Workers"),
    ("📄", "Generate PDFs"),
    ("🔍", "Batch Lookup"),
    ("✏️", "Export CSV"),
    ("⚙️", "Settings"),
]

with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <h1>📋 Transcript Generator</h1>
        <p>Construction Workforce Safety</p>
    </div>
    <div class="nav-section-label">Navigation</div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "nav", [label for _, label in NAV_ITEMS],
        label_visibility="collapsed", key="nav_radio"
    )

    nav_html = ""
    for icon, label in NAV_ITEMS:
        cls = "active" if page == label else ""
        nav_html += f'<div class="nav-item {cls}">{icon}&nbsp;&nbsp;{label}</div>'
    st.markdown(nav_html, unsafe_allow_html=True)

    # Loaded data summary
    if st.session_state.people:
        ppl = st.session_state.people
        crs = st.session_state.courses
        passed_n = sum(1 for p in ppl if any('pass' in c['status'].lower() for c in p['courses']))
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

# ══════════════════════════════════════════════════════════════════════════════
# ── Page: Upload & Process ────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
if page == "Upload & Process":
    st.markdown("""
    <div class="page-header">
        <h2>📤 Upload &amp; Process</h2>
        <p>Drop one or more CSV exports — each file is treated as a separate course</p>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="upload-hint">Supported columns: Name · Email · Course result · Finished · Started · Last 4 digits of Social</div>', unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Upload CSV files", type=["csv"],
        accept_multiple_files=True, label_visibility="collapsed"
    )

    if uploaded_files:
        with st.spinner("Processing files..."):
            people, courses = process_files(uploaded_files)
            st.session_state.people  = people
            st.session_state.courses = courses

        passed = sum(1 for p in people if any('pass' in c['status'].lower() for c in p['courses']))
        st.markdown(f"""
        <div class="stat-row">
            <div class="stat-box"><div class="stat-num">{len(people)}</div><div class="stat-label">Workers</div></div>
            <div class="stat-box"><div class="stat-num">{len(courses)}</div><div class="stat-label">Courses</div></div>
            <div class="stat-box"><div class="stat-num">{passed}</div><div class="stat-label">Passed</div></div>
            <div class="stat-box"><div class="stat-num">{len(people)-passed}</div><div class="stat-label">In Progress</div></div>
        </div>""", unsafe_allow_html=True)

        st.success(f"✅ Loaded {len(uploaded_files)} file(s). Use the sidebar to navigate.")

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
            <p><b>asbestos</b> → Asbestos Awareness &nbsp;·&nbsp; <b>covid</b> → COVID-19 for the Construction Workforce<br>
            <b>lead</b> → Lead Awareness Worker &nbsp;·&nbsp; <b>hazard</b> → Hazard Communication</p>
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

    if not require_data(): st.stop()

    people    = st.session_state.people
    use_color = st.session_state.use_color

    col_search, col_filter = st.columns([3, 1])
    with col_search:
        search_q = st.text_input("Search", placeholder="🔎  Search by name or email...", label_visibility="collapsed")
    with col_filter:
        status_filter = st.selectbox("Status", ["All", "Passed", "In Progress"], label_visibility="collapsed")

    filtered = people
    if search_q:
        q = search_q.lower()
        filtered = [p for p in filtered if q in p['name'].lower() or q in p['email'].lower()]
    if status_filter == "Passed":
        filtered = [p for p in filtered if any('pass' in c['status'].lower() for c in p['courses'])]
    elif status_filter == "In Progress":
        filtered = [p for p in filtered if not any('pass' in c['status'].lower() for c in p['courses'])]

    st.markdown(f'<div class="section-label">{len(filtered)} worker(s) shown</div>', unsafe_allow_html=True)

    for p in filtered:
        is_pass   = any('pass' in c['status'].lower() for c in p['courses'])
        row_cls   = 'pass' if is_pass else 'prog'
        badge_cls = 'badge-pass' if is_pass else 'badge-prog'
        badge_txt = 'PASSED' if is_pass else 'IN PROGRESS'
        ssn_part  = f'<span class="worker-ssn">· ••••{p["ssn4"]}</span>' if p.get('ssn4') else ''

        col_card, col_btn = st.columns([7, 1])
        with col_card:
            st.markdown(f"""
            <div class="worker-row {row_cls}">
                <span class="worker-name">{p['name']}</span>
                <span class="worker-email">{p['email']}</span>
                {ssn_part}
                <span class="badge {badge_cls}">{badge_txt}</span>
            </div>""", unsafe_allow_html=True)
        with col_btn:
            if st.button("👁", key=f"prev_{p['email']}", use_container_width=True, help=f"Preview {p['name']}"):
                show_preview_modal(p, use_color)

# ══════════════════════════════════════════════════════════════════════════════
# ── Page: Generate PDFs ───────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Generate PDFs":
    st.markdown("""
    <div class="page-header">
        <h2>📄 Generate PDFs</h2>
        <p>Download transcripts for all workers — merged into one PDF or as individual files in a ZIP</p>
    </div>""", unsafe_allow_html=True)

    if not require_data(): st.stop()

    people = st.session_state.people
    total  = len(people)

    st.markdown('<div class="section-label">PDF Color Mode</div>', unsafe_allow_html=True)
    color_toggle = st.checkbox("🖨️ Color PDFs (uncheck for grayscale / print-friendly)", value=st.session_state.use_color)
    st.session_state.use_color = color_toggle

    st.markdown('<div class="section-label">Download Options</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""<div class="info-card"><h4>📄 Merged PDF</h4>
        <p>All workers in one multi-page PDF, sorted alphabetically.</p></div>""", unsafe_allow_html=True)
        if st.button(f"Build Merged PDF ({total} workers)", use_container_width=True, type="primary"):
            with st.spinner(f"Building {total} transcripts..."):
                merged = merge_pdfs([build_person_pdf(p, use_color=color_toggle) for p in people])
            st.download_button("⬇️ Download All_Transcripts.pdf",
                data=merged, file_name="All_Transcripts.pdf",
                mime="application/pdf", use_container_width=True)

    with col2:
        st.markdown("""<div class="info-card"><h4>🗂 Individual ZIP</h4>
        <p>One PDF per worker, named by employee, packaged into a ZIP.</p></div>""", unsafe_allow_html=True)
        if st.button(f"Package Individual PDFs (ZIP)", use_container_width=True):
            with st.spinner("Packaging..."):
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for p in people:
                        safe_name = re.sub(r'[^\w\-]', '_', p['name'])
                        zf.writestr(f"{safe_name}.pdf", build_person_pdf(p, use_color=color_toggle))
                zip_buf.seek(0)
            st.download_button("⬇️ Download Transcripts.zip",
                data=zip_buf, file_name="Transcripts.zip",
                mime="application/zip", use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# ── Page: Batch Lookup ────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Batch Lookup":
    st.markdown("""
    <div class="page-header">
        <h2>🔍 Batch Lookup</h2>
        <p>Paste or upload a list of emails — only matched workers get transcripts</p>
    </div>""", unsafe_allow_html=True)

    if not require_data(): st.stop()

    people          = st.session_state.people
    people_by_email = {p['email'].lower(): p for p in people}
    use_color       = st.session_state.use_color

    batch_tab1, batch_tab2 = st.tabs(["✏️ Paste Emails", "📁 Upload File"])
    batch_emails = []

    with batch_tab1:
        raw_input = st.text_area("Emails", height=160,
            placeholder="jane.doe@example.com\njohn.smith@example.com\n...",
            label_visibility="collapsed")
        if raw_input.strip():
            batch_emails = parse_email_list(raw_input)
            if batch_emails:
                st.caption(f"Parsed **{len(batch_emails)}** valid email(s).")

    with batch_tab2:
        email_file = st.file_uploader("Upload .txt or .csv", type=["txt","csv"], key="batch_email_file")
        if email_file:
            batch_emails = parse_email_list(email_file.read().decode("utf-8", errors="ignore"))
            st.caption(f"Parsed **{len(batch_emails)}** valid email(s).")

    if batch_emails:
        matched   = [people_by_email[e] for e in batch_emails if e in people_by_email]
        unmatched = [e for e in batch_emails if e not in people_by_email]

        chips = "".join(f'<span class="match-chip">✓ {p["email"]}</span>' for p in matched)
        chips += "".join(f'<span class="nomatch-chip">✗ {e}</span>' for e in unmatched)
        st.markdown(f"""
        <div style="margin:8px 0 14px;">
            <strong style="font-size:0.85rem;color:#1B3A6B;">{len(matched)} matched · {len(unmatched)} not found</strong>
            <br><br>{chips}
        </div>""", unsafe_allow_html=True)

        if unmatched:
            with st.expander(f"⚠️ {len(unmatched)} email(s) not found"):
                for e in unmatched: st.markdown(f"- `{e}`")

        if matched:
            st.markdown('<div class="section-label">Matched Workers</div>', unsafe_allow_html=True)
            for p in matched:
                is_pass   = any('pass' in c['status'].lower() for c in p['courses'])
                row_cls   = 'pass' if is_pass else 'prog'
                badge_cls = 'badge-pass' if is_pass else 'badge-prog'
                badge_txt = 'PASSED' if is_pass else 'IN PROGRESS'
                ssn_part  = f'<span class="worker-ssn">· ••••{p["ssn4"]}</span>' if p.get('ssn4') else ''

                col_card, col_btn = st.columns([7, 1])
                with col_card:
                    st.markdown(f"""
                    <div class="worker-row {row_cls}">
                        <span class="worker-name">{p['name']}</span>
                        <span class="worker-email">{p['email']}</span>
                        {ssn_part}
                        <span class="badge {badge_cls}">{badge_txt}</span>
                    </div>""", unsafe_allow_html=True)
                with col_btn:
                    if st.button("👁", key=f"prev_batch_{p['email']}", use_container_width=True, help=f"Preview {p['name']}"):
                        show_preview_modal(p, use_color)

            st.markdown('<div class="section-label">Download Batch Results</div>', unsafe_allow_html=True)
            bcol1, bcol2 = st.columns(2)
            with bcol1:
                if st.button(f"📄 Merged PDF ({len(matched)} workers)", use_container_width=True, type="primary"):
                    with st.spinner("Building transcripts..."):
                        batch_merged = merge_pdfs([build_person_pdf(p, use_color=use_color) for p in matched])
                    st.download_button("⬇️ Download Batch_Transcripts.pdf",
                        data=batch_merged, file_name="Batch_Transcripts.pdf",
                        mime="application/pdf", use_container_width=True)
            with bcol2:
                if st.button(f"🗂 Individual ZIP ({len(matched)} PDFs)", use_container_width=True):
                    with st.spinner("Packaging..."):
                        zip_buf = io.BytesIO()
                        with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                            for p in matched:
                                safe_name = re.sub(r'[^\w\-]', '_', p['name'])
                                zf.writestr(f"{safe_name}.pdf", build_person_pdf(p, use_color=use_color))
                        zip_buf.seek(0)
                    st.download_button("⬇️ Download Batch_Transcripts.zip",
                        data=zip_buf, file_name="Batch_Transcripts.zip",
                        mime="application/zip", use_container_width=True)
        else:
            st.warning("None of the entered emails matched any workers in the uploaded CSVs.")

# ══════════════════════════════════════════════════════════════════════════════
# ── Page: Export CSV ──────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Export CSV":
    st.markdown("""
    <div class="page-header">
        <h2>✏️ Export CSV</h2>
        <p>A clean, fully-structured export with all fields — preview below before downloading</p>
    </div>""", unsafe_allow_html=True)

    if not require_data(): st.stop()

    people = st.session_state.people

    st.markdown("""<div class="info-card"><h4>Exported Fields</h4>
    <p><b>Name</b> · <b>Email</b> · <b>SSN Last 4</b> · <b>Course</b> · <b>Status</b> ·
    <b>Started Date</b> · <b>Completion Date</b> · <b>Passed</b> (Yes / No)</p>
    </div>""", unsafe_allow_html=True)

    preview_rows = []
    for p in people:
        for c in p['courses']:
            preview_rows.append({
                'Name':            p['name'],
                'Email':           p['email'],
                'SSN Last 4':      p.get('ssn4') or '',
                'Course':          c['course'],
                'Status':          c['status'],
                'Started Date':    c.get('started_date') or '',
                'Completion Date': c.get('completion_date') or '',
                'Passed':          'Yes' if 'pass' in c['status'].lower() else 'No',
            })

    preview_df = pd.DataFrame(preview_rows)
    st.markdown('<div class="section-label">Data Preview</div>', unsafe_allow_html=True)
    st.dataframe(preview_df, use_container_width=True, height=340)

    st.markdown(f'<div class="section-label">{len(preview_rows)} rows · {len(people)} workers · {len(st.session_state.courses)} courses</div>', unsafe_allow_html=True)

    st.download_button(
        "⬇️ Download combined.csv",
        data=build_clean_csv(people),
        file_name="combined.csv",
        mime="text/csv",
        use_container_width=True,
        type="primary",
    )

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
        value=st.session_state.use_color
    )
    st.session_state.use_color = use_color

    st.markdown('<div class="section-label">Course Keyword Detection</div>', unsafe_allow_html=True)
    st.markdown("""<div class="info-card"><h4>How course names are auto-detected</h4>
    <p>Keywords are matched against the uploaded filename and column headers. If no keyword matches, the filename is used as the course name.</p>
    </div>""", unsafe_allow_html=True)

    kw_df = pd.DataFrame([
        {"Keyword (filename / columns)": k, "Detected Course Name": v}
        for k, v in COURSE_KEYWORDS.items()
    ])
    st.dataframe(kw_df, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-label">About</div>', unsafe_allow_html=True)
    st.markdown("""<div class="info-card"><h4>Training Transcript Generator</h4>
    <p>
        Built for Construction Workforce Safety Training.<br>
        Upload CSV exports → auto-detect courses → generate printable PDF transcripts.<br>
        Workers are matched across multiple course files by email address.<br><br>
        <b>Requires:</b> Streamlit 1.32+ · reportlab · pypdf · pandas
    </p></div>""", unsafe_allow_html=True)
