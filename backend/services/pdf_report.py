import io
import json
from datetime import datetime
from typing import List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
)

from backend.schemas import SprintReport


# ── Colour palette ────────────────────────────────────────────────────────────
C_PRIMARY   = colors.HexColor("#1E3A5F")   # dark navy
C_SECONDARY = colors.HexColor("#2E86AB")   # steel blue
C_PASS      = colors.HexColor("#27AE60")
C_FAIL      = colors.HexColor("#E74C3C")
C_BLOCKED   = colors.HexColor("#F39C12")
C_LIGHT     = colors.HexColor("#F4F6F9")
C_WHITE     = colors.white
C_BLACK     = colors.HexColor("#2C3E50")


def _status_color(status: str) -> colors.Color:
    mapping = {"Pass": C_PASS, "Fail": C_FAIL, "Blocked": C_BLOCKED}
    return mapping.get(status, C_LIGHT)


def generate_sprint_pdf(report: SprintReport) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "Title", parent=styles["Title"],
        fontSize=22, textColor=C_PRIMARY, spaceAfter=4, alignment=TA_CENTER
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontSize=10, textColor=C_SECONDARY, spaceAfter=14, alignment=TA_CENTER
    )
    h1_style = ParagraphStyle(
        "H1", parent=styles["Heading1"],
        fontSize=14, textColor=C_PRIMARY, spaceBefore=16, spaceAfter=6
    )
    h2_style = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontSize=11, textColor=C_SECONDARY, spaceBefore=10, spaceAfter=4
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=9, textColor=C_BLACK, spaceAfter=4
    )
    bold_style = ParagraphStyle(
        "Bold", parent=body_style, fontName="Helvetica-Bold"
    )

    story = []

    # ── Cover ──────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.5 * cm))
    story.append(Paragraph("QA Sprint Tracker", title_style))
    story.append(Paragraph(f"Sprint Report — {report.sprint_name}", subtitle_style))
    story.append(Paragraph(
        f"Generated: {datetime.utcnow().strftime('%d %b %Y  %H:%M UTC')}",
        ParagraphStyle("small", parent=styles["Normal"], fontSize=8,
                       textColor=colors.grey, alignment=TA_CENTER)
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SECONDARY, spaceAfter=20))

    # ── Summary stats ──────────────────────────────────────────────────────────
    story.append(Paragraph("Sprint Summary", h1_style))

    summary_data = [
        ["Metric", "Value"],
        ["Tickets Tested", str(report.total_tickets)],
        ["Test Cases Written", str(report.total_test_cases)],
        ["Total Executions", str(report.total_executions)],
        ["✅  Passed", str(report.passed)],
        ["❌  Failed", str(report.failed)],
        ["🚫  Blocked", str(report.blocked)],
        ["Pass Rate", f"{report.pass_rate:.1f}%"],
        ["Bugs Logged", str(report.bug_count)],
    ]

    tbl = Table(summary_data, colWidths=[9 * cm, 7 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), C_PRIMARY),
        ("TEXTCOLOR",   (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT]),
        ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#BDC3C7")),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.5 * cm))

    # ── Per-Ticket breakdown ───────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Per-Ticket Breakdown", h1_style))

    for tr in report.ticket_reports:
        ref = f"[{tr.external_id}]  " if tr.external_id else ""
        story.append(Paragraph(f"{ref}{tr.title}", h2_style))

        ticket_data = [
            ["Test Cases", "Executions", "Passed", "Failed", "Blocked", "Coverage"],
            [
                str(tr.total_cases),
                str(tr.total_executions),
                str(tr.passed),
                str(tr.failed),
                str(tr.blocked),
                f"{tr.coverage_pct:.0f}%",
            ]
        ]
        t = Table(ticket_data, colWidths=[2.7 * cm] * 6)
        t.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0), C_SECONDARY),
            ("TEXTCOLOR",    (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, -1), 8),
            ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_LIGHT]),
            ("GRID",         (0, 0), (-1, -1), 0.4, colors.HexColor("#BDC3C7")),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ]))
        story.append(t)

        platforms_str = ", ".join(tr.platforms_tested) if tr.platforms_tested else "—"
        envs_str      = ", ".join(tr.environments_tested) if tr.environments_tested else "—"
        story.append(Paragraph(
            f"<b>Platforms:</b> {platforms_str} &nbsp;&nbsp; <b>Environments:</b> {envs_str}",
            body_style
        ))
        story.append(Spacer(1, 0.3 * cm))

    # ── Footer note ───────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_SECONDARY, spaceBefore=20))
    story.append(Paragraph(
        "Generated by <b>QA Sprint Tracker</b> — Empowering QA visibility in every sprint.",
        ParagraphStyle("footer", parent=styles["Normal"], fontSize=7,
                       textColor=colors.grey, alignment=TA_CENTER)
    ))

    doc.build(story)
    return buffer.getvalue()
