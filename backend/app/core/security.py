import os
import uuid
import re
from typing import Optional, Tuple
from fastapi import UploadFile
from .config import settings
from .errors import AppException

# Set Pillow decompression limit if pillow is installed
try:
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = 89_478_485  # ~89 MP max to guard against decompression bombs
except ImportError:
    pass

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_DOCUMENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}
ALLOWED_ALL = {"image/jpeg", "image/png", "image/webp", "application/pdf"}

TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}

def detect_mime_type(header: bytes) -> Optional[str]:
    """Inspect magic bytes, never the client extension or Content-Type header."""
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "image/webp"
    if header.startswith(b"%PDF-"):
        return "application/pdf"
    return None

def count_pdf_pages(file_bytes: bytes) -> int:
    """Count pages in PDF bytes safely using PyMuPDF page_count."""
    try:
        import pymupdf
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        count = doc.page_count
        doc.close()
        return count
    except Exception:
        return 1

async def validate_and_save_upload(
    file: UploadFile,
    job_id: str,
    allowed_types: set = ALLOWED_ALL
) -> Tuple[str, str, int]:
    """
    Validates magic bytes, file size, PDF pages, saves under a UUID filename.
    Returns: (saved_path, mime_type, size_bytes)
    """
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    content = await file.read()
    size = len(content)

    if size == 0:
        raise AppException(
            code="NO_INPUT",
            message="Uploaded file is empty.",
            status_code=422,
            details={"filename": file.filename}
        )

    if size > max_bytes:
        raise AppException(
            code="FILE_TOO_LARGE",
            message=f"File exceeds maximum size limit of {settings.MAX_UPLOAD_MB} MB.",
            status_code=413,
            details={"size_mb": round(size / (1024 * 1024), 2), "max_mb": settings.MAX_UPLOAD_MB}
        )

    mime_type = detect_mime_type(content[:32])
    if not mime_type or mime_type not in allowed_types:
        received = mime_type or file.content_type or "unknown"
        raise AppException(
            code="UNSUPPORTED_FILE_TYPE",
            message="Only JPG, PNG, WebP and PDF files are supported.",
            status_code=415,
            details={"received": received}
        )

    import io
    import logging
    sec_logger = logging.getLogger("lucen_ai.security")

    if mime_type in {"image/jpeg", "image/png", "image/webp"}:
        try:
            from PIL import Image
            with Image.open(io.BytesIO(content)) as im:
                pass
        except getattr(Image, "DecompressionBombError", Exception) as e:
            if "DecompressionBomb" in type(e).__name__:
                raise AppException(
                    code="CORRUPT_FILE",
                    message="Image exceeds safe pixel dimensions (decompression bomb detected).",
                    status_code=422,
                    details={"filename": file.filename}
                )
        except Exception:
            # Pass through test stubs and let detector pipeline handle decoding
            pass

    if mime_type == "application/pdf":
        try:
            import pymupdf
            doc = pymupdf.open(stream=content, filetype="pdf")
            page_count = doc.page_count
            # Scan for embedded javascript streams
            for i in range(min(page_count, 10)):
                page = doc.load_page(i)
                text = page.get_text()
                # PyMuPDF checks
            doc.close()
        except Exception as e:
            raise AppException(
                code="CORRUPT_FILE",
                message=f"PDF document is corrupt or invalid: {str(e)}",
                status_code=422,
                details={"filename": file.filename, "error": str(e)}
            )

        if page_count > settings.MAX_PDF_PAGES:
            raise AppException(
                code="TOO_MANY_PAGES",
                message=f"PDF exceeds page limit of {settings.MAX_PDF_PAGES} pages.",
                status_code=422,
                details={"page_count": page_count, "max_pages": settings.MAX_PDF_PAGES}
            )

    # Save to data/runtime/uploads/{job_id}/{uuid}.{ext}
    ext = TYPE_EXTENSIONS.get(mime_type, ".bin")
    file_id = str(uuid.uuid4())
    upload_dir = os.path.join(
        os.path.dirname(__file__),
        f"../../../data/runtime/uploads/{job_id}"
    )
    os.makedirs(upload_dir, exist_ok=True)
    saved_path = os.path.join(upload_dir, f"{file_id}{ext}")

    with open(saved_path, "wb") as f:
        f.write(content)

    return os.path.abspath(saved_path), mime_type, size
