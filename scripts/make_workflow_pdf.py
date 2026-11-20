from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parents[1] / "Job_Digest_Workflow_Guide.pdf"
ASSETS = Path(r"C:\Users\manikandan.m\.cursor\projects\d-backup-CRM-Source\assets")
IMG1 = ASSETS / "job-digest-overview.jpg"
IMG2 = ASSETS / "job-digest-daily-flow.jpg"
IMG3 = ASSETS / "job-digest-setup-checklist.jpg"

BLUE = HexColor("#0F4C81")
TEAL = HexColor("#0D7377")
LIGHT = HexColor("#F4F7FB")
DARK = HexColor("#1F2937")
MUTED = HexColor("#4B5563")
GREEN = HexColor("#047857")
ORANGE = HexColor("#B45309")
GRID = HexColor("#D1D5DB")


def build() -> Path:
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=BLUE,
            alignment=TA_CENTER,
            spaceAfter=8,
            leading=26,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverSub",
            fontName="Helvetica",
            fontSize=11,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=6,
            leading=15,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1",
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=BLUE,
            spaceBefore=8,
            spaceAfter=6,
            leading=18,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Body",
            fontName="Helvetica",
            fontSize=9.5,
            textColor=DARK,
            spaceAfter=4,
            leading=13,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Small",
            fontName="Helvetica",
            fontSize=8.5,
            textColor=MUTED,
            spaceAfter=3,
            leading=11,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Caption",
            fontName="Helvetica-Oblique",
            fontSize=8,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceBefore=2,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Cell",
            fontName="Helvetica",
            fontSize=8.5,
            textColor=DARK,
            leading=11,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CellBold",
            fontName="Helvetica-Bold",
            fontSize=8.5,
            textColor=DARK,
            leading=11,
        )
    )

    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="Job Digest Agent - Workflow Guide",
        author="Manikandan Madasamy",
    )
    story = []

    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Job Digest Agent", styles["CoverTitle"]))
    story.append(Paragraph("Simple Workflow Guide (Beginner)", styles["CoverSub"]))
    story.append(
        Paragraph(
            "For: <b>Manikandan Madasamy</b> &nbsp;|&nbsp; "
            "Email: <b>manimadasamy.dev@gmail.com</b><br/>"
            "Target: <b>Java Developer / Backend / Full Stack</b> in "
            "<b>Chennai &amp; Bengaluru</b>",
            styles["CoverSub"],
        )
    )
    story.append(Spacer(1, 3 * mm))
    story.append(HRFlowable(width="100%", thickness=1.2, color=BLUE, spaceAfter=6))
    story.append(
        Paragraph(
            "This short PDF explains <b>what the app does</b>, "
            "<b>how the daily flow works</b>, and <b>how to set it up</b> "
            "so anyone can understand quickly.",
            styles["Body"],
        )
    )

    story.append(Paragraph("1. What is this application?", styles["H1"]))
    story.append(
        Paragraph(
            "It is a free automatic job helper. Twice every day it searches for Java jobs "
            "in Chennai and Bengaluru, saves new jobs in Supabase, and emails only new "
            "matching jobs to you.",
            styles["Body"],
        )
    )

    box_data = [
        [
            Paragraph("<b>Searches</b><br/>Job boards + career pages", styles["Cell"]),
            Paragraph("<b>Filters</b><br/>Java / Spring / Full Stack", styles["Cell"]),
            Paragraph("<b>Stores</b><br/>Supabase (no duplicates)", styles["Cell"]),
            Paragraph("<b>Emails</b><br/>Only new jobs", styles["Cell"]),
        ]
    ]
    t = Table(box_data, colWidths=[42 * mm, 42 * mm, 42 * mm, 42 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.6, BLUE),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, GRID),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 4 * mm))

    if IMG1.exists():
        story.append(Image(str(IMG1), width=180 * mm, height=101 * mm))
        story.append(Paragraph("Figure A — End-to-end pieces of the system", styles["Caption"]))

    story.append(PageBreak())
    story.append(Paragraph("2. Daily automatic workflow", styles["H1"]))
    story.append(
        Paragraph(
            "After setup, you do not need to run anything manually every day. "
            "GitHub Actions starts the job automatically.",
            styles["Body"],
        )
    )

    steps = [
        ("A", "Schedule", "Runs at 8:00 AM and 6:00 PM IST"),
        ("B", "Collect jobs", "Reads job boards + company career pages"),
        ("C", "Match profile", "Keeps Java / Backend / Full Stack roles"),
        ("D", "Save in Supabase", "Stores listings; skips already-seen URLs"),
        ("E", "Send email", "Emails only NEW jobs to your Gmail"),
    ]
    rows = [
        [
            Paragraph(f"<b>{a}</b>", styles["CellBold"]),
            Paragraph(f"<b>{b}</b>", styles["CellBold"]),
            Paragraph(c, styles["Cell"]),
        ]
        for a, b, c in steps
    ]
    tbl = Table(
        [
            [
                Paragraph("<b>#</b>", styles["CellBold"]),
                Paragraph("<b>Step</b>", styles["CellBold"]),
                Paragraph("<b>What happens</b>", styles["CellBold"]),
            ]
        ]
        + rows,
        colWidths=[12 * mm, 35 * mm, 133 * mm],
    )
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("BACKGROUND", (0, 1), (-1, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, BLUE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, GRID),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(tbl)
    story.append(Spacer(1, 3 * mm))

    if IMG2.exists():
        story.append(Image(str(IMG2), width=180 * mm, height=101 * mm))
        story.append(Paragraph("Figure B — Daily automatic flow", styles["Caption"]))

    story.append(PageBreak())
    story.append(Paragraph("3. Setup workflow (one-time)", styles["H1"]))
    story.append(
        Paragraph(
            "Complete these steps once. Free tools: Supabase + Gmail + GitHub Actions.",
            styles["Body"],
        )
    )

    setup = [
        ("Step 1", "Source code", "Java job-digest project ready on your PC / GitHub"),
        (
            "Step 2",
            "Supabase",
            "Create project → run table SQL → run function SQL → copy URL + service_role key",
        ),
        ("Step 3", "Gmail", "Enable 2-Step Verification → create App Password"),
        (
            "Step 4",
            "GitHub",
            "Push code so repo ROOT has .github, job_agent, requirements.txt",
        ),
        ("Step 5", "Secrets", "Add 6 Actions secrets (names exact, no spaces)"),
        ("Step 6", "First run", "Actions → job-digest → Run workflow → check email"),
    ]
    srows = [
        [
            Paragraph(f"<b>{a}</b>", styles["CellBold"]),
            Paragraph(f"<b>{b}</b>", styles["CellBold"]),
            Paragraph(c, styles["Cell"]),
        ]
        for a, b, c in setup
    ]
    st = Table(
        [
            [
                Paragraph("<b>Step</b>", styles["CellBold"]),
                Paragraph("<b>Area</b>", styles["CellBold"]),
                Paragraph("<b>What you do</b>", styles["CellBold"]),
            ]
        ]
        + srows,
        colWidths=[20 * mm, 28 * mm, 132 * mm],
    )
    st.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), TEAL),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("BACKGROUND", (0, 1), (-1, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, TEAL),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, GRID),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(st)
    story.append(Spacer(1, 3 * mm))

    if IMG3.exists():
        story.append(Image(str(IMG3), width=155 * mm, height=116 * mm))
        story.append(Paragraph("Figure C — Setup checklist", styles["Caption"]))

    story.append(Paragraph("4. GitHub Secrets (copy names exactly)", styles["H1"]))
    secrets = [
        ("SUPABASE_URL", "Project URL from Supabase"),
        ("SUPABASE_SERVICE_ROLE_KEY", "service_role key (secret)"),
        ("GMAIL_USER", "manimadasamy.dev@gmail.com"),
        ("GMAIL_APP_PASSWORD", "16-character Gmail app password"),
        ("MAIL_TO", "manimadasamy.dev@gmail.com"),
        (
            "JOB_AGENT_TOKEN",
            "Same token used in Supabase SQL (example: mani-job-2026)",
        ),
    ]
    sec_rows = [
        [Paragraph(f"<b>{n}</b>", styles["CellBold"]), Paragraph(v, styles["Cell"])]
        for n, v in secrets
    ]
    sec_t = Table(
        [
            [
                Paragraph("<b>Secret Name</b>", styles["CellBold"]),
                Paragraph("<b>Value meaning</b>", styles["CellBold"]),
            ]
        ]
        + sec_rows,
        colWidths=[70 * mm, 110 * mm],
    )
    sec_t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ORANGE),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("BACKGROUND", (0, 1), (-1, -1), HexColor("#FFF7ED")),
                ("BOX", (0, 0), (-1, -1), 0.5, ORANGE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, HexColor("#FED7AA")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(sec_t)

    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("5. Common errors (quick fix)", styles["H1"]))
    story.append(
        Paragraph(
            "• <b>Actions shows Get started</b> → workflow must be at repo root "
            "<font face='Courier'>.github/workflows/</font> (not inside another folder).<br/>"
            "• <b>ja_start_run missing</b> → run function SQL in Supabase "
            "(tables alone are not enough).<br/>"
            "• <b>Secret name invalid</b> → underscores only, no spaces; "
            "use Secrets tab (not Variables).<br/>"
            "• <b>No email</b> → check App Password, spam folder, and Actions log.",
            styles["Body"],
        )
    )

    story.append(Spacer(1, 3 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=GREEN, spaceAfter=4))
    story.append(
        Paragraph(
            "<b>Success looks like:</b> Actions run is green, and/or you receive a digest "
            "email (or log shows 0 new jobs — that still means the system works).",
            styles["Body"],
        )
    )
    story.append(
        Paragraph(
            "Repo: github.com/manimadasamydev/job-digest-agent &nbsp;|&nbsp; "
            "Supabase project: job-digest &nbsp;|&nbsp; Schedule: 8 AM &amp; 6 PM IST",
            styles["Small"],
        )
    )

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(14 * mm, 8 * mm, "Job Digest Agent — Workflow Guide")
        canvas.drawRightString(A4[0] - 14 * mm, 8 * mm, f"Page {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return OUT


if __name__ == "__main__":
    path = build()
    print(path)
    print("size_bytes", path.stat().st_size)
