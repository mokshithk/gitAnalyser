import io
from datetime import datetime, timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch

from backend.flags.engine import MANDATORY_DISCLAIMER, SYSTEM_LIMITATIONS

def generate_pdf_report(analysis, flags, matches, commit_metrics) -> bytes:
    """
    Generates a professional, pure-Python PDF triage report for an analysis using ReportLab.
    Includes:
    - Metadata Header & Review Priority
    - Mandatory Human Review Disclaimer
    - Key Metrics Table
    - Flags Breakdown with Concrete Evidence & Suggested Follow-up Questions
    - System Limitations Panel
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
    )
    subtitle_style = ParagraphStyle(
        "SubTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
    )
    h2_style = ParagraphStyle(
        "Heading2Custom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
    )
    disclaimer_style = ParagraphStyle(
        "DisclaimerCustom",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#475569"),
    )
    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
    )
    bold_cell_style = ParagraphStyle(
        "BoldTableCell",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
    )

    story = []

    # Title & Header
    story.append(Paragraph("CodeProvenance &mdash; Triage & Evidence Report", title_style))
    story.append(Paragraph(f"Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | Analysis ID: #{analysis.id}", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=12))

    # Review Priority Banner
    opts = analysis.options or {}
    if analysis.status == "failed":
        priority = "NOT ANALYZED"
    else:
        priority = opts.get("review_priority", "CLEAN")
    priority_colors = {
        "HIGH": colors.HexColor("#ef4444"),
        "MEDIUM": colors.HexColor("#f59e0b"),
        "LOW": colors.HexColor("#3b82f6"),
        "CLEAN": colors.HexColor("#10b981"),
        "NOT ANALYZED": colors.HexColor("#64748b"),
    }
    banner_color = priority_colors.get(priority, colors.HexColor("#64748b"))

    priority_table = Table(
        [
            [
                Paragraph(f"<b>SOURCE:</b> {analysis.source}", body_style),
                Paragraph(f"<b>INPUT:</b> {analysis.input_type.upper()}", body_style),
                Paragraph(f"<b>MODE:</b> {analysis.mode.upper()}", body_style),
                Paragraph(f"<b>TRIAGE PRIORITY:</b> <font color='{banner_color.hexval()}'><b>{priority}</b></font>", body_style),
            ]
        ],
        colWidths=[200, 75, 75, 190],
    )
    priority_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(priority_table)
    story.append(Spacer(1, 10))

    # Mandatory Disclaimer Notice
    disclaimer_table = Table(
        [[Paragraph(f"<b>MANDATORY NOTICE:</b> {MANDATORY_DISCLAIMER}", disclaimer_style)]],
        colWidths=[540],
    )
    disclaimer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef2f2") if priority == "HIGH" else colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#fca5a5") if priority == "HIGH" else colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(disclaimer_table)
    story.append(Spacer(1, 12))

    # Key Telemetry Overview Table
    story.append(Paragraph("1. Commit & Repository Telemetry", h2_style))
    total_commits = commit_metrics.get("total_commits", "N/A") if commit_metrics else "N/A"
    final_lines = commit_metrics.get("final_codebase_lines", "N/A") if commit_metrics else "N/A"
    longest_gap = f"{commit_metrics.get('longest_gap_days', 0)} days" if commit_metrics else "N/A"
    primary_lang = opts.get("languages", {}).get("primary", "Python")

    metrics_data = [
        [Paragraph("Metric", bold_cell_style), Paragraph("Value", bold_cell_style), Paragraph("Metric", bold_cell_style), Paragraph("Value", bold_cell_style)],
        [Paragraph("Total Commits", table_cell_style), Paragraph(str(total_commits), table_cell_style), Paragraph("Primary Language", table_cell_style), Paragraph(str(primary_lang), table_cell_style)],
        [Paragraph("Final Net Lines", table_cell_style), Paragraph(str(final_lines), table_cell_style), Paragraph("Longest Inactive Gap", table_cell_style), Paragraph(str(longest_gap), table_cell_style)],
        [Paragraph("Total Flags Triggered", table_cell_style), Paragraph(str(len(flags)), table_cell_style), Paragraph("Similarity Matches Found", table_cell_style), Paragraph(str(len(matches)), table_cell_style)],
    ]
    metrics_table = Table(metrics_data, colWidths=[135, 135, 135, 135])
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 14))

    # Flags & Concrete Evidence
    story.append(Paragraph(f"2. Explainable Flags & Evidentiary Signals ({len(flags)} items)", h2_style))
    if not flags:
        story.append(Paragraph("No anomalous commit pace or high-similarity signals detected.", body_style))
    else:
        for idx, flg in enumerate(flags, start=1):
            sev_badge = flg.severity.upper()
            sev_color = "#ef4444" if sev_badge == "HIGH" else "#f59e0b" if sev_badge == "MEDIUM" else "#3b82f6"
            story.append(Paragraph(f"<b>Flag {idx}: [{sev_badge}] {flg.title}</b>", ParagraphStyle(
                "FlagTitle", parent=body_style, fontName="Helvetica-Bold", fontSize=9.5, leading=13, textColor=colors.HexColor(sev_color)
            )))

            ev = flg.evidence or {}
            ev_summary = []
            if "description" in ev:
                ev_summary.append(str(ev["description"]))
            if "sha" in ev:
                ev_summary.append(f"Associated Commit SHA: {ev['sha']}")
            if "share_percentage" in ev:
                ev_summary.append(f"Codebase Proportion: {ev['share_percentage']}%")
            if "matched_functions_count" in ev:
                ev_summary.append(f"Matched Functions Count: {ev['matched_functions_count']}")

            if ev_summary:
                story.append(Paragraph("<b>Evidence:</b> " + " | ".join(ev_summary), body_style))

            questions = ev.get("questions", [])
            if questions:
                story.append(Paragraph("<b>Suggested Interview Questions:</b>", ParagraphStyle("QTitle", parent=body_style, fontName="Helvetica-Bold", fontSize=8.5)))
                for q in questions:
                    story.append(Paragraph(f"&bull; {q}", ParagraphStyle("QItem", parent=body_style, leftIndent=12, fontSize=8.5, leading=11)))
            story.append(Spacer(1, 6))

    story.append(Spacer(1, 10))

    # Structural Similarity Matches
    if matches:
        story.append(Paragraph(f"3. Structural Similarity Highlights ({len(matches)} targets)", h2_style))
        match_table_data = [
            [Paragraph("Target Reference", bold_cell_style), Paragraph("Type", bold_cell_style), Paragraph("Score", bold_cell_style), Paragraph("Matched Funcs", bold_cell_style)]
        ]
        for m in matches[:5]:
            det = m.details or {}
            match_table_data.append([
                Paragraph(str(m.target_ref)[:50], table_cell_style),
                Paragraph(str(m.target_type), table_cell_style),
                Paragraph(f"{int(m.score * 100)}%", table_cell_style),
                Paragraph(str(det.get("matched_functions_count", 0)), table_cell_style),
            ])
        match_table = Table(match_table_data, colWidths=[240, 100, 100, 100])
        match_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(match_table)
        story.append(Spacer(1, 14))

    # Limitations Panel
    story.append(Paragraph("4. Known System Limitations", h2_style))
    limitations_data = []
    for lim in SYSTEM_LIMITATIONS:
        limitations_data.append([
            Paragraph(f"&bull; <b>{lim['title']}:</b> {lim['description']}", body_style)
        ])
    lim_table = Table(limitations_data, colWidths=[540])
    lim_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(lim_table)

    # Build PDF document
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
