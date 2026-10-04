"""Document OCR detector using RapidOCR (§11.1 Step 5).

Extracts word-level bounding boxes, text, confidence, estimated character height,
and baseline angle.
Detects:
- DOC-OCR-01: Low-confidence words inside numeric fields (weight 0.15).
- DOC-QUAL-01: Quality warning if mean confidence < 0.60.
"""

from typing import Dict, Any, List, Tuple
from pathlib import Path
import math
import re
import numpy as np
import cv2
from rapidocr_onnxruntime import RapidOCR

from ...schemas.evidence import Evidence
from ..base import Detector, DetectorOutput, AnalysisContext


class DocumentOCRDetector(Detector):
    name: str = "document_ocr"

    def __init__(self):
        super().__init__()
        self._engine = RapidOCR()

    def run(self, ctx: AnalysisContext) -> DetectorOutput:
        # ctx.runtime_data can store rendered_pages (from pre-step or pipeline)
        # or we render the first page from file_path
        rendered_pages = ctx.runtime_data.get("rendered_pages", [])
        if not rendered_pages:
            # If not rendered yet, read image or first page
            file_p = str(ctx.file_path)
            if file_p.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                img = cv2.imread(file_p)
                if img is not None:
                    rendered_pages = [img]

        if not rendered_pages:
            return DetectorOutput(
                status="skipped",
                evidence=[],
                details={"message": "No rendered document pages available for OCR."}
            )

        evidence: List[Evidence] = []
        quality_warnings: List[Dict[str, Any]] = []
        all_pages_ocr = []

        total_conf = 0.0
        total_words = 0

        for page_idx, page_img in enumerate(rendered_pages):
            h, w = page_img.shape[:2]
            results, _ = self._engine(page_img)
            page_words = []
            page_lines = []

            if results:
                for line_box, line_text, conf in results:
                    conf = float(conf)
                    # line_box: [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
                    xs = [pt[0] for pt in line_box]
                    ys = [pt[1] for pt in line_box]
                    lx0, lx1 = min(xs), max(xs)
                    ly0, ly1 = min(ys), max(ys)
                    lw = max(lx1 - lx0, 1.0)
                    lh = max(ly1 - ly0, 1.0)

                    # Compute baseline tilt angle
                    dx = line_box[1][0] - line_box[0][0]
                    dy = line_box[1][1] - line_box[0][1]
                    angle = math.degrees(math.atan2(dy, dx)) if dx != 0 else 0.0

                    page_lines.append({
                        "text": line_text,
                        "conf": round(conf, 3),
                        "bbox": [round(lx0 / w, 4), round(ly0 / h, 4), round(lw / w, 4), round(lh / h, 4)],
                        "pixel_bbox": [int(lx0), int(ly0), int(lw), int(lh)],
                        "angle": round(angle, 2)
                    })

                    # Split line into words
                    tokens = line_text.split()
                    if not tokens:
                        continue

                    # Allocate character-width slices across line width
                    total_chars = max(sum(len(t) for t in tokens) + len(tokens) - 1, 1)
                    char_w = lw / total_chars
                    cur_x = lx0

                    for token in tokens:
                        token_w = max(len(token) * char_w, 5.0)
                        word_record = {
                            "text": token,
                            "conf": round(conf, 3),
                            "bbox": [int(cur_x), int(ly0), int(token_w), int(lh)],
                            "normalized_bbox": [
                                round(cur_x / w, 4),
                                round(ly0 / h, 4),
                                round(token_w / w, 4),
                                round(lh / h, 4)
                            ],
                            "char_height": round(lh, 1),
                            "baseline_angle": round(angle, 2)
                        }
                        page_words.append(word_record)
                        total_conf += conf
                        total_words += 1

                        # DOC-OCR-01: Low confidence word inside numeric field
                        is_numeric = bool(re.search(r"\d", token))
                        if is_numeric and conf < 0.65:
                            evidence.append(Evidence(
                                id="DOC-OCR-01",
                                pipeline="document",
                                source="ocr",
                                kind="risk",
                                score=round(1.0 - conf, 3),
                                weight=0.15,
                                title="Low OCR Confidence in Numbers",
                                reason=f"Low OCR confidence ({conf:.0%}) detected on numeric text '{token}'.",
                                bboxes=[word_record["normalized_bbox"]],
                                details={"token": token, "conf": round(conf, 3), "page": page_idx + 1}
                            ))

                        cur_x += token_w + char_w  # advance with space

            all_pages_ocr.append({
                "page": page_idx + 1,
                "lines": page_lines,
                "words": page_words
            })

        # Check overall scan quality
        mean_conf = total_conf / max(total_words, 1)
        if total_words > 0 and mean_conf < 0.60:
            quality_warnings.append({
                "code": "DOC-QUAL-01",
                "message": f"Low document scan quality; OCR mean confidence is {mean_conf:.1%}."
            })

        # Store in runtime data for downstream detectors (fields, rules, anomaly)
        ctx.runtime_data["ocr_pages"] = all_pages_ocr

        return DetectorOutput(
            status="ok",
            evidence=evidence,
            details={
                "total_words_extracted": total_words,
                "mean_confidence": round(mean_conf, 3),
                "pages": all_pages_ocr
            },
            quality_warnings=quality_warnings
        )
