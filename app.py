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

.batch-box {
    background: #ffffff;
    border: 1.5px solid #1B3A6B22;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.batch-header {
    font-size: 1rem;
    font-weight: 600;
    color: #1B3A6B;
    margin-bottom: 4px;
}
.batch-sub {
    font-size: 0.8rem;
    color: #999;
    margin-bottom: 14px;
}
.match-chip {
    display: inline-block;
    background: #E8F5E9;
    color: #2E7D32;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 600;
    margin: 3px 4px 3px 0;
}
.nomatch-chip {
    display: inline-block;
    background: #FFF3E0;
    color: #E65100;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 600;
    margin: 3px 4px 3px 0;
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
    "asbestos": "Asbestos Awareness",
    "covid":    "COVID-19 for the Construction Workforce",
    "lead":     "Lead Awareness Worker",
    "hazard":   "Hazard Communication",
}

def detect_course(filename, df):
    fn = filename.lower()
    for kw, name in COURSE_KEYWORDS.items():
        if kw in fn:
            return name
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
                if i + 1 < len(cols):
                    ssn_col = cols[i + 1]
                break

        for _, row in df.iterrows():
            name  = str(row.get('Name',  '')).strip()
            email = str(row.get('Email', '')).strip()
            if not email or email == 'nan':
                continue
            key      = email.lower()
            result   = str(row.get('Course result', '')).strip()
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
        ORANGE_LT = colors.HexColor('#F5F5F5')

    GRAY_LT = colors.HexColor('#F5F5F5')
    GRAY_BD = colors.HexColor('#DDDDDD')
    WHITE   = colors.white
    TEXT    = colors.HexColor('#2C2C2C')

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
        leftMargin=0.65*inch, rightMargin=0.65*inch,
        topMargin=0.5*inch,   bottomMargin=0.65*inch)

    S = lambda n, **kw: ParagraphStyle(n, **kw)
    title_s       = S('t',  fontName='Helvetica-Bold',    fontSize=20, textColor=WHITE,    alignment=TA_CENTER)
    sub_s         = S('s',  fontName='Helvetica-Oblique', fontSize=10, textColor=GOLD,     alignment=TA_CENTER)
    label_s       = S('l',  fontName='Helvetica-Bold',    fontSize=9,  textColor=NAVY)
    value_s       = S('v',  fontName='Helvetica',         fontSize=10, textColor=TEXT)
    sec_s         = S('se', fontName='Helvetica-Bold',    fontSize=10, textColor=WHITE,    alignment=TA_LEFT)
    course_s      = S('c',  fontName='Helvetica-Bold',    fontSize=10, textColor=TEXT)
    status_pass_s = S('sp', fontName='Helvetica-Bold',    fontSize=9,  textColor=GREEN_DK)
    status_prog_s = S('so', fontName='Helvetica-Bold',    fontSize=9,  textColor=ORANGE_DK)
    date_s        = S('d',  fontName='Helvetica',         fontSize=9,  textColor=colors.HexColor('#666666'))

    story = []

    # Header banner
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

    # Worker info block
    name_display = person['name'] or person['email']
    ssn_display  = f"SSN (Last 4): ••••{person['ssn4']}" if person.get('ssn4') else "SSN (Last 4): —"
    info_data = [
        [Paragraph("EMPLOYEE", label_s), Paragraph("EMAIL", label_s), Paragraph("IDENTIFIER", label_s)],
        [Paragraph(name_display, value_s), Paragraph(person['email'], value_s), Paragraph(ssn_display, value_s)],
    ]
    info_table = Table(info_data, colWidths=[2.4*inch, 2.8*inch, 2.0*inch])
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
    story.append(Spacer(1, 6))

    # Course rows
    for i, c in enumerate(person['courses']):
        bg           = GRAY_LT if i % 2 == 0 else WHITE
        status_s     = status_pass_s if 'pass' in c['status'].lower() else status_prog_s
        status_label = c['status'] if c['status'] else '—'
        comp_date    = c['completion_date'] or '—'
        start_date   = c['started_date'] or '—'

        row_data = [[
            Paragraph(c['course'], course_s),
            Paragraph(status_label, status_s),
            Paragraph(f"Started: {start_date}", date_s),
            Paragraph(f"Completed: {comp_date}", date_s),
        ]]
        row_table = Table(row_data, colWidths=[2.9*inch, 1.1*inch, 1.5*inch, 1.7*inch])
        row_table.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), bg),
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
        "Generated by Training Transcript Generator · Construction Workforce Safety Training",
        footer_s
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()

# ── PDF merger ────────────────────────────────────────────────────────────────
def merge_pdfs(pdf_bytes_list: list) -> bytes:
    writer = PdfWriter()
    for pdf_bytes in pdf_bytes_list:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.read()

# ── Parse batch emails helper ─────────────────────────────────────────────────
def parse_email_list(raw_text: str) -> list:
    """Extract and normalize a list of emails from raw text (newline or comma separated)."""
    raw    = raw_text.replace(',', '\n')
    emails = [e.strip().lower() for e in raw.splitlines() if e.strip()]
    valid  = [e for e in emails if re.match(r'^[\w\.\+\-]+@[\w\-]+\.[a-z]{2,}$', e)]
    return list(dict.fromkeys(valid))  # deduplicate, preserve order

# ══════════════════════════════════════════════════════════════════════════════
# ── Main UI ───────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="section-label">Upload Training Data</div>', unsafe_allow_html=True)
st.markdown('<div class="upload-hint">Drop one or more CSV exports below — each file is treated as a separate course</div>', unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Upload CSV files",
    type=["csv"],
    accept_multiple_files=True,
    label_visibility="collapsed"
)

if uploaded_files:
    people, courses    = process_files(uploaded_files)
    people_by_email    = {p['email'].lower(): p for p in people}
    total  = len(people)
    passed = sum(1 for p in people if any('pass' in c['status'].lower() for c in p['courses']))

    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-box"><div class="stat-num">{total}</div><div class="stat-label">Workers</div></div>
        <div class="stat-box"><div class="stat-num">{len(courses)}</div><div class="stat-label">Courses</div></div>
        <div class="stat-box"><div class="stat-num">{passed}</div><div class="stat-label">Passed</div></div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("👥 Preview all workers"):
        for p in people:
            statuses  = [c['status'] for c in p['courses']]
            badge_cls = 'badge-pass' if any('pass' in s.lower() for s in statuses) else 'badge-prog'
            badge_txt = 'PASS' if any('pass' in s.lower() for s in statuses) else 'IN PROGRESS'
            st.markdown(f"""
            <div class="worker-card">
                <span>{p['name']} <span style="color:#999;font-size:0.8em">· {p['email']}</span></span>
                <span class="{badge_cls}">{badge_txt}</span>
            </div>
            """, unsafe_allow_html=True)

    # ── PDF Options ───────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">PDF Options</div>', unsafe_allow_html=True)
    color_choice = st.checkbox("🖨️ Color PDFs (leave unchecked for grayscale)", value=True)

    # ── Generate All ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Generate Transcripts / Export Data</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("📄 Generate All Transcripts PDF", use_container_width=True, type="primary"):
            with st.spinner(f"Building {total} transcripts..."):
                all_pdfs = [build_person_pdf(p, use_color=color_choice) for p in people]
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
                        pdf_bytes = build_person_pdf(p, use_color=color_choice)
                        safe_name = re.sub(r'[^\w\-]', '_', p['name'])
                        zf.writestr(f"{safe_name}.pdf", pdf_bytes)
                zip_buf.seek(0)
            st.download_button(
                label="⬇️ Download Transcripts.zip",
                data=zip_buf,
                file_name="Transcripts.zip",
                mime="application/zip",
                use_container_width=True
            )

    with col3:
        if st.button("✏️ Export Combined CSV", use_container_width=True):
            csv_buf = io.StringIO()
            csv_buf.write('Name,Email,SSN4,Course,Status,CompletionDate,StartedDate\n')
            for p in people:
                for c in p['courses']:
                    csv_buf.write(
                        f"{p['name']},{p['email']},{p.get('ssn4','')},{c['course']},"
                        f"{c['status']},{c.get('completion_date','')},{c.get('started_date','')}\n"
                    )
            st.download_button(
                label="⬇️ Download combined.csv",
                data=csv_buf.getvalue(),
                file_name="combined.csv",
                mime="text/csv",
                use_container_width=True
            )

    # ══════════════════════════════════════════════════════════════════════════
    # ── Batch Email Lookup ────────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown('<div class="section-label">Batch Email Lookup</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="batch-box">
        <div class="batch-header">🔍 Generate Transcripts for Specific Emails</div>
        <div class="batch-sub">Enter emails manually or upload a .txt / .csv file — only matched workers will get transcripts.</div>
    </div>
    """, unsafe_allow_html=True)

    batch_tab1, batch_tab2 = st.tabs(["✏️ Paste Emails", "📁 Upload File"])

    batch_emails = []

    with batch_tab1:
        raw_input = st.text_area(
            "Enter emails (one per line, or comma-separated):",
            height=160,
            placeholder="jane.doe@example.com\njohn.smith@example.com\n...",
            label_visibility="collapsed"
        )
        if raw_input.strip():
            batch_emails = parse_email_list(raw_input)
            if batch_emails:
                st.caption(f"Parsed **{len(batch_emails)}** valid email(s).")

    with batch_tab2:
        email_file = st.file_uploader(
            "Upload a .txt or .csv file containing emails",
            type=["txt", "csv"],
            key="batch_email_file"
        )
        if email_file:
            raw_file_text = email_file.read().decode("utf-8", errors="ignore")
            batch_emails  = parse_email_list(raw_file_text)
            st.caption(f"Parsed **{len(batch_emails)}** valid email(s) from uploaded file.")

    if batch_emails:
        matched   = [people_by_email[e] for e in batch_emails if e in people_by_email]
        unmatched = [e for e in batch_emails if e not in people_by_email]

        # Results summary chips
        chips_html = ""
        for p in matched:
            chips_html += f'<span class="match-chip">✓ {p["email"]}</span>'
        for e in unmatched:
            chips_html += f'<span class="nomatch-chip">✗ {e}</span>'

        st.markdown(f"""
        <div style="margin: 8px 0 14px;">
            <strong style="font-size:0.85rem; color:#1B3A6B;">
                {len(matched)} matched &nbsp;·&nbsp; {len(unmatched)} not found
            </strong><br/><br/>
            {chips_html}
        </div>
        """, unsafe_allow_html=True)

        if unmatched:
            with st.expander(f"⚠️ {len(unmatched)} email(s) not found in uploaded CSVs"):
                for e in unmatched:
                    st.markdown(f"- `{e}`")

        if matched:
            st.markdown('<div class="section-label">Download Batch Results</div>', unsafe_allow_html=True)
            bcol1, bcol2 = st.columns(2)

            with bcol1:
                if st.button(
                    f"📄 Generate PDF for {len(matched)} matched worker(s)",
                    use_container_width=True,
                    type="primary"
                ):
                    with st.spinner(f"Building {len(matched)} transcript(s)..."):
                        batch_pdfs   = [build_person_pdf(p, use_color=color_choice) for p in matched]
                        batch_merged = merge_pdfs(batch_pdfs)
                    st.download_button(
                        label="⬇️ Download Batch_Transcripts.pdf",
                        data=batch_merged,
                        file_name="Batch_Transcripts.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

            with bcol2:
                if st.button(
                    f"🗂 Download ZIP ({len(matched)} individual PDFs)",
                    use_container_width=True
                ):
                    with st.spinner("Packaging individual PDFs..."):
                        zip_buf = io.BytesIO()
                        with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                            for p in matched:
                                pdf_bytes = build_person_pdf(p, use_color=color_choice)
                                safe_name = re.sub(r'[^\w\-]', '_', p['name'])
                                zf.writestr(f"{safe_name}.pdf", pdf_bytes)
                        zip_buf.seek(0)
                    st.download_button(
                        label="⬇️ Download Batch_Transcripts.zip",
                        data=zip_buf,
                        file_name="Batch_Transcripts.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
        else:
            st.warning("None of the entered emails matched any workers in the uploaded CSVs.")

else:
    st.markdown("""
    <div class="upload-hint" style="margin-top: 32px;">
        ⬆️ Upload at least one CSV file above to get started
    </div>
    """, unsafe_allow_html=True)
