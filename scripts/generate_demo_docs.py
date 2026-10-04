"""Generates demo document samples for testing and evaluation (§23, Part 4).

Generates into data/demo_samples/docs/:
1. clean_invoice.pdf: Authentic GST invoice, correct math, single consistent font.
2. tampered_invoice.pdf: Total changed to INR 78,500 (line items = 24,000), retyped in Times-Bold, modified metadata.
3. scanned_invoice.jpg: Invoice rotated 1.5°, JPEG q70, scan texture.
4. hospital_bill.pdf: Bill total INR 42,500, but words state 'One Lakh Ten Thousand Rupees Only'.
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
import cv2
import numpy as np
import pymupdf

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfgen import canvas

# Add root path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from training.indian_numbers import format_inr, number_to_inr_words

DEMO_DIR = Path("data/demo_samples/docs")
DEMO_DIR.mkdir(parents=True, exist_ok=True)


def build_clean_invoice():
    pdf_path = DEMO_DIR / "clean_invoice.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("T", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.HexColor("#1A237E"))
    norm = ParagraphStyle("N", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=12)

    story = [
        Paragraph("TAX INVOICE - Apex Industrial Solutions Pvt Ltd", title_style),
        Spacer(1, 10),
    ]

    h_data = [
        [Paragraph("<b>Invoice No:</b> INV-2024-8842", norm), Paragraph("<b>Date:</b> 12/08/2024", norm)],
        [Paragraph("<b>GSTIN:</b> 27AAACA1234F1Z5", norm), Paragraph("<b>Due Date:</b> 12/09/2024", norm)],
        [Paragraph("<b>Billed To:</b> Reliance Logistics Ltd", norm), Paragraph("<b>State Code:</b> 27 (Maharashtra)", norm)],
    ]
    story.append(Table(h_data, colWidths=[260, 260]))
    story.append(Spacer(1, 15))

    # Items: Exactly adds up to 45,000 + 8,100 = 53,100
    rows = [
        ["Sl", "Description", "HSN", "Qty", "Rate (INR)", "Amount (INR)"],
        ["1", "Precision Ball Bearing Unit", "8482", "4", "5,000.00", "20,000.00"],
        ["2", "Hydraulic Hose Assembly", "4009", "5", "3,000.00", "15,000.00"],
        ["3", "Industrial Lubricant 20L Drum", "2710", "2", "5,000.00", "10,000.00"],
        ["", "", "", "", "Subtotal:", "45,000.00"],
        ["", "", "", "", "IGST (18%):", "8,100.00"],
        ["", "", "", "", "Total Payable:", "53,100.00"],
    ]
    t = Table(rows, colWidths=[30, 210, 60, 40, 90, 90])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EAF6")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (4, -1), (5, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -4), 0.5, colors.HexColor("#9E9E9E")),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>Amount in Words:</b> Fifty-Three Thousand One Hundred Rupees Only", norm))

    doc.build(story)
    print("Generated clean_invoice.pdf")


def build_tampered_invoice():
    pdf_path = DEMO_DIR / "tampered_invoice.pdf"

    # We build the PDF with a retyped total in Times-Bold and math discrepancy:
    # Line items = 20,000 + 4,000 = 24,000 (Subtotal: 24,000 + 4,320 = 28,320)
    # BUT Total Payable is tampered to: 88,500.00 in Times-Bold!
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("T", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.HexColor("#1A237E"))
    norm = ParagraphStyle("N", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=12)

    story = [
        Paragraph("TAX INVOICE - Bharat Engineering Works Pvt Ltd", title_style),
        Spacer(1, 10),
    ]

    h_data = [
        [Paragraph("<b>Invoice No:</b> INV-2024-9912", norm), Paragraph("<b>Date:</b> 15/07/2024", norm)],
        [Paragraph("<b>GSTIN:</b> 27BBDCE9876K1Z9", norm), Paragraph("<b>Due Date:</b> 15/08/2024", norm)],
        [Paragraph("<b>Billed To:</b> National Transport Co", norm), Paragraph("<b>State Code:</b> 27 (Maharashtra)", norm)],
    ]
    story.append(Table(h_data, colWidths=[260, 260]))
    story.append(Spacer(1, 15))

    rows = [
        ["Sl", "Description", "HSN", "Qty", "Rate (INR)", "Amount (INR)"],
        ["1", "Heavy Duty Engine Mount", "8708", "2", "10,000.00", "20,000.00"],
        ["2", "Brake Pad Lining Set", "6813", "4", "1,000.00", "4,000.00"],
        ["", "", "", "", "Subtotal:", "24,000.00"],
        ["", "", "", "", "IGST (18%):", "4,320.00"],
        ["", "", "", "", "Total Payable:", "88,500.00"],  # TAMPERED TOTAL!
    ]
    t = Table(rows, colWidths=[30, 210, 60, 40, 90, 90])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EAF6")),
        ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        # Retyped total in Times-Bold (Font Inconsistency DOC-FONT-01)
        ("FONTNAME", (4, -1), (5, -1), "Times-Bold"),
        ("TEXTCOLOR", (5, -1), (5, -1), colors.HexColor("#B71C1C")),  # Tamper visual cue
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTSIZE", (4, -1), (5, -1), 11),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -4), 0.5, colors.HexColor("#9E9E9E")),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>Amount in Words:</b> Twenty-Eight Thousand Three Hundred Twenty Rupees Only", norm))

    doc.build(story)

    # Now modify metadata using PyMuPDF to introduce DOC-META-02 (modified after creation) and producer Canva
    p_doc = pymupdf.open(str(pdf_path))
    meta = p_doc.metadata
    meta["producer"] = "Canva PDF Generator (Online Tool)"
    meta["creator"] = "iLovePDF Online Editor"
    meta["creationDate"] = "D:20240715100000Z"
    meta["modDate"] = "D:20240915153000Z"  # 62 days later
    p_doc.set_metadata(meta)
    p_doc.save(str(pdf_path), incremental=True, encryption=pymupdf.PDF_ENCRYPT_KEEP)
    p_doc.close()

    print("Generated tampered_invoice.pdf")


def build_scanned_invoice():
    # Render clean invoice to 150 DPI image, rotate by 1.5 degrees, and compress at q70
    clean_pdf = DEMO_DIR / "clean_invoice.pdf"
    p_doc = pymupdf.open(str(clean_pdf))
    page = p_doc[0]
    pix = page.get_pixmap(dpi=150)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    p_doc.close()

    h, w = img.shape[:2]
    # Rotate 1.5 degrees
    M = cv2.getRotationMatrix2D((w / 2, h / 2), 1.5, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

    # Subtle scan paper tint
    tint = np.array([0.96, 0.98, 0.99])
    scan_img = np.clip(rotated.astype(np.float32) * tint, 0, 255).astype(np.uint8)

    # Save as JPEG q70
    jpg_path = DEMO_DIR / "scanned_invoice.jpg"
    cv2.imwrite(str(jpg_path), scan_img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    print("Generated scanned_invoice.jpg")


def build_hospital_bill():
    pdf_path = DEMO_DIR / "hospital_bill.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("T", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.HexColor("#004D40"))
    norm = ParagraphStyle("N", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=12)

    story = [
        Paragraph("City Care Multi-Speciality Hospital", title_style),
        Paragraph("INPATIENT FINAL DISCHARGE BILL", ParagraphStyle("B", parent=norm, fontName="Helvetica-Bold", fontSize=11)),
        Spacer(1, 10),
    ]

    h_data = [
        [Paragraph("<b>Bill No:</b> MED-HB-772910", norm), Paragraph("<b>Patient:</b> Ramesh Kulkarni", norm)],
        [Paragraph("<b>UHID:</b> UHID-8823190", norm), Paragraph("<b>Admission:</b> 10/08/2024", norm)],
        [Paragraph("<b>Discharge:</b> 14/08/2024", norm), Paragraph("<b>Attending:</b> Dr. K. Sharma (MD)", norm)],
    ]
    story.append(Table(h_data, colWidths=[260, 260]))
    story.append(Spacer(1, 15))

    # Stated numeric total = 42,500.00
    rows = [
        ["Sl", "Charge Category", "Unit Rate", "Units", "Amount (INR)"],
        ["1", "Room Rent (Deluxe Ward - 4 Days)", "5,000.00", "4", "20,000.00"],
        ["2", "Surgical Consumables & Pharmacy", "12,500.00", "1", "12,500.00"],
        ["3", "Diagnostic Pathology & Radiology", "10,000.00", "1", "10,000.00"],
        ["", "", "", "Total Hospital Charges:", "42,500.00"],
    ]
    t = Table(rows, colWidths=[30, 280, 70, 40, 100])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E0F2F1")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (3, -1), (4, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -2), 0.5, colors.HexColor("#B2DFDB")),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))
    # DISCREPANCY: Digits = 42,500, but words state One Lakh Ten Thousand!
    story.append(Paragraph("<b>Amount in Words:</b> One Lakh Ten Thousand Rupees Only", norm))

    doc.build(story)
    print("Generated hospital_bill.pdf")


if __name__ == "__main__":
    build_clean_invoice()
    build_tampered_invoice()
    build_scanned_invoice()
    build_hospital_bill()
    print("All demo samples generated in data/demo_samples/docs/")
