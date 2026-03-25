"""
PDF Generator -- Creates payment receipts and SOAs (Statement of Account)
for Century project buyers after bank statement reconciliation.

Replaces the Salesforce receipt/SOA generation that Amit used to do manually.
Uses reportlab for professional PDF output with fam Master Agency branding.
"""

import os
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak,
)
from reportlab.pdfgen import canvas

from config.payment_settings import CENTURY_PROJECT, INSTALLMENT_TYPES, SPA_PENALTY


# fam branding colors
FAM_BLACK = HexColor("#000000")
FAM_RED = HexColor("#D51F2A")
FAM_GRAY = HexColor("#666666")
FAM_LIGHT_GRAY = HexColor("#EEEEEE")
FAM_DARK = HexColor("#1A1A1A")
FAM_WHITE = HexColor("#FFFFFF")


def _get_styles():
    """Custom paragraph styles for fam branding."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="FamTitle",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=FAM_BLACK,
        spaceAfter=4*mm,
    ))
    styles.add(ParagraphStyle(
        name="FamSubtitle",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=FAM_GRAY,
        spaceAfter=6*mm,
    ))
    styles.add(ParagraphStyle(
        name="FamHeading",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=FAM_BLACK,
        spaceBefore=6*mm,
        spaceAfter=3*mm,
    ))
    styles.add(ParagraphStyle(
        name="FamBody",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=FAM_DARK,
    ))
    styles.add(ParagraphStyle(
        name="FamBodyBold",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=FAM_DARK,
    ))
    styles.add(ParagraphStyle(
        name="FamSmall",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=FAM_GRAY,
    ))
    styles.add(ParagraphStyle(
        name="FamFooter",
        fontName="Helvetica",
        fontSize=7,
        leading=10,
        textColor=FAM_GRAY,
        alignment=TA_CENTER,
    ))
    return styles


def _header_footer(canvas_obj, doc):
    """Draw header/footer on each page."""
    canvas_obj.saveState()
    w, h = A4

    # Header bar
    canvas_obj.setFillColor(FAM_BLACK)
    canvas_obj.rect(0, h - 20*mm, w, 20*mm, fill=True, stroke=False)

    # fam logo text
    canvas_obj.setFillColor(FAM_WHITE)
    canvas_obj.setFont("Helvetica-Bold", 16)
    canvas_obj.drawString(20*mm, h - 14*mm, "fam")
    canvas_obj.setFillColor(FAM_RED)
    canvas_obj.setFont("Helvetica", 9)
    canvas_obj.drawString(38*mm, h - 14*mm, "Master Agency")

    # Right side: project name
    canvas_obj.setFillColor(FAM_WHITE)
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.drawRightString(w - 20*mm, h - 12*mm, "Century | Business Bay, Dubai")
    canvas_obj.drawRightString(w - 20*mm, h - 16*mm, f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}")

    # Footer
    canvas_obj.setFillColor(FAM_LIGHT_GRAY)
    canvas_obj.rect(0, 0, w, 12*mm, fill=True, stroke=False)
    canvas_obj.setFillColor(FAM_GRAY)
    canvas_obj.setFont("Helvetica", 7)
    canvas_obj.drawCentredString(w / 2, 5*mm,
        "fam Master Agency | A M B S Real Estate Development LLC | Century Project, Business Bay, Dubai")
    canvas_obj.drawString(20*mm, 5*mm, f"Page {doc.page}")

    # Red accent line under header
    canvas_obj.setStrokeColor(FAM_RED)
    canvas_obj.setLineWidth(1.5)
    canvas_obj.line(0, h - 20*mm, w, h - 20*mm)

    canvas_obj.restoreState()


# =========================================================================
# PAYMENT RECEIPT
# =========================================================================

def generate_receipt(
    output_path: str,
    receipt_no: str,
    unit_no: str,
    client_name: str,
    payment_date: str,
    amount: float,
    installment_type: str,
    payment_method: str = "Bank Transfer",
    reference: str = "",
    narration: str = "",
) -> str:
    """
    Generate a payment receipt PDF.
    Returns the output file path.
    """
    styles = _get_styles()
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=28*mm, bottomMargin=18*mm,
        leftMargin=20*mm, rightMargin=20*mm,
    )

    story = []

    # Title
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph("PAYMENT RECEIPT", styles["FamTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=FAM_RED, spaceAfter=4*mm))

    # Receipt details table
    receipt_data = [
        ["Receipt No:", receipt_no, "Date:", payment_date],
        ["Project:", "Century - Business Bay", "Unit No:", unit_no],
        ["Client Name:", client_name, "", ""],
    ]

    t = Table(receipt_data, colWidths=[30*mm, 55*mm, 28*mm, 55*mm])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9),
        ("FONT", (2, 0), (2, -1), "Helvetica-Bold", 9),
        ("FONT", (1, 0), (1, -1), "Helvetica", 9),
        ("FONT", (3, 0), (3, -1), "Helvetica", 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), FAM_DARK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4*mm),
    ]))
    story.append(t)
    story.append(Spacer(1, 6*mm))

    # Payment details
    story.append(Paragraph("Payment Details", styles["FamHeading"]))

    pay_data = [
        ["Description", "Details"],
        ["Installment Type", installment_type],
        ["Amount Paid", f"AED {amount:,.2f}"],
        ["Payment Method", payment_method],
        ["Transaction Reference", reference or "N/A"],
    ]
    if narration:
        pay_data.append(["Bank Narration", narration[:80]])

    pt = Table(pay_data, colWidths=[50*mm, 118*mm])
    pt.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("FONT", (0, 1), (0, -1), "Helvetica-Bold", 9),
        ("FONT", (1, 1), (1, -1), "Helvetica", 9),
        ("BACKGROUND", (0, 0), (-1, 0), FAM_BLACK),
        ("TEXTCOLOR", (0, 0), (-1, 0), FAM_WHITE),
        ("TEXTCOLOR", (0, 1), (-1, -1), FAM_DARK),
        ("BACKGROUND", (0, 1), (-1, -1), FAM_LIGHT_GRAY),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 3*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3*mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 3*mm),
    ]))
    story.append(pt)
    story.append(Spacer(1, 8*mm))

    # Escrow account details
    story.append(Paragraph("Escrow Account", styles["FamHeading"]))
    escrow = CENTURY_PROJECT["escrow_account"]
    story.append(Paragraph(f"<b>Account Name:</b> {escrow['name']}", styles["FamBody"]))
    story.append(Paragraph(f"<b>Bank:</b> {escrow['bank']}", styles["FamBody"]))
    story.append(Paragraph(f"<b>Branch:</b> {escrow['branch']}", styles["FamBody"]))
    story.append(Paragraph(f"<b>IBAN:</b> AE650260000205879166402", styles["FamBody"]))

    story.append(Spacer(1, 10*mm))

    # Disclaimer
    story.append(HRFlowable(width="100%", thickness=0.5, color=FAM_GRAY, spaceAfter=3*mm))
    story.append(Paragraph(
        "This receipt is system-generated by the fam Master Agency Payment Collector Agent. "
        "For any discrepancies, please contact ma.crm@famproperties.com.",
        styles["FamSmall"]
    ))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return output_path


# =========================================================================
# STATEMENT OF ACCOUNT (SOA)
# =========================================================================

def generate_soa(
    output_path: str,
    unit_no: str,
    client_name: str,
    sale_price: float,
    payments: list[dict],
    installment_schedule: list[dict] = None,
) -> str:
    """
    Generate a Statement of Account (SOA) PDF.

    payments: list of {date, description, amount, reference, installment_type}
    installment_schedule: list of {installment, amount, due_date, status}

    Returns the output file path.
    """
    styles = _get_styles()
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=28*mm, bottomMargin=18*mm,
        leftMargin=20*mm, rightMargin=20*mm,
    )

    story = []

    # Title
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph("STATEMENT OF ACCOUNT", styles["FamTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=FAM_RED, spaceAfter=4*mm))

    # Account details
    acct_data = [
        ["Project:", "Century - Business Bay, Dubai", "Date:", datetime.now().strftime("%d %b %Y")],
        ["Unit No:", unit_no, "Client:", client_name],
        ["Sale Price:", f"AED {sale_price:,.2f}", "", ""],
    ]

    at = Table(acct_data, colWidths=[25*mm, 60*mm, 20*mm, 63*mm])
    at.setStyle(TableStyle([
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9),
        ("FONT", (2, 0), (2, -1), "Helvetica-Bold", 9),
        ("FONT", (1, 0), (1, -1), "Helvetica", 9),
        ("FONT", (3, 0), (3, -1), "Helvetica", 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), FAM_DARK),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3*mm),
    ]))
    story.append(at)
    story.append(Spacer(1, 6*mm))

    # Payment history table
    story.append(Paragraph("Payment History", styles["FamHeading"]))

    total_paid = sum(p.get("amount", 0) for p in payments)

    pay_header = ["Date", "Description", "Reference", "Amount (AED)"]
    pay_rows = [pay_header]
    for p in payments:
        pay_rows.append([
            p.get("date", ""),
            p.get("description", p.get("installment_type", "")),
            p.get("reference", "")[:20],
            f"{p.get('amount', 0):,.2f}",
        ])
    # Total row
    pay_rows.append(["", "", "Total Paid:", f"{total_paid:,.2f}"])
    pay_rows.append(["", "", "Balance Due:", f"{max(0, sale_price - total_paid):,.2f}"])

    pt = Table(pay_rows, colWidths=[25*mm, 60*mm, 40*mm, 43*mm])
    pt.setStyle(TableStyle([
        # Header
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
        ("BACKGROUND", (0, 0), (-1, 0), FAM_BLACK),
        ("TEXTCOLOR", (0, 0), (-1, 0), FAM_WHITE),
        # Data rows
        ("FONT", (0, 1), (-1, -3), "Helvetica", 8),
        ("TEXTCOLOR", (0, 1), (-1, -3), FAM_DARK),
        ("BACKGROUND", (0, 1), (-1, -3), FAM_WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -3), [FAM_WHITE, FAM_LIGHT_GRAY]),
        # Total rows
        ("FONT", (0, -2), (-1, -1), "Helvetica-Bold", 9),
        ("BACKGROUND", (0, -2), (-1, -1), FAM_LIGHT_GRAY),
        ("TEXTCOLOR", (-1, -1), (-1, -1), FAM_RED),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (-2, -2), (-2, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5*mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 2*mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2*mm),
    ]))
    story.append(pt)
    story.append(Spacer(1, 6*mm))

    # Installment schedule (if provided)
    if installment_schedule:
        story.append(Paragraph("Upcoming Installment Schedule", styles["FamHeading"]))

        sched_header = ["Installment", "Amount (AED)", "Due Date", "Status"]
        sched_rows = [sched_header]
        for inst in installment_schedule:
            status = inst.get("status", "Pending")
            sched_rows.append([
                inst.get("installment", ""),
                f"{inst.get('amount', 0):,.2f}",
                inst.get("due_date", ""),
                status,
            ])

        st = Table(sched_rows, colWidths=[55*mm, 38*mm, 35*mm, 40*mm])
        st.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
            ("BACKGROUND", (0, 0), (-1, 0), FAM_BLACK),
            ("TEXTCOLOR", (0, 0), (-1, 0), FAM_WHITE),
            ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
            ("TEXTCOLOR", (0, 1), (-1, -1), FAM_DARK),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [FAM_WHITE, FAM_LIGHT_GRAY]),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5*mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5*mm),
            ("LEFTPADDING", (0, 0), (-1, -1), 2*mm),
        ]))
        story.append(st)
        story.append(Spacer(1, 6*mm))

    # SPA penalty notice
    story.append(Paragraph("Important Notice", styles["FamHeading"]))
    story.append(Paragraph(
        f"As per {SPA_PENALTY['clause_ref']} of the Sales and Purchase Agreement (SPA), "
        f"failure to settle any outstanding amount will incur a developer compensation charge of "
        f"{SPA_PENALTY['rate_pct_monthly']}% per month compounded {SPA_PENALTY['compounding']}.",
        styles["FamBody"]
    ))

    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=FAM_GRAY, spaceAfter=3*mm))
    story.append(Paragraph(
        "This SOA is system-generated by the fam Master Agency Payment Collector Agent. "
        "For any discrepancies, please contact ma.crm@famproperties.com.",
        styles["FamSmall"]
    ))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return output_path


# =========================================================================
# RECONCILIATION REPORT
# =========================================================================

def generate_reconciliation_report(
    output_path: str,
    period: str,
    account_name: str,
    matched_rows: list[dict],
    unmatched_rows: list[dict],
    summary: dict,
) -> str:
    """
    Generate a reconciliation report PDF for the Century team.
    Lists each transaction with matched unit details.
    """
    styles = _get_styles()
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=28*mm, bottomMargin=18*mm,
        leftMargin=15*mm, rightMargin=15*mm,
    )

    story = []

    story.append(Spacer(1, 8*mm))
    story.append(Paragraph("RECONCILIATION REPORT", styles["FamTitle"]))
    story.append(Paragraph(f"{account_name} | Period: {period}", styles["FamSubtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=FAM_RED, spaceAfter=4*mm))

    # Summary
    summary_data = [
        ["Total Credits", "Matched", "Unmatched", "Total Amount"],
        [
            str(summary.get("total_credits", 0)),
            str(summary.get("matched", 0)),
            str(summary.get("unmatched", 0)),
            f"AED {summary.get('total_amount', 0):,.2f}",
        ],
    ]
    st = Table(summary_data, colWidths=[45*mm, 45*mm, 45*mm, 45*mm])
    st.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("FONT", (0, 1), (-1, 1), "Helvetica-Bold", 14),
        ("BACKGROUND", (0, 0), (-1, 0), FAM_BLACK),
        ("TEXTCOLOR", (0, 0), (-1, 0), FAM_WHITE),
        ("BACKGROUND", (0, 1), (-1, 1), FAM_LIGHT_GRAY),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 3*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3*mm),
    ]))
    story.append(st)
    story.append(Spacer(1, 6*mm))

    # Matched transactions
    if matched_rows:
        story.append(Paragraph(f"Matched Transactions ({len(matched_rows)})", styles["FamHeading"]))

        header = ["Date", "Unit", "Client", "Amount (AED)", "Method"]
        rows = [header]
        for r in matched_rows[:100]:  # Cap at 100 for PDF size
            rows.append([
                r.get("date", "")[:10],
                r.get("unit", ""),
                r.get("client", "")[:25],
                f"{r.get('amount', 0):,.2f}",
                r.get("method", "")[:15],
            ])

        mt = Table(rows, colWidths=[22*mm, 15*mm, 55*mm, 40*mm, 48*mm])
        mt.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7),
            ("BACKGROUND", (0, 0), (-1, 0), FAM_BLACK),
            ("TEXTCOLOR", (0, 0), (-1, 0), FAM_WHITE),
            ("FONT", (0, 1), (-1, -1), "Helvetica", 7),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [FAM_WHITE, FAM_LIGHT_GRAY]),
            ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#DDDDDD")),
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5*mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5*mm),
            ("LEFTPADDING", (0, 0), (-1, -1), 1.5*mm),
        ]))
        story.append(mt)

    # Unmatched transactions
    if unmatched_rows:
        story.append(Spacer(1, 6*mm))
        story.append(Paragraph(f"Unmatched Transactions ({len(unmatched_rows)})", styles["FamHeading"]))

        header = ["Date", "Amount (AED)", "Description"]
        rows = [header]
        for r in unmatched_rows[:50]:
            rows.append([
                r.get("date", "")[:10],
                f"{r.get('amount', 0):,.2f}",
                r.get("description", "")[:60],
            ])

        ut = Table(rows, colWidths=[22*mm, 35*mm, 123*mm])
        ut.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7),
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#D51F2A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), FAM_WHITE),
            ("FONT", (0, 1), (-1, -1), "Helvetica", 7),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [FAM_WHITE, HexColor("#FFF5F5")]),
            ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#DDDDDD")),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5*mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5*mm),
            ("LEFTPADDING", (0, 0), (-1, -1), 1.5*mm),
        ]))
        story.append(ut)

    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=FAM_GRAY, spaceAfter=3*mm))
    story.append(Paragraph(
        "Generated by fam Master Agency Payment Collector Agent. "
        "For corrections, contact ma.crm@famproperties.com.",
        styles["FamSmall"]
    ))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return output_path
