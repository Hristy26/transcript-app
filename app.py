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
    layout="centered"
)

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    background: #F7F6F2;
}

.main-header {
    background: #1B3A6B;
    border-radius: 16px;
    padding: 36px 40px 28px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
}
.main-header::before {
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 180px; height: 180px;
    background: rgba(201,168,76,0.15);
    border-radius: 50%;
}
.main-header h1 {
    color: #ffffff;
    font-size: 1.75rem;
    font-weight: 600;
    margin: 0 0 4px;
    letter-spacing: -0.5px;
}
.main-header p {
    color: #C9A84C;
    font-size: 0.9rem;
    margin: 0;
    font-weight: 400;
}

.upload-hint {
    background: #ffffff;
    border: 2px dashed #C9A84C;
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
    color: #666;
    font-size: 0.85rem;
    margin-bottom: 8px;
}

.stat-row {
    display: flex;
    gap: 12px;
    margin: 16px 0;
}
.stat-box {
    flex: 1;
    background: #ffffff;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
    border: 1px solid #E8E4DB;
}
.stat-num {
    font-size: 2rem;
    font-weight: 600;
    color: #1B3A6B;
    font-family: 'DM Mono', monospace;
    line-height: 1;
}
.stat-label {
    font-size: 0.75rem;
    color: #999;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.worker-card {
    background: #ffffff;
    border-radius: 8px;
    padding: 10px 16px;
    margin: 4px 0;
    border-left: 3px solid #1B3A6B;
    font-size: 0.88rem;
    color: #333;
    display: flex;
    justify-content: space-between;
}
.badge-pass  { color: #2E7D32; font-weight: 600; }
.badge-prog  { color: #E65100; font-weight: 600; }

.section-label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #999;
    margin: 20px 0 8px;
}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>📋 Training Transcript Generator</h1>
    <p>Construction Workforce Safety Training · Drop CSVs to generate printable transcripts</p>
</div>
""", unsafe_allow_html=True)

# ── Course name detection ─────────────────────────────────────────────────────
COURSE_KEYWORDS = {
    "asbestos":      "Asbestos Awareness",
    "covid":         "COVID-19 for the Construction Workforce",
    "lead":          "Lead Awareness Worker",
    "hazard":        "Hazard Communication",
}

def detect_course(filename, df):
    fn = filename.lower()
    for kw, name in COURSE_KEYWORDS.items():
        if kw in fn:
            return name
    # fallback: check column headers
    cols = " ".join(df.columns).lower()
    for kw, name in COURSE_KEYWORDS.items():
        if kw in cols:
            return name
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

        cols = list(df.columns)
        ssn_col = None
        for i, c in enumerate(cols):
            if 'last 4 digits' in c.lower() and 'social' in c.lower():
                if i+1 < len(cols):
                    ssn_col = cols[i+1]
                break

        for _, row in df.iterrows():
            name  = str(row.get('Name',  '')).strip()
            email = str(row.get('Email', '')).strip()
            if not email or email == 'nan':
                continue
            key    = email.lower()
            result = str(row.get('Course result', '')).strip()
            finished = str(row.get('Finished', '')).strip()
            started  = str(row.get('Started',  '')).strip()

            def clean_date(d):
                if d in ('', '-', 'nan', 'Not finished yet'):
                    return None
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
                'course':           course_name,
                'status':           result,
                'completion_date':  clean_date(finished),
                'started_date':     clean_date(started),
            })

    return sorted(people.values(), key=lambda x: x['name'].lower()), course_names_seen

# ── PDF builder ───────────────────────────────────────────────────────────────
NAVY      = colors.HexColor('#1B3A6B')
GOLD      = colors.HexColor('#C9A84C')
GREEN_DK  = colors.HexColor('#2E7D32')
GREEN_LT  = colors.HexColor('#E8F5E9')
ORANGE_DK = colors.HexColor('#E65100')
ORANGE_LT = colors.HexColor('#FFF3E0')
GRAY_LT   = colors.HexColor('#F5F5F5')
GRAY_BD   = colors.HexColor('#DDDDDD')
WHITE     = colors.white
TEXT      = colors.HexColor('#2C2C2C')

def build_person_pdf(person) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
        leftMargin=0.65*inch, rightMargin=0.65*inch,
        topMargin=0.5*inch, bottomMargin=0.6*inch)

    S = lambda n, **kw: ParagraphStyle(n, **kw)
    title_s  = S('t',  fontName='Helvetica-Bold',    fontSize=20, textColor=WHITE,     alignment=TA_CENTER)
    sub_s    = S('s',  fontName='Helvetica-Oblique', fontSize=10, textColor=GOLD,      alignment=TA_CENTER)
    label_s  = S('l',  fontName='Helvetica-Bold',    fontSize=9,  textColor=NAVY)
    value_s  = S('v',  fontName='Helvetica',         fontSize=10, textColor=TEXT)
    sec_s    = S('se', fontName='Helvetica-Bold',    fontSize=10, textColor=WHITE,     alignment=TA_LEFT)
    col_s    = S('c',  fontName='Helvetica-Bold',    fontSize=8.5,textColor=WHITE,     alignment=TA_CENTER)
    cell_s   = S('ce', fontName='Helvetica',         fontSize=9.5,textColor=TEXT)
    cell_c_s = S('cc', fontName='Helvetica',         fontSize=9.5,textColor=TEXT,      alignment=TA_CENTER)
    green_s  = S('g',  fontName='Helvetica-Bold',    fontSize=9.5,textColor=GREEN_DK,  alignment=TA_CENTER)
    orange_s = S('o',  fontName='Helvetica-Bold',    fontSize=9.5,textColor=ORANGE_DK, alignment=TA_CENTER)
    footer_s = S('f',  fontName='Helvetica-Oblique', fontSize=7.5,
                       textColor=colors.HexColor('#888888'), alignment=TA_CENTER)

    story = []

    # Banner
    ht = Table([[Paragraph("TRAINING TRANSCRIPT", title_s)],
                [Paragraph("Construction Workforce Safety Training", sub_s)]],
               colWidths=[7.2*inch])
    ht.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), NAVY),
        ('TOPPADDING',    (0,0),(0,0), 14), ('BOTTOMPADDING',(0,0),(0,0), 2),
        ('TOPPADDING',    (0,1),(0,1), 2),  ('BOTTOMPADDING',(0,1),(0,1), 12),
    ]))
    story.append(ht)
    story.append(Spacer(1, 10))

    # Info box
    info = Table([
        [Paragraph("NAME",       label_s), Paragraph(person['name'],               value_s)],
        [Paragraph("EMAIL",      label_s), Paragraph(person['email'],              value_s)],
        [Paragraph("LAST 4 SS#", label_s), Paragraph(person['ssn4'] or '—',       value_s)],
    ], colWidths=[1.0*inch, 6.2*inch])
    info.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), GRAY_LT),
        ('BOX',           (0,0),(-1,-1), 1, GRAY_BD),
        ('INNERGRID',     (0,0),(-1,-1), 0.5, GRAY_BD),
        ('TOPPADDING',    (0,0),(-1,-1), 7), ('BOTTOMPADDING',(0,0),(-1,-1), 7),
        ('LEFTPADDING',   (0,0),(-1,-1), 10), ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
    ]))
    story.append(info)
    story.append(Spacer(1, 14))

    passed = [c for c in person['courses'] if c['status'].lower() == 'passed']
    inprog = [c for c in person['courses'] if c['status'].lower() == 'in progress']

    def course_table(rows_data, hdr_color, row_bg):
        rows = [[Paragraph("Course Name", col_s),
                 Paragraph("Status", col_s),
                 Paragraph("Date", col_s)]] + rows_data
        t = Table(rows, colWidths=[4.0*inch, 1.4*inch, 1.8*inch])
        style = [
            ('BACKGROUND',    (0,0),(-1,0), hdr_color),
            ('TOPPADDING',    (0,0),(-1,-1), 7), ('BOTTOMPADDING',(0,0),(-1,-1), 7),
            ('LEFTPADDING',   (0,0),(-1,-1), 8), ('RIGHTPADDING', (0,0),(-1,-1), 8),
            ('GRID',          (0,0),(-1,-1), 0.5, GRAY_BD),
            ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
        ]
        for i in range(1, len(rows)):
            style.append(('BACKGROUND',(0,i),(-1,i), row_bg if (i-1)%2==0 else WHITE))
        t.setStyle(TableStyle(style))
        return t

    if passed:
        h = Table([[Paragraph("  COMPLETED COURSES", sec_s)]], colWidths=[7.2*inch])
        h.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),GREEN_DK),
                                ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        story.append(h)
        rows = [[Paragraph(c['course'], cell_s),
                 Paragraph("Passed", green_s),
                 Paragraph(c['completion_date'] or '—', cell_c_s)] for c in passed]
        story.append(course_table(rows, colors.HexColor('#4CAF50'), GREEN_LT))
        story.append(Spacer(1, 14))

    if inprog:
        h = Table([[Paragraph("  COURSES IN PROGRESS", sec_s)]], colWidths=[7.2*inch])
        h.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),ORANGE_DK),
                                ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        story.append(h)
        rows = [[Paragraph(c['course'], cell_s),
                 Paragraph("In Progress", orange_s),
                 Paragraph(c['started_date'] or '—', cell_c_s)] for c in inprog]
        story.append(course_table(rows, colors.HexColor('#FF7043'), ORANGE_LT))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width='100%', thickness=0.5, color=GRAY_BD))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Construction Workforce Safety Training  |  Confidential Training Record", footer_s))

    doc.build(story)
    return buf.getvalue()

def merge_pdfs(pdf_bytes_list) -> bytes:
    writer = PdfWriter()
    for pdf_bytes in pdf_bytes_list:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()

# ── Upload section ────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Upload CSV Files</div>', unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Drop your CSV exports here",
    type=["csv"],
    accept_multiple_files=True,
    label_visibility="collapsed"
)

if not uploaded_files:
    st.markdown("""
    <div class="upload-hint">
        ⬆️ Drag and drop one or more training CSV files above<br>
        <small>Supports: Asbestos, COVID-19, Lead Awareness, Hazard Communication — or any new course CSV</small>
    </div>
    """, unsafe_allow_html=True)

# ── Process ───────────────────────────────────────────────────────────────────
if uploaded_files:
    with st.spinner("Reading files..."):
        people, courses_found = process_files(uploaded_files)

    total     = len(people)
    passed_ct = sum(1 for p in people if any(c['status'].lower()=='passed'    for c in p['courses']))
    inprog_ct = sum(1 for p in people if any(c['status'].lower()=='in progress' for c in p['courses']))

    # Stats
    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-box"><div class="stat-num">{total}</div><div class="stat-label">Workers Found</div></div>
        <div class="stat-box"><div class="stat-num">{len(courses_found)}</div><div class="stat-label">Courses</div></div>
        <div class="stat-box"><div class="stat-num">{passed_ct}</div><div class="stat-label">Have Completions</div></div>
        <div class="stat-box"><div class="stat-num">{inprog_ct}</div><div class="stat-label">In Progress</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Courses detected
    st.markdown('<div class="section-label">Courses Detected</div>', unsafe_allow_html=True)
    for c in courses_found:
        st.markdown(f"<div style='font-size:0.85rem;color:#555;padding:2px 0'>✅ {c}</div>", unsafe_allow_html=True)

    # Worker preview
    st.markdown('<div class="section-label">Workers Preview</div>', unsafe_allow_html=True)
    with st.expander(f"View all {total} workers", expanded=False):
        for p in people:
            passed_n = sum(1 for c in p['courses'] if c['status'].lower()=='passed')
            inprog_n = sum(1 for c in p['courses'] if c['status'].lower()=='in progress')
            st.markdown(f"""
            <div class="worker-card">
                <span><b>{p['name']}</b> &nbsp;·&nbsp; <span style="color:#999;font-size:0.82rem">{p['email']}</span></span>
                <span>
                    <span class="badge-pass">{passed_n} passed</span>
                    {'&nbsp;·&nbsp;<span class="badge-prog">' + str(inprog_n) + ' in progress</span>' if inprog_n else ''}
                </span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="section-label">Generate Transcripts</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📄 Generate All Transcripts PDF", use_container_width=True, type="primary"):
            with st.spinner(f"Building {total} transcripts..."):
                all_pdfs = [build_person_pdf(p) for p in people]
                merged   = merge_pdfs(all_pdfs)
            st.download_button(
                label="⬇️ Download All_Transcripts.pdf",
                data=merged,
                file_name="All_Transcripts.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    with col2:
        if st.button("🗂 Download Individual PDFs (ZIP)", use_container_width=True):
            with st.spinner("Packaging individual PDFs..."):
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for p in people:
                        pdf_bytes = build_person_pdf(p)
                        safe_name = re.sub(r'[^\w\-]', '_', p['name'])
                        zf.writestr(f"{safe_name}.pdf", pdf_bytes)
                zip_buf.seek(0)
            st.download_button(
                label="⬇️ Download Individual_PDFs.zip",
                data=zip_buf.getvalue(),
                file_name="Individual_Transcripts.zip",
                mime="application/zip",
                use_container_width=True
            )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;margin-top:48px;font-size:0.75rem;color:#bbb;">
    Construction Workforce Safety Training · Private Use Only
</div>
""", unsafe_allow_html=True)
