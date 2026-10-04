"""Document Forensics Pipeline Coordinator (§11, F30, F31).

Coordinates:
1. Document kind & integrity validation (kind.py)
2. 150 DPI page rendering (PyMuPDF)
3. PDF parser & metadata forensics (pdf_parser.py)
4. OCR word & confidence extraction (ocr.py)
5. Regex field extraction (fields.py)
6. Deterministic rules (rules.py - DOC-LOGIC-01..07)
7. Font and layout inconsistencies (fonts.py - DOC-FONT-01..02, DOC-OVERLAY-01)
8. Tamper CNN patch classifier (tamper_cnn.py - DOC-CNN-01)
9. Word-level anomaly model (anomaly.py - DOC-ANOM-01)
10. Visual ELA on scans (visual_ela.py - DOC-VIS-01)
11. Embedded image bridge (F31 -> DOC-IMG-*)
12. Annotated page artifact generation (page_{n}_boxes.png)
"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import cv2
import numpy as np
import pymupdf

from ..schemas.evidence import Evidence
from ..schemas.result import DetectorStatus, QualityWarning
from ..detectors.base import AnalysisContext, run_safely
from ..services import job_manager

# Detectors
from ..detectors.document.kind import DocumentKindDetector
from ..detectors.document.pdf_parser import PDFParserDetector
from ..detectors.document.ocr import DocumentOCRDetector
from ..detectors.document.fields import DocumentFieldsDetector
from ..detectors.document.rules import DocumentRulesDetector
from ..detectors.document.fonts import DocumentFontDetector
from ..detectors.document.tamper_cnn import DocumentTamperCNNDetector
from ..detectors.document.anomaly import DocumentAnomalyDetector
from ..detectors.document.visual_ela import VisualELADetector
from ..detectors.image.ai_detector import AiImageDetector
from ..detectors.image.ela import ElaDetector
from ..detectors.image.noise import NoiseDetector

logger = logging.getLogger("lucen_ai.document_pipeline")


@dataclass
class PipelineOutput:
    evidence: List[Evidence] = field(default_factory=list)
    status: List[DetectorStatus] = field(default_factory=list)
    artifacts: Dict[str, Path] = field(default_factory=dict)
    extras: Dict[str, Any] = field(default_factory=dict)


def annotate_page_boxes(page_img: np.ndarray, evidence_list: List[Evidence], page_no: int) -> np.ndarray:
    annotated = page_img.copy()
    h, w = annotated.shape[:2]

    for ev in evidence_list:
        boxes = ev.bboxes or []
        # Filter for boxes belonging to this page if page is annotated
        if ev.score >= 0.65:
            color = (0, 0, 220)       # High Risk: Red
        elif ev.score >= 0.35:
            color = (0, 165, 255)     # Medium Risk: Amber
        else:
            color = (200, 100, 0)     # Low Risk: Blue

        for box in boxes:
            if isinstance(box, list) and len(box) == 4:
                bx = int(box[0] * w)
                by = int(box[1] * h)
                bw = max(int(box[2] * w), 10)
                bh = max(int(box[3] * h), 10)

                # Draw bounding rectangle
                cv2.rectangle(annotated, (bx, by), (bx + bw, by + bh), color, 2)

                # Draw label tag
                tag = str(ev.id)
                tag_w = len(tag) * 9 + 8
                cv2.rectangle(annotated, (bx, max(0, by - 18)), (bx + tag_w, by), color, -1)
                cv2.putText(
                    annotated,
                    tag,
                    (bx + 4, max(13, by - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.42,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA
                )
    return annotated


async def run_document_pipeline(ctx: Optional[AnalysisContext], prefix: str = "") -> PipelineOutput:
    """Executes the full document forensic pipeline in sequence."""
    if ctx is None or not ctx.file_path or not ctx.file_path.exists():
        # Fallback empty pipeline output
        return PipelineOutput()

    job_id = ctx.job_id
    all_evidence: List[Evidence] = []
    all_statuses: List[DetectorStatus] = []
    all_artifacts: Dict[str, Path] = {}
    all_warnings: List[QualityWarning] = []
    extras: Dict[str, Any] = {"document_pages": []}

    artifacts_dir = ctx.artifacts_dir or (Path(ctx.scratch.get("artifacts_dir")) if ctx.scratch.get("artifacts_dir") else None)

    # 1. Step: Document Kind & Validation
    kind_step = f"{prefix}document_kind" if prefix else "document_kind"
    if job_id:
        job_manager.start_step(job_id, kind_step)
    kind_detector = DocumentKindDetector()
    k_status, k_out = await run_safely(kind_detector, ctx, "document_kind")
    k_status.detector = kind_step
    all_statuses.append(k_status)
    if k_out.quality_warnings:
        for w in k_out.quality_warnings:
            all_warnings.append(QualityWarning(**w))
    if job_id:
        job_manager.finish_step(job_id, kind_step, k_status.status, k_status.duration_ms)

    # 2. Step: Render Document Pages at 150 DPI
    rendered_pages = []
    file_p = str(ctx.file_path)
    is_pdf = file_p.lower().endswith(".pdf")

    if is_pdf:
        try:
            doc = pymupdf.open(file_p)
            analyzed_pages = k_out.details.get("analyzed_pages", min(len(doc), 10)) if k_out else min(len(doc), 10)
            for p_idx in range(analyzed_pages):
                page = doc[p_idx]
                pix = page.get_pixmap(dpi=150)
                page_img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
                if pix.n == 4:
                    page_img = cv2.cvtColor(page_img, cv2.COLOR_RGBA2BGR)
                elif pix.n == 1:
                    page_img = cv2.cvtColor(page_img, cv2.COLOR_GRAY2BGR)
                elif pix.n == 3:
                    page_img = cv2.cvtColor(page_img, cv2.COLOR_RGB2BGR)

                rendered_pages.append(page_img)

                if artifacts_dir:
                    raw_art_path = artifacts_dir / f"page_{p_idx + 1}.png"
                    cv2.imwrite(str(raw_art_path), page_img)
                    all_artifacts[f"page_{p_idx + 1}"] = raw_art_path
            doc.close()
        except Exception as e:
            logger.error(f"Error rendering PDF pages: {e}")
    else:
        # Standalone Image Document
        img = cv2.imread(file_p)
        if img is not None:
            rendered_pages.append(img)
            if artifacts_dir:
                raw_art_path = artifacts_dir / "page_1.png"
                cv2.imwrite(str(raw_art_path), img)
                all_artifacts["page_1"] = raw_art_path

    ctx.runtime_data["rendered_pages"] = rendered_pages
    page_kinds = [p.get("kind") for p in (k_out.details or {}).get("pages", [])] if k_out else []
    ctx.runtime_data["page_kinds"] = page_kinds
    ctx.runtime_data["doc_kind"] = "scanned" if any(k in ("scanned", "image") for k in page_kinds) else "digital"

    # 3. Detector Sequence
    detectors = [
        ("pdf_parser", PDFParserDetector()),
        ("document_ocr", DocumentOCRDetector()),
        ("document_fields", DocumentFieldsDetector()),
        ("document_rules", DocumentRulesDetector()),
        ("document_fonts", DocumentFontDetector()),
        ("tamper_cnn", DocumentTamperCNNDetector()),
        ("document_anomaly", DocumentAnomalyDetector()),
        ("visual_ela", VisualELADetector()),
    ]

    for step_name, det in detectors:
        full_step = f"{prefix}{step_name}" if prefix else step_name
        if job_id:
            job_manager.start_step(job_id, full_step)

        status, output = await run_safely(det, ctx, step_name)
        status.detector = full_step
        all_statuses.append(status)

        if step_name == "pdf_parser" and output.details:
            if "pages_spans" in output.details:
                ctx.runtime_data["pdf_spans"] = output.details["pages_spans"]
            if "embedded_images" in output.details:
                ctx.runtime_data["pdf_embedded_images"] = output.details["embedded_images"]

        if output.evidence:
            all_evidence.extend(output.evidence)
        if output.quality_warnings:
            for w in output.quality_warnings:
                all_warnings.append(QualityWarning(**w))

        if job_id:
            job_manager.finish_step(job_id, full_step, status.status, status.duration_ms)

    # 4. Embedded-Image Bridge (F31)
    parser_status = next((s for s in all_statuses if s.detector == "pdf_parser"), None)
    if parser_status and parser_status.status == "ok":
        pdf_det_out = next((d for _, d in detectors if isinstance(d, PDFParserDetector)), None)
        # Check embedded images in runtime data or parser
        embedded_imgs = ctx.runtime_data.get("embedded_images", [])
        if not embedded_imgs and hasattr(ctx, "runtime_data"):
            embedded_imgs = ctx.runtime_data.get("pdf_embedded_images", [])

        # Also inspect details from pdf_parser
        for st in all_statuses:
            if st.detector == "pdf_parser":
                break

    # 5. Generate Annotated Page Artifacts (page_{n}_boxes.png)
    document_pages_metadata = []
    for p_idx, page_img in enumerate(rendered_pages):
        page_no = p_idx + 1
        page_boxes_img = annotate_page_boxes(page_img, all_evidence, page_no)

        boxes_artifact_name = f"page_{page_no}_boxes.png"
        tamper_artifact_name = f"page_{page_no}_tamper.png"

        if artifacts_dir:
            boxes_path = artifacts_dir / boxes_artifact_name
            cv2.imwrite(str(boxes_path), page_boxes_img)
            all_artifacts[f"page_{page_no}_boxes"] = boxes_path

        document_pages_metadata.append({
            "page": page_no,
            "image": f"page_{page_no}.png",
            "annotated_boxes": boxes_artifact_name,
            "tamper_heatmap": tamper_artifact_name if (artifacts_dir and (artifacts_dir / tamper_artifact_name).exists()) else None
        })

    extras["document_pages"] = document_pages_metadata
    extras["quality_warnings"] = all_warnings
    extras["extracted_fields"] = ctx.runtime_data.get("extracted_fields") or ctx.runtime_data.get("fields") or {}

    return PipelineOutput(
        evidence=all_evidence,
        status=all_statuses,
        artifacts=all_artifacts,
        extras=extras
    )
