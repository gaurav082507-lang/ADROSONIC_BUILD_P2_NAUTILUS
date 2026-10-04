"""Document kind and integrity detector (§11.1 Step 1).

Inspects magic bytes, checks for corruption/encryption, enforces page limit,
and classifies pages as digital, scanned, or hybrid.
"""

from typing import Dict, Any, List
from pathlib import Path
import pymupdf

from ...core.config import settings
from ...core.errors import LucenError
from ..base import Detector, DetectorOutput, AnalysisContext


class DocumentKindDetector(Detector):
    name: str = "document_kind"

    def run(self, ctx: AnalysisContext) -> DetectorOutput:
        file_path = ctx.file_path
        if not file_path.exists():
            raise LucenError(status_code=404, error_code="NOT_FOUND", message="Document file not found.")

        # Read first 32 bytes for magic byte validation
        with open(file_path, "rb") as f:
            header = f.read(32)

        is_pdf = header.startswith(b"%PDF-")
        is_jpeg = header.startswith(b"\xff\xd8\xff")
        is_png = header.startswith(b"\x89PNG\r\n\x1a\n")
        is_webp = header.startswith(b"RIFF") and header[8:12] == b"WEBP"

        if not (is_pdf or is_jpeg or is_png or is_webp):
            raise LucenError(
                status_code=415,
                error_code="UNSUPPORTED_MEDIA_TYPE",
                message="Unsupported file format. Please upload a PDF, JPEG, PNG, or WebP document."
            )

        details: Dict[str, Any] = {
            "format": "pdf" if is_pdf else "image",
            "page_count": 1,
            "analyzed_pages": 1,
            "page_limit_exceeded": False,
            "pages": []
        }
        warnings = []

        if is_pdf:
            try:
                doc = pymupdf.open(str(file_path))
            except Exception as e:
                raise LucenError(
                    status_code=422,
                    error_code="CORRUPT_FILE",
                    message=f"PDF document is corrupt and cannot be opened: {str(e)}"
                )

            if doc.is_encrypted or doc.needs_pass:
                doc.close()
                raise LucenError(
                    status_code=422,
                    error_code="CORRUPT_FILE",
                    message="Password-protected or encrypted PDFs are not supported."
                )

            total_pages = len(doc)
            max_pages = getattr(settings, "MAX_PDF_PAGES", 10)
            analyzed_pages = min(total_pages, max_pages)

            details["page_count"] = total_pages
            details["analyzed_pages"] = analyzed_pages

            if total_pages > max_pages:
                details["page_limit_exceeded"] = True
                warnings.append({
                    "code": "DOC-QUAL-01",
                    "message": f"Document has {total_pages} pages; only the first {max_pages} pages were analyzed."
                })

            for page_num in range(analyzed_pages):
                page = doc[page_num]
                text = page.get_text()
                images = page.get_images()

                has_text = len(text.strip()) > 50
                has_images = len(images) > 0

                if has_text and has_images:
                    page_kind = "hybrid"
                elif has_text:
                    page_kind = "digital"
                else:
                    page_kind = "scanned"

                details["pages"].append({
                    "page": page_num + 1,
                    "kind": page_kind,
                    "char_count": len(text.strip()),
                    "image_count": len(images)
                })

            doc.close()
        else:
            # Standalone image document
            details["pages"].append({
                "page": 1,
                "kind": "image",
                "char_count": 0,
                "image_count": 1
            })

        return DetectorOutput(
            status="ok",
            evidence=[],
            details=details,
            quality_warnings=warnings
        )
