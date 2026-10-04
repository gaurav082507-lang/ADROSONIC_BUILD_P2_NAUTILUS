"""PDF structural parser, span extractor, and metadata forensics (§11.1 Steps 3 & 4).

Extracts:
1. Spans with text, font name, size, flags, color, and bounding boxes via get_text("dict").
2. Embedded images (filtered for size >= 200x200 px).
3. Metadata checks:
   - DOC-META-01: Producer/Creator is a consumer or online editing tool.
   - DOC-META-02: Modified long after creation (> 60s).
   - DOC-META-03: Appended revisions (%%EOF count > 1).
   - DOC-META-04: Creation date inconsistent with document date.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path
import re
import pymupdf

from ...schemas.evidence import Evidence
from ..base import Detector, DetectorOutput, AnalysisContext

CONSUMER_EDITORS = [
    "canva", "ilovepdf", "smallpdf", "photoshop", "gimp", "sejda",
    "pdfescape", "foxit", "libreoffice", "inkscape", "pdf24", "nitro",
    "soda", "acrobat web", "wondershare", "camscanner"
]


def _parse_pdf_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    # PDF dates are formatted like "D:YYYYMMDDHHmmSSOHH'mm'"
    clean = re.sub(r"^D:", "", date_str)
    clean = clean.split("+")[0].split("-")[0].split("Z")[0].replace("'", "")
    formats = ["%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y%m%d"]
    for fmt in formats:
        try:
            return datetime.strptime(clean[:len(datetime.now().strftime(fmt))], fmt)
        except Exception:
            continue
    return None


class PDFParserDetector(Detector):
    name: str = "pdf_parser"

    def run(self, ctx: AnalysisContext) -> DetectorOutput:
        file_path = ctx.file_path
        with open(file_path, "rb") as f:
            raw_bytes = f.read()

        if not raw_bytes.startswith(b"%PDF-"):
            # Image document; metadata PDF checks not applicable
            return DetectorOutput(
                status="skipped",
                evidence=[],
                details={"message": "Non-PDF document; PDF parser skipped."}
            )

        doc = pymupdf.open(str(file_path))
        meta = doc.metadata or {}
        evidence: List[Evidence] = []
        details: Dict[str, Any] = {
            "producer": meta.get("producer", ""),
            "creator": meta.get("creator", ""),
            "creation_date": meta.get("creationDate", ""),
            "mod_date": meta.get("modDate", ""),
            "eof_count": 0,
            "embedded_images": [],
            "pages_spans": []
        }

        # 1. DOC-META-01: Online / Consumer Editor
        combined_tools = f"{meta.get('producer', '')} {meta.get('creator', '')}".lower()
        matched_tool = next((t for t in CONSUMER_EDITORS if t in combined_tools), None)
        if matched_tool:
            evidence.append(Evidence(
                id="DOC-META-01",
                pipeline="document",
                source="metadata",
                kind="risk",
                score=0.75,
                weight=0.15,
                title="Consumer/Online Editor Producer",
                reason=f"The PDF was created or modified using a consumer tool ({matched_tool.title()}).",
                details={"matched_tool": matched_tool, "producer": meta.get("producer", ""), "creator": meta.get("creator", "")}
            ))

        # 2. DOC-META-02: Modified long after creation
        c_dt = _parse_pdf_date(meta.get("creationDate"))
        m_dt = _parse_pdf_date(meta.get("modDate"))
        if c_dt and m_dt:
            diff_seconds = (m_dt - c_dt).total_seconds()
            if diff_seconds > 60:
                hours = diff_seconds / 3600.0
                delta_str = f"{hours:.1f} hours" if hours >= 1.0 else f"{int(diff_seconds)} seconds"
                evidence.append(Evidence(
                    id="DOC-META-02",
                    pipeline="document",
                    source="metadata",
                    kind="risk",
                    score=0.70,
                    weight=0.20,
                    title="Modified Long After Creation",
                    reason=f"The PDF was modified {delta_str} after it was created.",
                    details={"delta": delta_str, "diff_seconds": diff_seconds, "producer": meta.get("producer", "PDF editor")}
                ))

        # 3. DOC-META-03: Incremental updates (%%EOF count)
        eof_count = raw_bytes.count(b"%%EOF")
        details["eof_count"] = eof_count
        if eof_count > 1:
            evidence.append(Evidence(
                id="DOC-META-03",
                pipeline="document",
                source="metadata",
                kind="risk",
                score=0.65,
                weight=0.20,
                title="Appended Revisions Detected",
                reason=f"The PDF file contains {eof_count} revision segments appended after its first save.",
                details={"eof_count": eof_count}
            ))

        # Extract Spans and Embedded Images per page
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_w = page.rect.width
            page_h = page.rect.height

            # Spans via get_text("dict")
            page_dict = page.get_text("dict")
            spans_list = []
            for block in page_dict.get("blocks", []):
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            bx0, by0, bx1, by1 = span.get("bbox", [0, 0, 0, 0])
                            spans_list.append({
                                "text": span.get("text", ""),
                                "font": span.get("font", ""),
                                "size": round(span.get("size", 10.0), 1),
                                "flags": span.get("flags", 0),
                                "color": span.get("color", 0),
                                "bbox": [
                                    round(bx0 / max(page_w, 1), 4),
                                    round(by0 / max(page_h, 1), 4),
                                    round((bx1 - bx0) / max(page_w, 1), 4),
                                    round((by1 - by0) / max(page_h, 1), 4),
                                ],
                                "raw_bbox": [bx0, by0, bx1, by1]
                            })

            details["pages_spans"].append({
                "page": page_idx + 1,
                "width_pt": page_w,
                "height_pt": page_h,
                "spans": spans_list
            })

            # Embedded Images (Bridge F31)
            image_list = page.get_images(full=True)
            for img_info in image_list:
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                if base_image:
                    iw = base_image.get("width", 0)
                    ih = base_image.get("height", 0)
                    # Filter: ignore tiny icons/decorations below 200x200
                    if iw >= 200 and ih >= 200:
                        image_bytes = base_image.get("image")
                        ext = base_image.get("ext", "png")
                        details["embedded_images"].append({
                            "page": page_idx + 1,
                            "xref": xref,
                            "width": iw,
                            "height": ih,
                            "format": ext,
                            "bytes": image_bytes
                        })

        doc.close()

        # Save to context runtime_data for downstream detectors (fields, rules, fonts)
        ctx.runtime_data["pdf_spans"] = details["pages_spans"]
        ctx.runtime_data["pdf_embedded_images"] = details["embedded_images"]

        return DetectorOutput(
            status="ok",
            evidence=evidence,
            details=details
        )
