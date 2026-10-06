"""
Sample Invoice Generator for DocFlow V1 (Person B - Task B1)

Generates 8 invoice test files + 1 failme.pdf in samples/invoices/
and corresponding expected ground-truth JSON files in samples/expected/.
"""

import json
import os
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import numpy as np

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable


BASE_DIR = Path(__file__).resolve().parent
INVOICES_DIR = BASE_DIR / "invoices"
EXPECTED_DIR = BASE_DIR / "expected"

INVOICES_DIR.mkdir(parents=True, exist_ok=True)
EXPECTED_DIR.mkdir(parents=True, exist_ok=True)


def create_pdf_invoice(
    filepath: Path,
    vendor_name: str,
    vendor_address: str,
    gstin: str,
    invoice_number: str,
    invoice_date: str,
    currency: str,
    items: list[dict],
    subtotal: str,
    tax: str,
    total: str,
    custom_note: str = "",
    alt_style: bool = False,
):
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle(
        "HeaderTitle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1e293b") if not alt_style else colors.HexColor("#0f172a"),
    )
    subtitle_style = ParagraphStyle(
        "SubTitle",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#475569"),
    )
    bold_style = ParagraphStyle(
        "BoldText",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    # Title & Vendor Header
    header_data = [
        [
            Paragraph(f"<b>{vendor_name}</b>", header_style),
            Paragraph(f"<font size=16 color='#0284c7'><b>TAX INVOICE</b></font>", ParagraphStyle("RAlign", parent=styles["Normal"], alignment=2)),
        ],
        [
            Paragraph(f"{vendor_address}<br/><b>GSTIN:</b> {gstin}", subtitle_style),
            Paragraph(
                f"<b>Invoice No:</b> {invoice_number}<br/>"
                f"<b>Invoice Date:</b> {invoice_date}<br/>"
                f"<b>Currency:</b> {currency}",
                ParagraphStyle("RAlignSub", parent=subtitle_style, alignment=2),
            ),
        ],
    ]

    header_table = Table(header_data, colWidths=[300, 215])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#cbd5e1"), spaceAfter=15))

    # Bill To Section
    bill_data = [
        [
            Paragraph("<b>Billed To:</b>", bold_style),
            Paragraph("<b>Ship To:</b>", bold_style),
        ],
        [
            Paragraph("Horizon Enterprises Pvt. Ltd.<br/>402, Trade Tower, Bandra Kurla Complex<br/>Mumbai, Maharashtra 400051<br/>GSTIN: 27AABCH1234F1Z1", subtitle_style),
            Paragraph("Horizon Warehouse 3<br/>Plot 12, TTC Industrial Area, MIDC<br/>Navi Mumbai, Maharashtra 400705", subtitle_style),
        ],
    ]
    bill_table = Table(bill_data, colWidths=[260, 255])
    bill_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(bill_table)
    story.append(Spacer(1, 15))

    # Line Items Table
    table_content = [
        [
            Paragraph("<b>#</b>", bold_style),
            Paragraph("<b>Description</b>", bold_style),
            Paragraph("<b>Qty</b>", bold_style),
            Paragraph(f"<b>Rate ({currency})</b>", bold_style),
            Paragraph(f"<b>Amount ({currency})</b>", bold_style),
        ]
    ]

    for idx, it in enumerate(items, 1):
        table_content.append(
            [
                Paragraph(str(idx), subtitle_style),
                Paragraph(it["description"], subtitle_style),
                Paragraph(str(it["quantity"]), subtitle_style),
                Paragraph(f"{float(it['rate']):.2f}", subtitle_style),
                Paragraph(f"{float(it['amount']):.2f}", subtitle_style),
            ]
        )

    items_table = Table(table_content, colWidths=[30, 245, 60, 90, 90])
    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9") if not alt_style else colors.HexColor("#e2e8f0")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    story.append(items_table)
    story.append(Spacer(1, 15))

    # Totals Summary
    totals_data = [
        [Paragraph("<b>Subtotal:</b>", subtitle_style), Paragraph(f"<b>{currency} {subtotal}</b>", ParagraphStyle("TR1", parent=subtitle_style, alignment=2))],
        [Paragraph("<b>Tax (GST):</b>", subtitle_style), Paragraph(f"<b>{currency} {tax}</b>", ParagraphStyle("TR2", parent=subtitle_style, alignment=2))],
        [Paragraph("<font size=11><b>Grand Total:</b></font>", bold_style), Paragraph(f"<font size=11 color='#0284c7'><b>{currency} {total}</b></font>", ParagraphStyle("TR3", parent=bold_style, alignment=2))],
    ]

    totals_table = Table(totals_data, colWidths=[380, 135])
    totals_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LINEABOVE", (0, 2), (-1, 2), 1, colors.HexColor("#94a3b8")),
            ]
        )
    )
    story.append(totals_table)

    if custom_note:
        story.append(Spacer(1, 15))
        story.append(Paragraph(f"<i>Note: {custom_note}</i>", subtitle_style))

    story.append(Spacer(1, 30))
    story.append(Paragraph("This is a computer-generated invoice and requires no signature.", ParagraphStyle("Foot", parent=subtitle_style, alignment=1, textColor=colors.HexColor("#94a3b8"))))

    doc.build(story)


def create_sample_expected_json(
    filepath: Path,
    vendor_name: str,
    invoice_number: str,
    invoice_date: str,
    gstin: str,
    currency: str,
    subtotal: str,
    tax: str,
    total: str,
    line_items: list[dict],
    default_conf: float = 0.98,
):
    data = {
        "document_type": "invoice",
        "fields": {
            "vendor_name": {"value": vendor_name, "confidence": default_conf, "bbox": None},
            "invoice_number": {"value": invoice_number, "confidence": default_conf, "bbox": None},
            "invoice_date": {"value": invoice_date, "confidence": default_conf, "bbox": None},
            "gstin": {"value": gstin, "confidence": default_conf, "bbox": None},
            "currency": {"value": currency, "confidence": default_conf, "bbox": None},
            "subtotal": {"value": subtotal, "confidence": default_conf, "bbox": None},
            "tax": {"value": tax, "confidence": default_conf, "bbox": None},
            "total": {"value": total, "confidence": default_conf, "bbox": None},
        },
        "line_items": [
            {
                "description": it["description"],
                "quantity": str(it["quantity"]),
                "rate": f"{float(it['rate']):.2f}",
                "amount": f"{float(it['amount']):.2f}",
                "confidence": default_conf,
            }
            for it in line_items
        ],
        "raw_model_output": None,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def render_invoice_to_image(
    vendor_name: str,
    vendor_address: str,
    gstin: str,
    invoice_number: str,
    invoice_date: str,
    currency: str,
    items: list[dict],
    subtotal: str,
    tax: str,
    total: str,
    width: int = 1200,
    height: int = 1600,
) -> Image.Image:
    """Create a crisp invoice image using Pillow."""
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Margins and header
    margin = 80
    y = 80

    # Header
    draw.text((margin, y), vendor_name, fill=(30, 41, 59))
    draw.text((width - margin - 220, y), "TAX INVOICE", fill=(2, 132, 199))
    y += 40

    draw.text((margin, y), f"{vendor_address}", fill=(71, 85, 105))
    draw.text((width - margin - 220, y), f"Invoice No: {invoice_number}", fill=(71, 85, 105))
    y += 25
    draw.text((margin, y), f"GSTIN: {gstin}", fill=(15, 23, 42))
    draw.text((width - margin - 220, y), f"Date: {invoice_date}", fill=(71, 85, 105))
    y += 25
    draw.text((width - margin - 220, y), f"Currency: {currency}", fill=(71, 85, 105))
    y += 45

    # Line separator
    draw.line([(margin, y), (width - margin, y)], fill=(203, 213, 225), width=3)
    y += 30

    # Billed To
    draw.text((margin, y), "Billed To:", fill=(15, 23, 42))
    draw.text((margin + 500, y), "Ship To:", fill=(15, 23, 42))
    y += 25
    draw.text((margin, y), "Horizon Enterprises Pvt. Ltd.\n402, Trade Tower, BKC, Mumbai\nGSTIN: 27AABCH1234F1Z1", fill=(71, 85, 105))
    draw.text((margin + 500, y), "Horizon Warehouse 3\nPlot 12, TTC MIDC, Navi Mumbai", fill=(71, 85, 105))
    y += 85

    # Table Header
    draw.rectangle([(margin, y), (width - margin, y + 40)], fill=(241, 245, 249))
    draw.text((margin + 15, y + 10), "#", fill=(15, 23, 42))
    draw.text((margin + 70, y + 10), "Description", fill=(15, 23, 42))
    draw.text((margin + 520, y + 10), "Qty", fill=(15, 23, 42))
    draw.text((margin + 640, y + 10), f"Rate ({currency})", fill=(15, 23, 42))
    draw.text((margin + 840, y + 10), f"Amount ({currency})", fill=(15, 23, 42))
    y += 40

    for idx, it in enumerate(items, 1):
        draw.line([(margin, y), (width - margin, y)], fill=(226, 232, 240), width=1)
        draw.text((margin + 15, y + 12), str(idx), fill=(71, 85, 105))
        draw.text((margin + 70, y + 12), it["description"], fill=(71, 85, 105))
        draw.text((margin + 520, y + 12), str(it["quantity"]), fill=(71, 85, 105))
        draw.text((margin + 640, y + 12), f"{float(it['rate']):.2f}", fill=(71, 85, 105))
        draw.text((margin + 840, y + 12), f"{float(it['amount']):.2f}", fill=(71, 85, 105))
        y += 40

    draw.line([(margin, y), (width - margin, y)], fill=(203, 213, 225), width=2)
    y += 30

    # Totals
    draw.text((width - margin - 350, y), "Subtotal:", fill=(71, 85, 105))
    draw.text((width - margin - 150, y), f"{currency} {subtotal}", fill=(71, 85, 105))
    y += 30
    draw.text((width - margin - 350, y), "Tax (GST):", fill=(71, 85, 105))
    draw.text((width - margin - 150, y), f"{currency} {tax}", fill=(71, 85, 105))
    y += 35
    draw.line([(width - margin - 360, y), (width - margin, y)], fill=(148, 163, 184), width=2)
    y += 10
    draw.text((width - margin - 350, y), "Grand Total:", fill=(15, 23, 42))
    draw.text((width - margin - 150, y), f"{currency} {total}", fill=(2, 132, 199))

    return img


def generate_all_samples():
    print("Generating DocFlow V1 sample invoices and expected JSONs...")

    # Sample 1: clean_invoice.pdf
    s1_vendor = "Apex Infotech Solutions Pvt Ltd"
    s1_addr = "801, Prestige Tech Park, Marathahalli, Bangalore 560103"
    s1_gstin = "27AABCA1234F1Z5"
    s1_inv_num = "INV-2026-001"
    s1_date = "2026-09-15"
    s1_currency = "INR"
    s1_items = [
        {"description": "Cloud Hosting Subscription", "quantity": "1", "rate": "5000.00", "amount": "5000.00"},
        {"description": "Technical Support Services", "quantity": "10", "rate": "350.00", "amount": "3500.00"},
        {"description": "SSL Certificate 1-Yr", "quantity": "1", "rate": "1500.00", "amount": "1500.00"},
    ]
    s1_subtotal = "10000.00"
    s1_tax = "1800.00"
    s1_total = "11800.00"

    p1 = INVOICES_DIR / "clean_invoice.pdf"
    create_pdf_invoice(p1, s1_vendor, s1_addr, s1_gstin, s1_inv_num, s1_date, s1_currency, s1_items, s1_subtotal, s1_tax, s1_total)
    create_sample_expected_json(EXPECTED_DIR / "clean_invoice.json", s1_vendor, s1_inv_num, s1_date, s1_gstin, s1_currency, s1_subtotal, s1_tax, s1_total, s1_items)
    print("[OK] Created clean_invoice.pdf and expected JSON")

    # Sample 2: scanned_invoice.pdf
    s2_vendor = "Bharat Heavy Logistics Ltd"
    s2_addr = "Plot 45, Transport Nagar, Nigdi, Pune 411044"
    s2_gstin = "29AABCB5678G1Z2"
    s2_inv_num = "INV-2026-882"
    s2_date = "2026-08-20"
    s2_currency = "INR"
    s2_items = [
        {"description": "Freight Transport (Bangalore to Mumbai)", "quantity": "2", "rate": "12000.00", "amount": "24000.00"},
        {"description": "Loading and Unloading Charges", "quantity": "1", "rate": "2500.00", "amount": "2500.00"},
    ]
    s2_subtotal = "26500.00"
    s2_tax = "4770.00"
    s2_total = "31270.00"

    # Create image, apply scan skew / noise, save as PDF
    img_s2 = render_invoice_to_image(s2_vendor, s2_addr, s2_gstin, s2_inv_num, s2_date, s2_currency, s2_items, s2_subtotal, s2_tax, s2_total)
    # Skew slightly (1.2 degrees)
    img_s2_rot = img_s2.rotate(1.2, resample=Image.BICUBIC, expand=False, fillcolor=(248, 248, 248))
    # Add slight grayscale scanner contrast
    enhancer = ImageEnhance.Contrast(img_s2_rot)
    img_s2_proc = enhancer.enhance(1.1)
    # Save as scanned PDF
    img_s2_proc.save(str(INVOICES_DIR / "scanned_invoice.pdf"), "PDF", resolution=150.0)
    create_sample_expected_json(EXPECTED_DIR / "scanned_invoice.json", s2_vendor, s2_inv_num, s2_date, s2_gstin, s2_currency, s2_subtotal, s2_tax, s2_total, s2_items)
    print("[OK] Created scanned_invoice.pdf and expected JSON")

    # Sample 3: photo_invoice.jpg
    s3_vendor = "Krishna Stationery & Office Supplies"
    s3_addr = "Shop 14, Main Market, Connaught Place, New Delhi 110001"
    s3_gstin = "07AABCD9012H1Z8"
    s3_inv_num = "INV-2026-304"
    s3_date = "2026-07-10"
    s3_currency = "INR"
    s3_items = [
        {"description": "A4 Paper Reams", "quantity": "20", "rate": "250.00", "amount": "5000.00"},
        {"description": "Whiteboard Markers Box", "quantity": "5", "rate": "300.00", "amount": "1500.00"},
    ]
    s3_subtotal = "6500.00"
    s3_tax = "1170.00"
    s3_total = "7670.00"

    img_s3 = render_invoice_to_image(s3_vendor, s3_addr, s3_gstin, s3_inv_num, s3_date, s3_currency, s3_items, s3_subtotal, s3_tax, s3_total)
    # Add perspective transform & slight warm lighting for photo look
    w, h = img_s3.size
    # Slight perspective trapezoid
    coeffs = (1.02, 0.03, -20, 0.01, 1.01, -15, 0.00003, 0.00001)
    img_s3_photo = img_s3.transform((w, h), Image.PERSPECTIVE, coeffs, Image.BICUBIC, fillcolor=(220, 215, 205))
    # Slight warmth / lighting gradient
    overlay = Image.new("RGB", (w, h), (250, 245, 235))
    img_s3_final = Image.blend(img_s3_photo, overlay, 0.08)
    img_s3_final.save(str(INVOICES_DIR / "photo_invoice.jpg"), "JPEG", quality=88)
    create_sample_expected_json(EXPECTED_DIR / "photo_invoice.json", s3_vendor, s3_inv_num, s3_date, s3_gstin, s3_currency, s3_subtotal, s3_tax, s3_total, s3_items)
    print("[OK] Created photo_invoice.jpg and expected JSON")

    # Sample 4: blurry_invoice.png
    s4_vendor = "Sunrise Electricals Pvt Ltd"
    s4_addr = "12, Industrial Estate, Guindy, Chennai 600032"
    s4_gstin = "33AABCE3456J1Z1"
    s4_inv_num = "INV-2026-119"
    s4_date = "2026-06-05"
    s4_currency = "INR"
    s4_items = [
        {"description": "LED Tube Lights 20W", "quantity": "50", "rate": "180.00", "amount": "9000.00"},
        {"description": "Copper Wiring Roll", "quantity": "2", "rate": "3000.00", "amount": "6000.00"},
    ]
    s4_subtotal = "15000.00"
    s4_tax = "2700.00"
    s4_total = "17700.00"

    img_s4 = render_invoice_to_image(s4_vendor, s4_addr, s4_gstin, s4_inv_num, s4_date, s4_currency, s4_items, s4_subtotal, s4_tax, s4_total)
    # Heavy Gaussian Blur to trigger low confidence
    img_s4_blur = img_s4.filter(ImageFilter.GaussianBlur(radius=3.5))
    img_s4_blur.save(str(INVOICES_DIR / "blurry_invoice.png"), "PNG")
    # For blurry_invoice.png, expected JSON retains ground truth values
    create_sample_expected_json(EXPECTED_DIR / "blurry_invoice.json", s4_vendor, s4_inv_num, s4_date, s4_gstin, s4_currency, s4_subtotal, s4_tax, s4_total, s4_items, default_conf=0.60)
    print("[OK] Created blurry_invoice.png and expected JSON")

    # Sample 5: wrong_total.pdf (total != subtotal + tax, everything else valid)
    s5_vendor = "Metro Hardware Supplies"
    s5_addr = "22, Lamington Road, Grant Road, Mumbai 400007"
    s5_gstin = "27AABCF7890K1Z4"
    s5_inv_num = "INV-2026-550"
    s5_date = "2026-09-01"
    s5_currency = "INR"
    s5_items = [
        {"description": "Industrial Power Drill", "quantity": "2", "rate": "4000.00", "amount": "8000.00"},
        {"description": "Drill Bit Set", "quantity": "4", "rate": "500.00", "amount": "2000.00"},
    ]
    s5_subtotal = "10000.00"
    s5_tax = "1800.00"
    s5_total = "11500.00"  # DELIBERATE MISMATCH: 10000 + 1800 = 11800 != 11500

    create_pdf_invoice(INVOICES_DIR / "wrong_total.pdf", s5_vendor, s5_addr, s5_gstin, s5_inv_num, s5_date, s5_currency, s5_items, s5_subtotal, s5_tax, s5_total)
    create_sample_expected_json(EXPECTED_DIR / "wrong_total.json", s5_vendor, s5_inv_num, s5_date, s5_gstin, s5_currency, s5_subtotal, s5_tax, s5_total, s5_items)
    print("[OK] Created wrong_total.pdf and expected JSON")

    # Sample 6: bad_gstin.pdf (Invalid GSTIN format, everything else valid)
    s6_vendor = "Delta Industrial Tools"
    s6_addr = "104, Peenya Industrial Area, Phase 1, Bangalore 560058"
    s6_gstin = "27INVALIDGSTIN99"  # DELIBERATELY INVALID GSTIN
    s6_inv_num = "INV-2026-702"
    s6_date = "2026-09-10"
    s6_currency = "INR"
    s6_items = [
        {"description": "Heavy Duty Clamps", "quantity": "10", "rate": "450.00", "amount": "4500.00"},
        {"description": "Safety Helmets", "quantity": "5", "rate": "300.00", "amount": "1500.00"},
    ]
    s6_subtotal = "6000.00"
    s6_tax = "1080.00"
    s6_total = "7080.00"

    create_pdf_invoice(INVOICES_DIR / "bad_gstin.pdf", s6_vendor, s6_addr, s6_gstin, s6_inv_num, s6_date, s6_currency, s6_items, s6_subtotal, s6_tax, s6_total)
    create_sample_expected_json(EXPECTED_DIR / "bad_gstin.json", s6_vendor, s6_inv_num, s6_date, s6_gstin, s6_currency, s6_subtotal, s6_tax, s6_total, s6_items)
    print("[OK] Created bad_gstin.pdf and expected JSON")

    # Sample 7: clean_invoice_copy.pdf (Byte-identical copy of clean_invoice.pdf)
    shutil.copyfile(INVOICES_DIR / "clean_invoice.pdf", INVOICES_DIR / "clean_invoice_copy.pdf")
    shutil.copyfile(EXPECTED_DIR / "clean_invoice.json", EXPECTED_DIR / "clean_invoice_copy.json")
    print("[OK] Created clean_invoice_copy.pdf (byte-identical copy) and expected JSON")

    # Sample 8: same_invoice_resaved.pdf (Same vendor + invoice number as clean_invoice, but DIFFERENT bytes)
    create_pdf_invoice(
        INVOICES_DIR / "same_invoice_resaved.pdf",
        s1_vendor,
        s1_addr,
        s1_gstin,
        s1_inv_num,
        s1_date,
        s1_currency,
        s1_items,
        s1_subtotal,
        s1_tax,
        s1_total,
        custom_note="Re-printed copy for accounts archive.",
        alt_style=True,
    )
    shutil.copyfile(EXPECTED_DIR / "clean_invoice.json", EXPECTED_DIR / "same_invoice_resaved.json")
    print("[OK] Created same_invoice_resaved.pdf (business duplicate, different bytes) and expected JSON")

    # Sample 9: failme.pdf (For retry demo)
    s9_vendor = "Faulty Test Services Pvt Ltd"
    s9_addr = "101, Test Road, Cyber City, Gurugram 122002"
    s9_gstin = "06AABCT9999Z1Z9"
    s9_inv_num = "INV-FAIL-001"
    s9_date = "2026-09-20"
    s9_currency = "INR"
    s9_items = [
        {"description": "Diagnostics Testing", "quantity": "1", "rate": "1000.00", "amount": "1000.00"},
    ]
    s9_subtotal = "1000.00"
    s9_tax = "180.00"
    s9_total = "1180.00"
    create_pdf_invoice(INVOICES_DIR / "failme.pdf", s9_vendor, s9_addr, s9_gstin, s9_inv_num, s9_date, s9_currency, s9_items, s9_subtotal, s9_tax, s9_total)
    create_sample_expected_json(EXPECTED_DIR / "failme.json", s9_vendor, s9_inv_num, s9_date, s9_gstin, s9_currency, s9_subtotal, s9_tax, s9_total, s9_items)
    print("[OK] Created failme.pdf and expected JSON")

    print("\nAll sample generation completed successfully!")


if __name__ == "__main__":
    generate_all_samples()
