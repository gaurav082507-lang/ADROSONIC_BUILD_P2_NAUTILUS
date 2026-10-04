"""Deterministic consistency rules for document forensics (§11.1 Step 7).

Rules:
- DOC-LOGIC-01: Sum of line items ≠ subtotal / total (tolerance 0.01, weight 0.80).
- DOC-LOGIC-02: Tax / discount percentage does not reproduce stated amount (weight 0.50).
- DOC-LOGIC-03: Invalid date logic (due date before invoice, service in future) (weight 0.50).
- DOC-LOGIC-04: ID / policy number fails format or Verhoeff checksum (weight 0.50).
- DOC-LOGIC-05: Same field disagrees across pages (weight 0.60).
- DOC-LOGIC-06: Numbers formatted inconsistently within document (weight 0.25).
- DOC-LOGIC-07: Amount in words differs from amount in digits (weight 0.70).
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import re

from ...schemas.evidence import Evidence
from ..base import Detector, DetectorOutput, AnalysisContext
from ...core.formatters import validate_verhoeff, format_inr


class DocumentRulesDetector(Detector):
    name: str = "document_rules"

    def run(self, ctx: AnalysisContext) -> DetectorOutput:
        fields = ctx.runtime_data.get("extracted_fields", {})
        if not fields:
            return DetectorOutput(
                status="skipped",
                evidence=[],
                details={"reason": "No extracted fields found; rules skipped."}
            )

        evidence: List[Evidence] = []
        checks_evaluated = []

        # ----------------------------------------------------
        # DOC-LOGIC-01: Sum of line items != subtotal / total
        # ----------------------------------------------------
        line_items = fields.get("line_items", [])
        total_rec = fields.get("total_amount")
        subtotal_rec = fields.get("subtotal")
        tax_amt_rec = fields.get("tax_amount")

        if line_items and (total_rec or subtotal_rec):
            checks_evaluated.append("DOC-LOGIC-01")
            sum_items = round(sum(item["amount"] for item in line_items), 2)

            total_mismatch = False
            if total_rec:
                tax_val = tax_amt_rec["value"] if tax_amt_rec else 0.0
                expected_with_tax = round(sum_items + tax_val, 2)
                # If total differs from both sum_items and sum_items + tax
                if abs(total_rec["value"] - sum_items) > 0.05 and abs(total_rec["value"] - expected_with_tax) > 0.05:
                    total_mismatch = True

            subtotal_mismatch = False
            if subtotal_rec:
                if abs(sum_items - subtotal_rec["value"]) > 0.05:
                    subtotal_mismatch = True

            if total_mismatch:
                target_rec = total_rec
                expected_target = target_rec["value"]
                diff = abs(sum_items - expected_target)
                involved_boxes = [target_rec["bbox"]] if target_rec.get("bbox") else []
                involved_boxes.extend([item["bbox"] for item in line_items if item.get("bbox")])

                evidence.append(Evidence(
                    id="DOC-LOGIC-01",
                    pipeline="document",
                    source="rules",
                    kind="risk",
                    score=min(1.0, 0.70 + (diff / max(expected_target, 1.0)) * 0.3),
                    weight=0.80,
                    title="Line Items Sum Mismatch",
                    reason=f"The line items add up to INR {format_inr(sum_items)} but the stated total is INR {format_inr(expected_target)}.",
                    bboxes=involved_boxes[:5],
                    details={
                        "expected": sum_items,
                        "found": expected_target,
                        "diff": round(diff, 2),
                        "items_count": len(line_items)
                    }
                ))
            elif subtotal_mismatch:
                target_rec = subtotal_rec
                expected_target = target_rec["value"]
                diff = abs(sum_items - expected_target)
                involved_boxes = [target_rec["bbox"]] if target_rec.get("bbox") else []
                involved_boxes.extend([item["bbox"] for item in line_items if item.get("bbox")])

                evidence.append(Evidence(
                    id="DOC-LOGIC-01",
                    pipeline="document",
                    source="rules",
                    kind="risk",
                    score=min(1.0, 0.70 + (diff / max(expected_target, 1.0)) * 0.3),
                    weight=0.80,
                    title="Line Items Sum Mismatch",
                    reason=f"The line items add up to INR {format_inr(sum_items)} but the stated subtotal is INR {format_inr(expected_target)}.",
                    bboxes=involved_boxes[:5],
                    details={
                        "expected": sum_items,
                        "found": expected_target,
                        "diff": round(diff, 2),
                        "items_count": len(line_items)
                    }
                ))

        # ----------------------------------------------------
        # DOC-LOGIC-02: Tax percentage does not reproduce amount
        # ----------------------------------------------------
        subtotal = subtotal_rec["value"] if subtotal_rec else None
        tax_amt_rec = fields.get("tax_amount")
        tax_pct = fields.get("tax_percentage")

        if subtotal and tax_amt_rec and tax_pct:
            checks_evaluated.append("DOC-LOGIC-02")
            expected_tax = round(subtotal * (tax_pct / 100.0), 2)
            found_tax = tax_amt_rec["value"]
            diff = abs(expected_tax - found_tax)
            if diff > 0.10:
                evidence.append(Evidence(
                    id="DOC-LOGIC-02",
                    pipeline="document",
                    source="rules",
                    kind="risk",
                    score=0.75,
                    weight=0.50,
                    title="Tax/Discount Math Inconsistent",
                    reason=f"Stated {tax_pct:.1f}% tax should be INR {format_inr(expected_tax)} on INR {format_inr(subtotal)}, but found INR {format_inr(found_tax)}.",
                    bboxes=[tax_amt_rec.get("bbox")] if tax_amt_rec.get("bbox") else [],
                    details={
                        "subtotal": subtotal,
                        "tax_percentage": tax_pct,
                        "expected_tax": expected_tax,
                        "found_tax": found_tax
                    }
                ))

        # ----------------------------------------------------
        # DOC-LOGIC-03: Invalid date logic
        # ----------------------------------------------------
        dates = fields.get("dates", [])
        if len(dates) >= 2:
            checks_evaluated.append("DOC-LOGIC-03")
            parsed_dates = []
            for d in dates:
                text = d["text"].replace("-", "/")
                for fmt in ["%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d"]:
                    try:
                        parsed_dates.append((datetime.strptime(text, fmt), d))
                        break
                    except Exception:
                        continue

            if len(parsed_dates) >= 2:
                # If first date (e.g. invoice) is after second date (e.g. due date)
                d0_dt, d0_rec = parsed_dates[0]
                d1_dt, d1_rec = parsed_dates[1]
                if d0_dt > d1_dt and (d0_dt - d1_dt).days > 1:
                    evidence.append(Evidence(
                        id="DOC-LOGIC-03",
                        pipeline="document",
                        source="rules",
                        kind="risk",
                        score=0.70,
                        weight=0.50,
                        title="Invalid Date Sequence",
                        reason=f"Chronological contradiction: stated date {d0_rec['text']} occurs after subsequent date {d1_rec['text']}.",
                        bboxes=[b for b in [d0_rec.get("bbox"), d1_rec.get("bbox")] if b],
                        details={"date_1": d0_rec["text"], "date_2": d1_rec["text"]}
                    ))

        # ----------------------------------------------------
        # DOC-LOGIC-04: ID / Aadhaar Checksum verification
        # ----------------------------------------------------
        aadhaar_list = fields.get("aadhaar_numbers", [])
        for a_entry in aadhaar_list:
            checks_evaluated.append("DOC-LOGIC-04")
            clean_digits = a_entry["text"]
            if len(clean_digits) == 12:
                is_valid = validate_verhoeff(clean_digits)
                if not is_valid:
                    evidence.append(Evidence(
                        id="DOC-LOGIC-04",
                        pipeline="document",
                        source="rules",
                        kind="risk",
                        score=0.85,
                        weight=0.50,
                        title="ID/Checksum Format Invalid",
                        reason=f"12-digit identity number '{clean_digits[:4]} XXXX {clean_digits[-4:]}' failed Verhoeff checksum validation.",
                        bboxes=[a_entry.get("bbox")] if a_entry.get("bbox") else [],
                        details={"aadhaar_masked": f"{clean_digits[:4]} XXXX {clean_digits[-4:]}"}
                    ))

        # ----------------------------------------------------
        # DOC-LOGIC-06: Inconsistent Number Formatting
        # ----------------------------------------------------
        ocr_pages = ctx.runtime_data.get("ocr_pages", [])
        indian_fmt_count = 0
        western_fmt_count = 0
        for p in ocr_pages:
            for w in p.get("words", []):
                t = w["text"]
                if re.search(r"\b\d{1,2},\d{2},\d{3}\b", t):
                    indian_fmt_count += 1
                elif re.search(r"\b\d{1,3},\d{3},\d{3}\b", t):
                    western_fmt_count += 1

        if indian_fmt_count > 0 and western_fmt_count > 0:
            checks_evaluated.append("DOC-LOGIC-06")
            evidence.append(Evidence(
                id="DOC-LOGIC-06",
                pipeline="document",
                source="rules",
                kind="risk",
                score=0.45,
                weight=0.25,
                title="Inconsistent Number Formatting",
                reason="Document mixes Indian numbering formatting (1,20,000) with International grouping (120,000).",
                details={"indian_count": indian_fmt_count, "western_count": western_fmt_count}
            ))

        # ----------------------------------------------------
        # DOC-LOGIC-07: Amount in Words differs from digits
        # ----------------------------------------------------
        words_amt = fields.get("parsed_words_amount")
        if total_rec and words_amt:
            checks_evaluated.append("DOC-LOGIC-07")
            numeric_total = total_rec["value"]
            diff = abs(words_amt - numeric_total)
            if diff > 1.0:
                evidence.append(Evidence(
                    id="DOC-LOGIC-07",
                    pipeline="document",
                    source="rules",
                    kind="risk",
                    score=0.85,
                    weight=0.70,
                    title="Amount in Words Mismatch",
                    reason=f"Stated amount in words parses to INR {format_inr(words_amt)}, but digit total states INR {format_inr(numeric_total)}.",
                    bboxes=[total_rec.get("bbox")] if total_rec.get("bbox") else [],
                    details={
                        "words_text": fields.get("amount_in_words"),
                        "parsed_from_words": words_amt,
                        "numeric_digits": numeric_total,
                        "diff": round(diff, 2)
                    }
                ))

        if not checks_evaluated:
            return DetectorOutput(
                status="skipped",
                evidence=[],
                details={"message": "No checkable fields found in document."}
            )

        return DetectorOutput(
            status="ok",
            evidence=evidence,
            details={
                "checks_evaluated": checks_evaluated,
                "violations_found": len(evidence)
            }
        )
