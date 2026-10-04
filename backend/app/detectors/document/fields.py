"""Document field extraction engine using regex and OCR bounding box mapping (§11.1 Step 6).

Extracts:
- Document dates (DD/MM/YYYY, YYYY-MM-DD)
- Currency amounts (₹, INR, Rs., Indian comma formatting)
- Invoice / Policy / Claim / UHID numbers
- Tax rates and percentages
- Line items (quantities, rates, item totals)
- Subtotal and Total amounts
- Amount in words (English / Indian words)
- Aadhaar (12-digit) and PAN numbers
- Maps extracted strings back to page bounding boxes
"""

from typing import Dict, Any, List, Optional
import re
from ...core.config import settings
from ...schemas.evidence import Evidence
from ..base import Detector, DetectorOutput, AnalysisContext
from .word_features import extract_word_features
from ...core.formatters import parse_inr_words_to_number


def _clean_amount_str(s: str) -> Optional[float]:
    clean = re.sub(r"[^\d.]", "", s.replace(",", ""))
    try:
        return float(clean)
    except Exception:
        return None


class DocumentFieldsDetector(Detector):
    name: str = "document_fields"

    def run(self, ctx: AnalysisContext) -> DetectorOutput:
        ocr_pages = ctx.runtime_data.get("ocr_pages", [])
        pdf_spans_pages = ctx.runtime_data.get("pdf_spans", [])

        # Accumulate text and word boxes across pages
        fields: Dict[str, Any] = {
            "invoice_numbers": [],
            "policy_numbers": [],
            "claim_numbers": [],
            "dates": [],
            "amounts": [],
            "subtotal": None,
            "tax_amount": None,
            "total_amount": None,
            "tax_percentage": None,
            "amount_in_words": None,
            "parsed_words_amount": None,
            "aadhaar_numbers": [],
            "pan_numbers": [],
            "line_items": [],
            "llm": "skipped"
        }

        # 1. If PDF, extract high-precision digital blocks and text
        is_pdf = str(ctx.file_path).lower().endswith(".pdf")
        if is_pdf and ctx.file_path.exists():
            try:
                import pymupdf
                doc = pymupdf.open(str(ctx.file_path))
                for page_idx in range(len(doc)):
                    page = doc[page_idx]
                    pw = page.rect.width
                    ph = page.rect.height
                    full_text = page.get_text("text")

                    for m in re.finditer(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b", full_text):
                        d_str = m.group(1)
                        if not any(d["text"] == d_str for d in fields["dates"]):
                            fields["dates"].append({"text": d_str, "page": page_idx + 1})

                    for m in re.finditer(r"\b(INV-[A-Za-z0-9-]+|REP-EST-[A-Za-z0-9-]+|MED-HB-[A-Za-z0-9-]+)\b", full_text):
                        if not any(i["text"] == m.group(1) for i in fields["invoice_numbers"]):
                            fields["invoice_numbers"].append({"text": m.group(1), "page": page_idx + 1})

                    for m in re.finditer(r"\b(POL-[A-Za-z0-9-]+|CLM-DOC-[A-Za-z0-9-]+)\b", full_text):
                        if not any(p["text"] == m.group(1) for p in fields["policy_numbers"]):
                            fields["policy_numbers"].append({"text": m.group(1), "page": page_idx + 1})

                    for m in re.finditer(r"\b(\d{4}\s?\d{4}\s?\d{4})\b", full_text):
                        clean_a = m.group(1).replace(" ", "")
                        if not any(a["text"] == clean_a for a in fields["aadhaar_numbers"]):
                            fields["aadhaar_numbers"].append({"text": clean_a, "page": page_idx + 1})

                    for m in re.finditer(r"\b([A-Z]{5}\d{4}[A-Z])\b", full_text):
                        if not any(p["text"] == m.group(1) for p in fields["pan_numbers"]):
                            fields["pan_numbers"].append({"text": m.group(1), "page": page_idx + 1})

                    tpm = re.search(r"\b(\d{1,2}(?:\.\d{1,2})?)\s?%\b", full_text)
                    if tpm and fields["tax_percentage"] is None:
                        try:
                            fields["tax_percentage"] = float(tpm.group(1))
                        except Exception:
                            pass

                    wm = re.search(r"(?:amount in words|estimate in words|words|sum of rupees)[:\s]+([A-Za-z\s-]+(?:Rupees|Rupee)?[A-Za-z\s-]*(?:Only)?)", full_text, re.IGNORECASE)
                    if wm and fields["amount_in_words"] is None:
                        w_text = wm.group(1).strip()
                        fields["amount_in_words"] = w_text
                        parsed_val = parse_inr_words_to_number(w_text)
                        if parsed_val > 0:
                            fields["parsed_words_amount"] = parsed_val

                    # Blocks for line items, subtotals, tax, totals
                    blocks = page.get_text("blocks")
                    for b in blocks:
                        bx0, by0, bx1, by1, btext, b_no, b_type = b
                        norm_box = [round(bx0 / pw, 4), round(by0 / ph, 4), round((bx1 - bx0) / pw, 4), round((by1 - by0) / ph, 4)]
                        btext_clean = btext.strip()

                        if re.search(r"\b(total payable|grand total|total hospital charges|total estimate|claim amount|total:)\b", btext_clean, re.IGNORECASE) and not re.search(r"\bsub[\s-]?total\b", btext_clean, re.IGNORECASE):
                            amts = re.findall(r"([\d,]+(?:\.\d{2})?)", btext_clean)
                            if amts:
                                val = _clean_amount_str(amts[-1])
                                if val and val > 100:
                                    fields["total_amount"] = {"value": val, "bbox": norm_box, "page": page_idx + 1}
                        elif re.search(r"\bsub[\s-]?total\b", btext_clean, re.IGNORECASE):
                            amts = re.findall(r"([\d,]+\.\d{2})", btext_clean)
                            if amts:
                                val = _clean_amount_str(amts[-1])
                                if val:
                                    fields["subtotal"] = {"value": val, "bbox": norm_box, "page": page_idx + 1}
                        elif re.search(r"\b(IGST|CGST|SGST|Tax)\b", btext_clean, re.IGNORECASE) and not re.search(r"\btax\s+invoice\b", btext_clean, re.IGNORECASE):
                            amts = re.findall(r"([\d,]+\.\d{2})", btext_clean)
                            if amts:
                                val = _clean_amount_str(amts[-1])
                                if val:
                                    fields["tax_amount"] = {"value": val, "bbox": norm_box, "page": page_idx + 1}
                        elif re.match(r"^\d+\n", btext_clean):
                            row_lines = btext_clean.split("\n")
                            amts = [_clean_amount_str(x) for x in row_lines if re.match(r"^[\d,]+\.\d{2}$", x.strip())]
                            amts = [a for a in amts if a is not None]
                            if amts:
                                desc = row_lines[1] if len(row_lines) > 1 else btext_clean
                                fields["line_items"].append({
                                    "description": desc,
                                    "amount": amts[-1],
                                    "bbox": norm_box,
                                    "page": page_idx + 1
                                })
                doc.close()
            except Exception:
                pass

        # 2. Extract from OCR lines with lookahead (essential for scanned images or fallback)
        for p_idx, p_data in enumerate(ocr_pages):
            page_no = p_data.get("page", p_idx + 1)
            lines = p_data.get("lines", [])
            words = p_data.get("words", [])
            page_full_text = "\n".join(l.get("text", "") for l in lines)

            # Dates
            date_matches = list(re.finditer(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b", page_full_text))
            for m in date_matches:
                d_str = m.group(1)
                matched_box = next((w["normalized_bbox"] for w in words if d_str in w["text"]), None)
                if not any(d["text"] == d_str for d in fields["dates"]):
                    fields["dates"].append({"text": d_str, "page": page_no, "bbox": matched_box})

            # Identifiers
            inv_matches = re.finditer(r"\b(INV-[A-Za-z0-9-]+|REP-EST-[A-Za-z0-9-]+|MED-HB-[A-Za-z0-9-]+)\b", page_full_text)
            for m in inv_matches:
                matched_box = next((w["normalized_bbox"] for w in words if m.group(1) in w["text"]), None)
                if not any(i["text"] == m.group(1) for i in fields["invoice_numbers"]):
                    fields["invoice_numbers"].append({"text": m.group(1), "page": page_no, "bbox": matched_box})

            pol_matches = re.finditer(r"\b(POL-[A-Za-z0-9-]+|CLM-DOC-[A-Za-z0-9-]+)\b", page_full_text)
            for m in pol_matches:
                matched_box = next((w["normalized_bbox"] for w in words if m.group(1) in w["text"]), None)
                if not any(p["text"] == m.group(1) for p in fields["policy_numbers"]):
                    fields["policy_numbers"].append({"text": m.group(1), "page": page_no, "bbox": matched_box})

            # Aadhaar & PAN
            aadhaar_matches = re.finditer(r"\b(\d{4}\s?\d{4}\s?\d{4})\b", page_full_text)
            for m in aadhaar_matches:
                clean_a = m.group(1).replace(" ", "")
                matched_box = next((w["normalized_bbox"] for w in words if clean_a[:4] in w["text"]), None)
                if not any(a["text"] == clean_a for a in fields["aadhaar_numbers"]):
                    fields["aadhaar_numbers"].append({"text": clean_a, "page": page_no, "bbox": matched_box})

            pan_matches = re.finditer(r"\b([A-Z]{5}\d{4}[A-Z])\b", page_full_text)
            for m in pan_matches:
                if not any(p["text"] == m.group(1) for p in fields["pan_numbers"]):
                    fields["pan_numbers"].append({"text": m.group(1), "page": page_no})

            # Words
            if fields["amount_in_words"] is None:
                words_match = re.search(r"(?:amount in words|estimate in words|words|sum of rupees)[:\s]+([A-Za-z\s-]+(?:Rupees|Rupee)?[A-Za-z\s-]*(?:Only)?)", page_full_text, re.IGNORECASE)
                if words_match:
                    w_text = words_match.group(1).strip()
                    fields["amount_in_words"] = w_text
                    parsed_val = parse_inr_words_to_number(w_text)
                    if parsed_val > 0:
                        fields["parsed_words_amount"] = parsed_val

            # Line amounts with lookahead
            for i, l in enumerate(lines):
                l_text = l.get("text", "")
                amt_m = re.findall(r"(?:INR|Rs\.?|₹)?\s*([\d,]+\.\d{2})", l_text)
                lookahead_amt = None
                if not amt_m and i + 1 < len(lines):
                    la_m = re.findall(r"^([\d,]+\.\d{2})$", lines[i + 1].get("text", "").strip())
                    if la_m:
                        lookahead_amt = _clean_amount_str(la_m[0])

                if fields["subtotal"] is None and re.search(r"\bsub[\s-]?total\b", l_text, re.IGNORECASE):
                    val = _clean_amount_str(amt_m[-1]) if amt_m else lookahead_amt
                    if val is not None:
                        fields["subtotal"] = {"value": val, "page": page_no, "bbox": l["bbox"]}

                elif fields["tax_amount"] is None and re.search(r"\b(IGST|CGST|SGST|Tax)\b", l_text, re.IGNORECASE) and not re.search(r"\btax\s+invoice\b", l_text, re.IGNORECASE):
                    val = _clean_amount_str(amt_m[-1]) if amt_m else lookahead_amt
                    if val is not None:
                        fields["tax_amount"] = {"value": val, "page": page_no, "bbox": l["bbox"]}

                elif fields["total_amount"] is None and re.search(r"\b(total payable|grand total|total hospital charges|total estimate|claim amount|total:?)\b", l_text, re.IGNORECASE) and not re.search(r"\bsub[\s-]?total\b", l_text, re.IGNORECASE):
                    val = _clean_amount_str(amt_m[-1]) if amt_m else lookahead_amt
                    if val is not None and val > 100:
                        fields["total_amount"] = {"value": val, "page": page_no, "bbox": l["bbox"]}

                # Line items from OCR if empty
                if not fields["line_items"] and amt_m and not re.search(r"\b(total|subtotal|gst|tax|date|due|inr|rs)\b", l_text, re.IGNORECASE):
                    val = _clean_amount_str(amt_m[-1])
                    if val is not None and val > 0:
                        fields["line_items"].append({
                            "description": l_text,
                            "amount": val,
                            "page": page_no,
                            "bbox": l["bbox"]
                        })

        # Save to context runtime_data for rules
        ctx.runtime_data["extracted_fields"] = fields

        return DetectorOutput(
            status="ok",
            evidence=[],
            details={
                "fields": fields,
                "items_count": len(fields["line_items"]),
                "has_total": fields["total_amount"] is not None,
                "has_words": fields["amount_in_words"] is not None,
            }
        )
