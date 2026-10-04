"""Font consistency, layout geometry, and text overlay detector (§11.1 Step 4).

Checks:
- DOC-FONT-01: Font differs within a field group / numeric column (weight 0.40).
- DOC-FONT-02: Size, baseline, or stroke deviation within a line (weight 0.30).
- DOC-OVERLAY-01: Visible text layer (OCR) differs from hidden digital text layer (weight 0.70).
"""

from typing import Dict, Any, List
import re
import numpy as np

from ...schemas.evidence import Evidence
from ..base import Detector, DetectorOutput, AnalysisContext


def _normalize_font_family(name: str) -> str:
    clean = re.sub(r"[-_, ]*(bold|italic|oblique|regular|light|medium|black|semibold|heavy)", "", name, flags=re.IGNORECASE)
    clean = re.sub(r"^[A-Z]{6}\+", "", clean)
    return clean.strip().lower()


class DocumentFontDetector(Detector):
    name: str = "document_fonts"

    def run(self, ctx: AnalysisContext) -> DetectorOutput:
        ocr_pages = ctx.runtime_data.get("ocr_pages", [])
        pdf_spans_pages = ctx.runtime_data.get("pdf_spans", [])

        evidence: List[Evidence] = []
        details: Dict[str, Any] = {"checks": []}

        # 1. DOC-FONT-01: Font Inconsistency across Spans
        for page_data in pdf_spans_pages:
            page_no = page_data.get("page", 1)
            spans = page_data.get("spans", [])

            # Group monetary/numeric spans
            num_spans = [s for s in spans if re.search(r"\b[\d,]+\.\d{2}\b", s.get("text", ""))]
            if len(num_spans) >= 2:
                # Find dominant base font family in numeric spans
                families = [_normalize_font_family(s.get("font", "default")) for s in num_spans]
                from collections import Counter
                counts = Counter(families)
                dominant_family, _ = counts.most_common(1)[0]
                dominant_font = next((s.get("font", "default") for s in num_spans if _normalize_font_family(s.get("font", "default")) == dominant_family), "default")

                for s in num_spans:
                    s_font = s.get("font", "default")
                    s_family = _normalize_font_family(s_font)
                    if s_family != dominant_family:
                        evidence.append(Evidence(
                            id="DOC-FONT-01",
                            pipeline="document",
                            source="rules",
                            kind="risk",
                            score=0.75,
                            weight=0.40,
                            title="Font Mismatch in Field Group",
                            reason=f"The value '{s['text']}' uses font '{s_font}', differing from the column's dominant font '{dominant_font}'.",
                            bboxes=[s["bbox"]],
                            details={
                                "text": s["text"],
                                "font_a": s_font,
                                "font_b": dominant_font,
                                "page": page_no
                            }
                        ))
                        break  # Report top mismatch

        # 2. DOC-FONT-02: Baseline & Character Height Deviations
        font_outliers = []
        for page_data in ocr_pages:
            page_no = page_data.get("page", 1)
            words = page_data.get("words", [])

            # Group words by approximate Y line
            lines_dict = {}
            for w in words:
                y = w["bbox"][1]
                line_key = y // 20
                lines_dict.setdefault(line_key, []).append(w)

            for line_key, line_words in lines_dict.items():
                if len(line_words) >= 5:
                    heights = [w["char_height"] for w in line_words]
                    mean_h = np.mean(heights)
                    std_h = np.std(heights)

                    if std_h > 1.5:
                        for w in line_words:
                            # Flag if height is > 3.2 std from line mean (tightened threshold)
                            z = abs(w["char_height"] - mean_h) / (std_h + 1e-6)
                            if z > 3.2 and re.search(r"\d", w["text"]):
                                font_outliers.append((w, z, page_no))

        # Require >= 3 outlier words before emitting DOC-FONT-02 to prevent clean false positives
        if len(font_outliers) >= 3:
            w_top, z_top, p_top = max(font_outliers, key=lambda x: x[1])
            evidence.append(Evidence(
                id="DOC-FONT-02",
                pipeline="document",
                source="rules",
                kind="risk",
                score=0.65,
                weight=0.30,
                title="Size/Baseline Inconsistency",
                reason=f"Character height of '{w_top['text']}' deviates {z_top:.1f} std deviations from the surrounding line median ({len(font_outliers)} outlier words found).",
                bboxes=[o[0]["normalized_bbox"] for o in font_outliers[:3]],
                details={"word": w_top["text"], "z_score": round(float(z_top), 2), "page": p_top, "outliers_count": len(font_outliers)}
            ))

        # 3. DOC-OVERLAY-01: Visible (OCR) vs Digital Text Layer Mismatch
        if pdf_spans_pages and ocr_pages:
            for p_idx in range(min(len(pdf_spans_pages), len(ocr_pages))):
                pdf_spans = pdf_spans_pages[p_idx].get("spans", [])
                ocr_words = ocr_pages[p_idx].get("words", [])

                # Compare amounts found in OCR vs PDF spans
                for ow in ocr_words:
                    otext = ow["text"]
                    if re.match(r"^[\d,]+\.\d{2}$", otext):
                        # Find overlapping PDF span
                        ob = ow["normalized_bbox"]
                        for ps in pdf_spans:
                            pb = ps["bbox"]
                            # Check bounding box overlap
                            overlap_x = max(0, min(ob[0] + ob[2], pb[0] + pb[2]) - max(ob[0], pb[0]))
                            overlap_y = max(0, min(ob[1] + ob[3], pb[1] + pb[3]) - max(ob[1], pb[1]))
                            if overlap_x > 0.02 and overlap_y > 0.01:
                                ptext = re.sub(r"[^\d.]", "", ps["text"].replace(",", ""))
                                oclean = re.sub(r"[^\d.]", "", otext.replace(",", ""))
                                if ptext and oclean and ptext != oclean:
                                    evidence.append(Evidence(
                                        id="DOC-OVERLAY-01",
                                        pipeline="document",
                                        source="forensics",
                                        kind="risk",
                                        score=0.90,
                                        weight=0.70,
                                        title="Text Overlay Mismatch",
                                        reason=f"Visible rendered text '{otext}' contradicts the underlying digital text layer ('{ps['text']}').",
                                        bboxes=[ob],
                                        details={
                                            "visible_text": otext,
                                            "hidden_text": ps["text"],
                                            "page": p_idx + 1
                                        }
                                    ))
                                    break

        return DetectorOutput(
            status="ok",
            evidence=evidence,
            details={"findings_count": len(evidence)}
        )
