"""Visual ELA on scans (§11.1 Step 11).

For scanned or image documents, detects large compression anomaly regions
that overlap OCR text boxes, providing a non-learned forensic second opinion.
Emits:
- DOC-VIS-01: Compression anomaly over text region (scans) (weight 0.25).
"""

from typing import Dict, Any, List
import cv2
import numpy as np

from ...schemas.evidence import Evidence
from ..base import Detector, DetectorOutput, AnalysisContext
from .tamper_cnn import compute_page_ela


class VisualELADetector(Detector):
    name: str = "visual_ela"

    def run(self, ctx: AnalysisContext) -> DetectorOutput:
        doc_kind = ctx.runtime_data.get("doc_kind", "digital")
        file_p = str(ctx.file_path or "").lower()
        is_image_file = file_p.endswith((".png", ".jpg", ".jpeg", ".webp"))
        if doc_kind != "scanned" and not is_image_file:
            return DetectorOutput(
                status="skipped",
                evidence=[],
                details={"message": "DOC-VIS-01 skipped: document is digital PDF (visual ELA only runs on scans and photo documents)."}
            )

        rendered_pages = ctx.runtime_data.get("rendered_pages", [])
        ocr_pages = ctx.runtime_data.get("ocr_pages", [])

        if not rendered_pages:
            file_p = str(ctx.file_path)
            if file_p.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                img = cv2.imread(file_p)
                if img is not None:
                    rendered_pages = [img]

        if not rendered_pages:
            return DetectorOutput(
                status="skipped",
                evidence=[],
                details={"message": "No rendered document pages available."}
            )

        evidence: List[Evidence] = []
        details: Dict[str, Any] = {"pages": []}

        for p_idx, img in enumerate(rendered_pages):
            page_no = p_idx + 1
            h, w = img.shape[:2]
            ela = compute_page_ela(img)
            gray_ela = cv2.cvtColor(ela, cv2.COLOR_BGR2GRAY)

            # Robust threshold: median + 3.5 * MAD
            med = float(np.median(gray_ela))
            mad = float(np.median(np.abs(gray_ela - med)))
            thresh = med + 3.5 * max(mad, 1.0)

            bin_anom = (gray_ela > thresh).astype(np.uint8) * 255
            # Dilate to connect nearby noisy pixels
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
            closed = cv2.morphologyEx(bin_anom, cv2.MORPH_CLOSE, kernel)

            # OCR word boxes for this page
            page_words = ocr_pages[p_idx].get("words", []) if p_idx < len(ocr_pages) else []

            # Check overlap between large ELA anomaly blobs and text boxes
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(closed)
            overlapping_boxes = []

            for lbl in range(1, num_labels):
                area = int(stats[lbl, cv2.CC_STAT_AREA])
                if area >= 600:
                    bx = int(stats[lbl, cv2.CC_STAT_LEFT])
                    by = int(stats[lbl, cv2.CC_STAT_TOP])
                    bw = int(stats[lbl, cv2.CC_STAT_WIDTH])
                    bh = int(stats[lbl, cv2.CC_STAT_HEIGHT])
                    norm_box = [round(bx / w, 4), round(by / h, 4), round(bw / w, 4), round(bh / h, 4)]

                    # Check if overlaps with any text box
                    has_text_overlap = False
                    for wb in page_words:
                        w_norm = wb["normalized_bbox"]
                        ox = max(0, min(norm_box[0] + norm_box[2], w_norm[0] + w_norm[2]) - max(norm_box[0], w_norm[0]))
                        oy = max(0, min(norm_box[1] + norm_box[3], w_norm[1] + w_norm[3]) - max(norm_box[1], w_norm[1]))
                        if ox > 0 and oy > 0:
                            has_text_overlap = True
                            break

                    if has_text_overlap:
                        overlapping_boxes.append(norm_box)

            if overlapping_boxes:
                evidence.append(Evidence(
                    id="DOC-VIS-01",
                    pipeline="document",
                    source="forensics",
                    kind="risk",
                    score=0.70,
                    weight=0.25,
                    title="Visual Compression Anomaly",
                    reason=f"Significant ELA compression anomaly overlapping text regions detected on page {page_no}.",
                    bboxes=overlapping_boxes[:3],
                    details={"page": page_no, "anomalous_regions": len(overlapping_boxes)}
                ))

            details["pages"].append({
                "page": page_no,
                "anomalous_regions": len(overlapping_boxes)
            })

        return DetectorOutput(
            status="ok",
            evidence=evidence,
            details=details
        )
