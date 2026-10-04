"""
Prepares comprehensive evaluation datasets for Lucen AI:
1. data/eval/images/real (60 real photos)
2. data/eval/images/ai_full (60 AI generated photos)
3. data/eval/images/edited (60 edited/tampered photos)
4. data/eval/real_edits (15 hand-tampered documents) + originals/
5. data/eval/real_world (5 real-world style documents: ecommerce, utility, pharmacy, telecom, hospital)
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EVAL_IMAGES_REAL = os.path.join(BASE_DIR, "data", "eval", "images", "real")
EVAL_IMAGES_AI = os.path.join(BASE_DIR, "data", "eval", "images", "ai_full")
EVAL_IMAGES_EDITED = os.path.join(BASE_DIR, "data", "eval", "images", "edited")
EVAL_REAL_EDITS = os.path.join(BASE_DIR, "data", "eval", "real_edits")
EVAL_REAL_EDITS_ORIG = os.path.join(EVAL_REAL_EDITS, "originals")
EVAL_REAL_WORLD = os.path.join(BASE_DIR, "data", "eval", "real_world")

for d in [EVAL_IMAGES_REAL, EVAL_IMAGES_AI, EVAL_IMAGES_EDITED, EVAL_REAL_EDITS, EVAL_REAL_EDITS_ORIG, EVAL_REAL_WORLD]:
    os.makedirs(d, exist_ok=True)

def download_dataset_images():
    print(">>> 1. Downloading real & AI images from HuggingFace dataset...")
    # Fetch trees
    def get_tree(folder):
        url = f"https://huggingface.co/api/datasets/rmayormartins/aivshuman/tree/main/DATASET_aivshuman/{folder}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())

    # Download AI images
    ai_tree = get_tree("ai")
    print(f"Found {len(ai_tree)} AI images in remote dataset.")
    count_ai = 0
    for item in ai_tree:
        if count_ai >= 60:
            break
        path = item["path"]
        fname = f"ai_sample_{count_ai:03d}.jpg"
        target = os.path.join(EVAL_IMAGES_AI, fname)
        if os.path.exists(target) and os.path.getsize(target) > 1000:
            count_ai += 1
            continue
        try:
            encoded_path = urllib.parse.quote(path)
            raw_url = f"https://huggingface.co/datasets/rmayormartins/aivshuman/resolve/main/{encoded_path}"
            req = urllib.request.Request(raw_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
            with open(target, "wb") as f:
                f.write(data)
            count_ai += 1
            if count_ai % 10 == 0:
                print(f"Downloaded {count_ai}/60 AI images")
        except Exception as e:
            # Fallback to Picsum seed if individual download fails
            pass

    # Download Real images
    human_tree = get_tree("human")
    print(f"Found {len(human_tree)} Real human images in remote dataset.")
    count_real = 0
    for item in human_tree:
        if count_real >= 60:
            break
        path = item["path"]
        fname = f"real_sample_{count_real:03d}.jpg"
        target = os.path.join(EVAL_IMAGES_REAL, fname)
        if os.path.exists(target) and os.path.getsize(target) > 1000:
            count_real += 1
            continue
        try:
            encoded_path = urllib.parse.quote(path)
            raw_url = f"https://huggingface.co/datasets/rmayormartins/aivshuman/resolve/main/{encoded_path}"
            req = urllib.request.Request(raw_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
            with open(target, "wb") as f:
                f.write(data)
            count_real += 1
            if count_real % 10 == 0:
                print(f"Downloaded {count_real}/60 Real images")
        except Exception as e:
            pass

    # If any count < 60, fill with high-res photography from picsum
    for i in range(count_real, 60):
        target = os.path.join(EVAL_IMAGES_REAL, f"real_sample_{i:03d}.jpg")
        if not os.path.exists(target) or os.path.getsize(target) < 1000:
            url = f"https://picsum.photos/seed/real_cam_{i}/512/512"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
            with open(target, "wb") as f:
                f.write(data)
    print(f"Real images total: {len(os.listdir(EVAL_IMAGES_REAL))}")
    print(f"AI images total: {len(os.listdir(EVAL_IMAGES_AI))}")

def create_edited_images():
    print(">>> 2. Creating 60 Photoshop-style edited images for ELA/Noise calibration...")
    real_files = sorted([os.path.join(EVAL_IMAGES_REAL, f) for f in os.listdir(EVAL_IMAGES_REAL) if f.endswith(".jpg")])
    for i, rf in enumerate(real_files[:60]):
        target = os.path.join(EVAL_IMAGES_EDITED, f"edited_sample_{i:03d}.jpg")
        try:
            with Image.open(rf) as im:
                im = im.convert("RGB")
                w, h = im.size
                edited = im.copy()
                draw = ImageDraw.Draw(edited)
                # Recipes:
                # 0: Spliced patch from another image or region
                # 1: Cloned / copy-move patch
                # 2: Inpainted/blurred block
                # 3: Overlay high-contrast object/stamp
                mode = i % 4
                pw, ph = int(w * 0.25), int(h * 0.25)
                x1, y1 = int(w * 0.2), int(h * 0.2)
                if mode == 0:
                    # Splice: take patch from inverted or shifted region with different tone
                    patch = im.crop((x1, y1, x1 + pw, y1 + ph))
                    patch = patch.filter(ImageFilter.EDGE_ENHANCE_MORE)
                    edited.paste(patch, (int(w * 0.5), int(h * 0.5)))
                elif mode == 1:
                    # Copy-move
                    patch = im.crop((x1, y1, x1 + pw, y1 + ph))
                    edited.paste(patch, (x1 + 40, y1 + 40))
                elif mode == 2:
                    # Local blur / smoothing / smudge
                    patch = im.crop((x1, y1, x1 + pw, y1 + ph)).filter(ImageFilter.GaussianBlur(radius=5))
                    edited.paste(patch, (x1, y1))
                else:
                    # Local high-contrast geometric stamp / text
                    draw.rectangle([x1, y1, x1 + pw, y1 + ph], fill=(220, 20, 60))

                # Save with different JPEG quality to produce strong ELA disparity
                edited.save(target, "JPEG", quality=82)
        except Exception as e:
            print(f"Error editing sample {i}: {e}")
    print(f"Edited images total: {len(os.listdir(EVAL_IMAGES_EDITED))}")

def create_hand_tampered_documents():
    print(">>> 3. Creating 15 hand-tampered documents with originals...")
    import fitz  # PyMuPDF
    for i in range(15):
        orig_pdf_path = os.path.join(EVAL_REAL_EDITS_ORIG, f"invoice_orig_{i+1:02d}.pdf")
        tamp_pdf_path = os.path.join(EVAL_REAL_EDITS, f"invoice_tampered_{i+1:02d}.pdf")

        # 1. Create clean original PDF
        doc = fitz.open()
        page = doc.new_page(width=595, height=842) # A4
        subtotal = 50000 + i * 5000
        tax = int(round(subtotal * 0.18))
        total = subtotal + tax

        html = f"""
        <div style="font-family: sans-serif; padding: 30px;">
            <h1 style="color: #1e3a8a;">TAX INVOICE</h1>
            <p><strong>Invoice No:</strong> INV-2026-{1000+i}</p>
            <p><strong>Date:</strong> 12/03/2026</p>
            <p><strong>Customer:</strong> Rajesh Kumar</p>
            <hr/>
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                <tr style="background: #f1f5f9; text-align: left;">
                    <th style="padding: 8px;">Description</th>
                    <th style="padding: 8px;">Qty</th>
                    <th style="padding: 8px;">Rate (INR)</th>
                    <th style="padding: 8px;">Amount (INR)</th>
                </tr>
                <tr>
                    <td style="padding: 8px;">Professional IT Services</td>
                    <td style="padding: 8px;">1</td>
                    <td style="padding: 8px;">{subtotal:,.2f}</td>
                    <td style="padding: 8px;">{subtotal:,.2f}</td>
                </tr>
            </table>
            <div style="margin-top: 30px; text-align: right; width: 100%;">
                <p>Subtotal: INR {subtotal:,.2f}</p>
                <p>GST (18%): INR {tax:,.2f}</p>
                <h3>Total: INR {total:,.2f}</h3>
            </div>
        </div>
        """
        # Insert text directly
        page.insert_text((50, 60), "TAX INVOICE", fontsize=20, fontname="helv", color=(0.1, 0.2, 0.5))
        page.insert_text((50, 90), f"Invoice No: INV-2026-{1000+i}", fontsize=11, fontname="helv")
        page.insert_text((50, 110), f"Date: 12/03/2026", fontsize=11, fontname="helv")
        page.insert_text((50, 130), f"Customer: Rajesh Kumar", fontsize=11, fontname="helv")

        page.insert_text((50, 180), "Professional IT Services", fontsize=11, fontname="helv")
        page.insert_text((350, 180), "1", fontsize=11, fontname="helv")
        page.insert_text((420, 180), f"{subtotal:,.2f}", fontsize=11, fontname="helv")

        page.insert_text((380, 240), f"Subtotal: INR {subtotal:,.2f}", fontsize=11, fontname="helv")
        page.insert_text((380, 260), f"GST (18%): INR {tax:,.2f}", fontsize=11, fontname="helv")
        page.insert_text((380, 290), f"Total: INR {total:,.2f}", fontsize=13, fontname="helv")

        doc.save(orig_pdf_path)
        doc.close()

        # 2. Create tampered PDF (change total from total to total + 50,000 using overlay text & font change)
        tampered_total = total + 50000
        doc_tamp = fitz.open(orig_pdf_path)
        p = doc_tamp[0]
        # Cover old total with white rect and insert tampered total with different font (Times-Roman)
        rect = fitz.Rect(375, 275, 550, 305)
        p.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
        p.insert_text((380, 290), f"Total: INR {tampered_total:,.2f}", fontsize=13, fontname="times-bold", color=(0, 0, 0))
        doc_tamp.save(tamp_pdf_path)
        doc_tamp.close()

    print(f"Hand tampered documents created: {len(os.listdir(EVAL_REAL_EDITS))} in real_edits, {len(os.listdir(EVAL_REAL_EDITS_ORIG))} in originals")

def create_real_world_samples():
    print(">>> 4. Creating 5 realistic real-world documents in data/eval/real_world...")
    import fitz
    samples = [
        ("ecommerce_amazon_invoice.pdf", "Amazon India Tax Invoice", "Order # 408-1293847-1928374", 2499.00, 449.82, 2948.82),
        ("utility_electricity_bill.pdf", "BSES Yamuna Power Limited", "CA No: 100293847", 3410.00, 170.50, 3580.50),
        ("pharmacy_apollo_bill.pdf", "Apollo Pharmacy Retail Bill", "Bill No: APO-DEL-8921", 1250.00, 62.50, 1312.50),
        ("hospital_discharge_bill.pdf", "Max Super Speciality Hospital", "UHID: MAX.00029381", 45000.00, 0.00, 45000.00),
        ("telecom_airtel_bill.pdf", "Bharti Airtel Broadband Invoice", "Account No: 9028374615", 999.00, 179.82, 1178.82)
    ]
    for fname, title, id_str, sub, tax, tot in samples:
        doc = fitz.open()
        p = doc.new_page(width=595, height=842)
        p.insert_text((50, 60), title, fontsize=16, fontname="helv", color=(0.1, 0.1, 0.3))
        p.insert_text((50, 90), id_str, fontsize=11, fontname="helv")
        p.insert_text((50, 110), "Date: 01/02/2026", fontsize=11, fontname="helv")
        p.insert_text((50, 160), f"Base Charges: INR {sub:,.2f}", fontsize=11, fontname="helv")
        p.insert_text((50, 180), f"Taxes / Surcharges: INR {tax:,.2f}", fontsize=11, fontname="helv")
        p.insert_text((50, 210), f"Total Payable: INR {tot:,.2f}", fontsize=13, fontname="helv")
        p.insert_text((50, 240), f"Status: Paid Successfully", fontsize=10, fontname="helv", color=(0, 0.5, 0))
        target = os.path.join(EVAL_REAL_WORLD, fname)
        doc.save(target)
        doc.close()
    print(f"Real world test documents created: {len(os.listdir(EVAL_REAL_WORLD))}")

if __name__ == "__main__":
    download_dataset_images()
    create_edited_images()
    create_hand_tampered_documents()
    create_real_world_samples()
    print("\nDataset preparation complete!")
