"""Generates clean, authentic synthetic insurance documents (PDF + 150 DPI PNG).

Supports 4 template families + 2 hard-negative families:
1. GST Tax Invoice (retail & corporate)
2. Hospital Inpatient Bill / Discharge Summary
3. Motor Vehicle Repair Estimate / Quotation
4. Insurance Claim Form
5. Hard Negatives: Mixed fonts by design & official stamped documents

Split by template family 70/15/15 (train/val/test).
"""

import os
import sys
import json
import random
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from faker import Faker
import pymupdf

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.graphics.shapes import Drawing, Circle, String as DString, Rect

# Add parent path for local imports
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from indian_numbers import format_inr, number_to_inr_words, generate_verhoeff

fake = Faker("en_IN")

# Available PDF standard fonts
FONTS = ["Helvetica", "Helvetica-Bold", "Times-Roman", "Times-Bold", "Courier", "Courier-Bold"]

TEMPLATE_SPLITS = {
    "gst_invoice_corp": "train",
    "gst_invoice_retail": "train",
    "gst_invoice_services": "val",
    "gst_invoice_export": "test",
    "hospital_bill_ipd": "train",
    "hospital_bill_surgery": "val",
    "hospital_bill_daycare": "test",
    "motor_repair_bodyshop": "train",
    "motor_repair_parts": "val",
    "claim_form_motor": "train",
    "claim_form_health": "test",
    "hard_neg_mixed_fonts": "train",
    "hard_neg_stamped": "test",
}


def _create_round_stamp(text: str = "PAID & VERIFIED", color=colors.HexColor("#0D47A1")) -> Drawing:
    d = Drawing(120, 50)
    d.add(Rect(5, 5, 110, 40, rx=5, ry=5, fillColor=None, strokeColor=color, strokeWidth=2))
    d.add(DString(15, 20, text, fontName="Helvetica-Bold", fontSize=9, fillColor=color))
    return d


def generate_clean_document(template_name: str, sample_id: str, seed: int, out_dir: Path) -> dict:
    random.seed(seed)
    fake.seed_instance(seed)

    pdf_path = out_dir / f"{sample_id}.pdf"
    png_path = out_dir / f"{sample_id}.png"
    json_path = out_dir / f"{sample_id}.json"

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    story = []

    # Metadata dictionary for downstream evaluation
    doc_metadata = {
        "sample_id": sample_id,
        "template": template_name,
        "split": TEMPLATE_SPLITS.get(template_name, "train"),
        "seed": seed,
        "created_at": datetime.now().isoformat(),
        "fields": {},
        "line_items": [],
        "pdf_path": str(pdf_path),
        "png_path": str(png_path),
        "json_path": str(json_path),
    }

    # Font setup
    body_font = "Helvetica"
    header_font = "Helvetica-Bold"
    if "mixed_fonts" in template_name:
        body_font = "Courier"
        header_font = "Times-Bold"

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName=header_font,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1A237E") if "claim" not in template_name else colors.HexColor("#880E4F"),
        alignment=0
    )
    normal_style = ParagraphStyle(
        "DocNormal",
        parent=styles["Normal"],
        fontName=body_font,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#212121")
    )
    bold_style = ParagraphStyle(
        "DocBold",
        parent=normal_style,
        fontName="Helvetica-Bold" if "mixed_fonts" not in template_name else "Times-Bold"
    )

    date_obj = fake.date_between(start_date="-1y", end_date="today")
    date_str = date_obj.strftime("%d/%m/%Y")
    due_date_str = (date_obj + timedelta(days=random.randint(15, 45))).strftime("%d/%m/%Y")

    if "gst_invoice" in template_name:
        inv_no = f"INV-{date_obj.year}-{random.randint(1000, 9999)}"
        seller_name = fake.company() + " Pvt Ltd"
        buyer_name = fake.name()
        seller_gstin = f"27{fake.bothify(text='?????####?')}1Z{fake.bothify(text='?')}".upper()
        buyer_pan = fake.bothify(text="?????####?").upper()

        story.append(Paragraph(f"TAX INVOICE - {seller_name}", title_style))
        story.append(Spacer(1, 10))

        header_data = [
            [Paragraph(f"<b>Invoice No:</b> {inv_no}", normal_style), Paragraph(f"<b>Date:</b> {date_str}", normal_style)],
            [Paragraph(f"<b>GSTIN:</b> {seller_gstin}", normal_style), Paragraph(f"<b>Due Date:</b> {due_date_str}", normal_style)],
            [Paragraph(f"<b>Billed To:</b> {buyer_name}", normal_style), Paragraph(f"<b>PAN:</b> {buyer_pan}", normal_style)],
            [Paragraph(f"<b>Address:</b> {fake.address().replace(chr(10), ', ')}", normal_style), Paragraph("<b>State Code:</b> 27 (Maharashtra)", normal_style)],
        ]
        h_table = Table(header_data, colWidths=[260, 260])
        h_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(h_table)
        story.append(Spacer(1, 15))

        # Line items
        items = []
        possible_items = [
            ("Industrial Spare Gears", 8483),
            ("Hydraulic Valve Assembly", 8481),
            ("Lubricant Grease 50L Drum", 2710),
            ("Pneumatic Control System", 8412),
            ("Electrical Relay Module", 8536),
            ("High Pressure Rubber Hose", 4009),
        ]
        chosen = random.sample(possible_items, k=random.randint(2, 4))
        subtotal = 0.0
        line_item_records = []
        table_rows = [["Sl", "Description", "HSN", "Qty", "Rate (INR)", "Amount (INR)"]]

        for i, (item_desc, hsn) in enumerate(chosen, start=1):
            qty = random.randint(1, 10)
            rate = round(random.uniform(500, 25000), 2)
            amount = round(qty * rate, 2)
            subtotal += amount
            line_item_records.append({"item": item_desc, "hsn": str(hsn), "qty": qty, "rate": rate, "amount": amount})
            table_rows.append([str(i), item_desc, str(hsn), str(qty), format_inr(rate), format_inr(amount)])

        subtotal = round(subtotal, 2)
        tax_rate = 0.18
        tax_amount = round(subtotal * tax_rate, 2)
        total_amount = round(subtotal + tax_amount, 2)
        words = number_to_inr_words(total_amount)

        table_rows.append(["", "", "", "", "Subtotal:", format_inr(subtotal)])
        table_rows.append(["", "", "", "", "IGST (18%):", format_inr(tax_amount)])
        table_rows.append(["", "", "", "", "Total Payable:", format_inr(total_amount)])

        t = Table(table_rows, colWidths=[30, 210, 60, 40, 90, 90])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EAF6")),
            ("FONTNAME", (0, 0), (-1, 0), header_font),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -4), 0.5, colors.HexColor("#9E9E9E")),
            ("LINEABOVE", (4, -3), (5, -1), 1, colors.HexColor("#1A237E")),
            ("FONTNAME", (4, -1), (5, -1), header_font),
            ("FONTSIZE", (4, -1), (5, -1), 9),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 15))

        story.append(Paragraph(f"<b>Amount in Words:</b> {words}", normal_style))
        story.append(Spacer(1, 20))

        doc_metadata["fields"] = {
            "document_type": "GST Tax Invoice",
            "invoice_number": inv_no,
            "date": date_str,
            "due_date": due_date_str,
            "seller": seller_name,
            "buyer": buyer_name,
            "subtotal": subtotal,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
            "total_amount": total_amount,
            "amount_in_words": words,
        }
        doc_metadata["line_items"] = line_item_records

    elif "hospital_bill" in template_name:
        bill_no = f"MED-HB-{random.randint(100000, 999999)}"
        hosp_name = fake.company() + " Multi-Speciality Hospital"
        patient_name = fake.name()
        admission_date = date_str
        discharge_date = (date_obj + timedelta(days=random.randint(2, 7))).strftime("%d/%m/%Y")
        patient_uhid = f"UHID-{random.randint(1000000, 9999999)}"

        story.append(Paragraph(f"{hosp_name}", title_style))
        story.append(Paragraph("INPATIENT FINAL BILL & DISCHARGE SUMMARY", bold_style))
        story.append(Spacer(1, 10))

        h_data = [
            [Paragraph(f"<b>Bill No:</b> {bill_no}", normal_style), Paragraph(f"<b>Patient:</b> {patient_name}", normal_style)],
            [Paragraph(f"<b>UHID:</b> {patient_uhid}", normal_style), Paragraph(f"<b>Age/Gender:</b> {random.randint(22, 68)} Y / {random.choice(['M', 'F'])}", normal_style)],
            [Paragraph(f"<b>Date of Admission:</b> {admission_date}", normal_style), Paragraph(f"<b>Date of Discharge:</b> {discharge_date}", normal_style)],
            [Paragraph("<b>Ward / Bed:</b> Deluxe Room 402", normal_style), Paragraph("<b>Attending Doctor:</b> Dr. " + fake.name(), normal_style)],
        ]
        t_head = Table(h_data, colWidths=[260, 260])
        t_head.setStyle(TableStyle([("PADDING", (0, 0), (-1, -1), 2)]))
        story.append(t_head)
        story.append(Spacer(1, 15))

        charges = [
            ("Room Rent & Nursing Charges (5 Days)", 25000.0),
            ("Operation Theatre & Surgical Charges", 45000.0),
            ("Anaesthesia Professional Charges", 12000.0),
            ("Pharmacy Medicines & Consumables", round(random.uniform(8500, 24000), 2)),
            ("Pathology & Biochemistry Lab Tests", 6800.0),
            ("Radiology & CT Scan Diagnostics", 7500.0),
        ]
        subtotal = round(sum(c[1] for c in charges), 2)
        discount = 0.0
        total_amount = subtotal
        words = number_to_inr_words(total_amount)

        table_rows = [["Sl", "Charge Category", "Unit Rate", "Units", "Amount (INR)"]]
        for idx, (desc, amt) in enumerate(charges, 1):
            table_rows.append([str(idx), desc, "-", "1", format_inr(amt)])
        table_rows.append(["", "", "", "Total Hospital Charges:", format_inr(total_amount)])

        t_charges = Table(table_rows, colWidths=[30, 280, 70, 40, 100])
        t_charges.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E0F2F1")),
            ("FONTNAME", (0, 0), (-1, 0), header_font),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -2), 0.5, colors.HexColor("#B2DFDB")),
            ("FONTNAME", (3, -1), (4, -1), header_font),
            ("FONTSIZE", (3, -1), (4, -1), 9),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_charges)
        story.append(Spacer(1, 15))
        story.append(Paragraph(f"<b>Amount in Words:</b> {words}", normal_style))
        story.append(Spacer(1, 20))

        doc_metadata["fields"] = {
            "document_type": "Hospital Bill",
            "bill_number": bill_no,
            "patient_name": patient_name,
            "uhid": patient_uhid,
            "admission_date": admission_date,
            "discharge_date": discharge_date,
            "hospital_name": hosp_name,
            "subtotal": subtotal,
            "total_amount": total_amount,
            "amount_in_words": words,
        }

    elif "motor_repair" in template_name:
        est_no = f"REP-EST-{random.randint(10000, 99999)}"
        workshop = fake.company() + " Authorized Auto Care"
        vehicle_reg = f"MH {random.randint(1, 48):02d} {fake.bothify(text='??').upper()} {random.randint(1000, 9999)}"
        policy_no = f"POL-MOT-{random.randint(10000000, 99999999)}"
        chassis_no = fake.bothify(text="MAT######??######").upper()

        story.append(Paragraph(f"{workshop}", title_style))
        story.append(Paragraph("MOTOR INSURANCE REPAIR ESTIMATE", bold_style))
        story.append(Spacer(1, 10))

        v_data = [
            [Paragraph(f"<b>Estimate No:</b> {est_no}", normal_style), Paragraph(f"<b>Date:</b> {date_str}", normal_style)],
            [Paragraph(f"<b>Vehicle Reg No:</b> {vehicle_reg}", normal_style), Paragraph(f"<b>Policy No:</b> {policy_no}", normal_style)],
            [Paragraph(f"<b>Chassis No:</b> {chassis_no}", normal_style), Paragraph(f"<b>Insured:</b> {fake.name()}", normal_style)],
        ]
        t_veh = Table(v_data, colWidths=[260, 260])
        story.append(t_veh)
        story.append(Spacer(1, 15))

        parts = [
            ("Front Bumper Assembly Replacement", 14500.0),
            ("Headlight RH Projector LED Unit", 18200.0),
            ("Fender Panel RH Alignment & Paint", 6500.0),
            ("Radiator Grille Frame", 4200.0),
            ("Labour: Dismantling & Refitting", 5500.0),
        ]
        subtotal = round(sum(p[1] for p in parts), 2)
        gst = round(subtotal * 0.18, 2)
        total_amount = round(subtotal + gst, 2)
        words = number_to_inr_words(total_amount)

        table_rows = [["Sl", "Repair Item Description", "Part / Labour", "Amount (INR)"]]
        for idx, (p_desc, p_amt) in enumerate(parts, 1):
            table_rows.append([str(idx), p_desc, "Parts" if "Labour" not in p_desc else "Labour", format_inr(p_amt)])
        table_rows.append(["", "", "Subtotal:", format_inr(subtotal)])
        table_rows.append(["", "", "GST (18%):", format_inr(gst)])
        table_rows.append(["", "", "Total Estimate:", format_inr(total_amount)])

        t_parts = Table(table_rows, colWidths=[30, 290, 100, 100])
        t_parts.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFF3E0")),
            ("FONTNAME", (0, 0), (-1, 0), header_font),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -4), 0.5, colors.HexColor("#FFE0B2")),
            ("FONTNAME", (2, -1), (3, -1), header_font),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_parts)
        story.append(Spacer(1, 15))
        story.append(Paragraph(f"<b>Estimate in Words:</b> {words}", normal_style))
        story.append(Spacer(1, 20))

        doc_metadata["fields"] = {
            "document_type": "Motor Repair Estimate",
            "estimate_number": est_no,
            "vehicle_reg": vehicle_reg,
            "policy_number": policy_no,
            "date": date_str,
            "subtotal": subtotal,
            "tax_amount": gst,
            "total_amount": total_amount,
            "amount_in_words": words,
        }

    else:  # Claim Form / Hard Negative
        form_no = f"CLM-DOC-{random.randint(100000, 999999)}"
        claimant = fake.name()
        policy_no = f"POL-{random.randint(10000000, 99999999)}"
        aadhaar_base = str(random.randint(20000000000, 99999999999))
        valid_aadhaar = generate_verhoeff(aadhaar_base)
        claimed_amt = float(random.randint(25, 250) * 1000)
        words = number_to_inr_words(claimed_amt)

        story.append(Paragraph("INSURANCE CLAIM SUBMISSION FORM", title_style))
        story.append(Spacer(1, 10))

        c_data = [
            [Paragraph(f"<b>Claim Reference:</b> {form_no}", normal_style), Paragraph(f"<b>Submission Date:</b> {date_str}", normal_style)],
            [Paragraph(f"<b>Policy Number:</b> {policy_no}", normal_style), Paragraph(f"<b>Claimant:</b> {claimant}", normal_style)],
            [Paragraph(f"<b>Aadhaar ID:</b> {valid_aadhaar}", normal_style), Paragraph(f"<b>Contact:</b> +91 {random.randint(7000000000, 9999999999)}", normal_style)],
            [Paragraph(f"<b>Total Claim Amount:</b> INR {format_inr(claimed_amt)}", bold_style), Paragraph(f"<b>Words:</b> {words}", normal_style)],
        ]
        t_claim = Table(c_data, colWidths=[260, 260])
        t_claim.setStyle(TableStyle([("PADDING", (0, 0), (-1, -1), 4)]))
        story.append(t_claim)
        story.append(Spacer(1, 15))
        story.append(Paragraph("<b>Declaration:</b> I hereby solemnly declare that all statements made herein are true and correct to the best of my knowledge.", normal_style))
        story.append(Spacer(1, 15))

        doc_metadata["fields"] = {
            "document_type": "Claim Form",
            "claim_number": form_no,
            "policy_number": policy_no,
            "claimant": claimant,
            "aadhaar_id": valid_aadhaar,
            "date": date_str,
            "total_amount": claimed_amt,
            "amount_in_words": words,
        }

    # Add stamp if requested in hard negative
    if "stamped" in template_name:
        story.append(Spacer(1, 10))
        story.append(_create_round_stamp("OFFICIALLY VERIFIED & APPROVED"))

    # Build PDF
    doc.build(story)

    # Render page 1 to 150 DPI PNG via PyMuPDF
    pdf_doc = pymupdf.open(str(pdf_path))
    page = pdf_doc[0]
    pix = page.get_pixmap(dpi=150)
    pix.save(str(png_path))
    pdf_doc.close()

    # Save JSON metadata
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(doc_metadata, f, indent=2)

    return doc_metadata


def generate_dataset(mode: str = "quick", base_dir: Path = None):
    if base_dir is None:
        base_dir = Path("data/training/clean")
    base_dir.mkdir(parents=True, exist_ok=True)

    templates = list(TEMPLATE_SPLITS.keys())
    count = 100 if mode == "quick" else 800

    print(f"Generating {count} clean documents ({mode} mode)...")
    samples = []
    for i in range(count):
        tmpl = templates[i % len(templates)]
        sample_id = f"clean_{i:04d}_{tmpl}"
        meta = generate_clean_document(tmpl, sample_id, seed=1000 + i, out_dir=base_dir)
        samples.append(meta)

    # Summary table
    splits = {}
    for s in samples:
        sp = s["split"]
        splits[sp] = splits.get(sp, 0) + 1
    print(f"Generated {len(samples)} clean documents: {splits}")
    return samples


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Generate ~100 samples")
    parser.add_argument("--full", action="store_true", help="Generate ~800 samples")
    args = parser.parse_args()

    mode = "full" if args.full else "quick"
    generate_dataset(mode)
