import json
import logging
from typing import Optional, List, Any
from fastapi import APIRouter, BackgroundTasks, UploadFile, File, Form, Depends, Request

from ...schemas.job import JobStatus
from ...services import job_manager, orchestrator
from ...core.security import validate_and_save_upload, ALLOWED_IMAGE_TYPES, ALLOWED_DOCUMENT_TYPES
from ...core.config import settings
from ...core.errors import AppException
from ...core.rate_limit import check_rate_limit

from ...core.auth import require_role

from starlette.datastructures import UploadFile as StarletteUploadFile

router = APIRouter(dependencies=[Depends(require_role("investigator"))])
logger = logging.getLogger("lucen_ai.api.analyze")

def _is_file(f: Any) -> bool:
    return bool(getattr(f, "filename", None))

@router.post("/analyze/image", status_code=202, dependencies=[Depends(check_rate_limit)])
async def analyze_image(
    background_tasks: BackgroundTasks,
    request: Request,
    file: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None)
):
    upload = file or image
    if not upload or not getattr(upload, "filename", None):
        try:
            form_data = await request.form()
            for k in ("file", "image", "files", "images"):
                val = form_data.get(k)
                if _is_file(val):
                    upload = val
                    break
        except Exception:
            pass

    if not upload:
        raise AppException(code="NO_INPUT", message="No image file provided.", status_code=422)

    job_id = job_manager.create_job("image")

    if settings.MOCK_ANALYSIS:
        content = await upload.read()
        await upload.seek(0)
        if content.startswith(b"fake"):
            # Dummy test bytes in mock mode
            background_tasks.add_task(orchestrator.run_analysis_job, job_id, "image")
            return {"job_id": job_id}

    saved_path, mime_type, size = await validate_and_save_upload(
        upload, job_id, ALLOWED_IMAGE_TYPES
    )
    background_tasks.add_task(orchestrator.run_analysis_job, job_id, "image", [saved_path])
    return {"job_id": job_id}

@router.post("/analyze/document", status_code=202, dependencies=[Depends(check_rate_limit)])
async def analyze_document(
    background_tasks: BackgroundTasks,
    request: Request,
    file: Optional[UploadFile] = File(None),
    document: Optional[UploadFile] = File(None)
):
    upload = file or document
    if not upload or not getattr(upload, "filename", None):
        try:
            form_data = await request.form()
            for k in ("file", "document", "files", "documents"):
                val = form_data.get(k)
                if _is_file(val):
                    upload = val
                    break
        except Exception:
            pass

    if not upload:
        raise AppException(code="NO_INPUT", message="No document file provided.", status_code=422)

    job_id = job_manager.create_job("document")

    if settings.MOCK_ANALYSIS:
        content = await upload.read()
        await upload.seek(0)
        if content.startswith(b"fake"):
            background_tasks.add_task(orchestrator.run_analysis_job, job_id, "document")
            return {"job_id": job_id}

    saved_path, mime_type, size = await validate_and_save_upload(
        upload, job_id, ALLOWED_DOCUMENT_TYPES
    )
    background_tasks.add_task(orchestrator.run_analysis_job, job_id, "document", [saved_path])
    return {"job_id": job_id}

@router.post("/analyze/claim", status_code=202, dependencies=[Depends(check_rate_limit)])
async def analyze_claim(
    background_tasks: BackgroundTasks,
    request: Request,
    image: List[UploadFile] = File(default=[]),
    images: List[UploadFile] = File(default=[]),
    files: List[UploadFile] = File(default=[]),
    document: Optional[UploadFile] = File(None),
    id_photo: Optional[UploadFile] = File(None),
    selfie: Optional[UploadFile] = File(None),
    metadata: Optional[str] = Form(None)
):
    collected_images: List[Any] = []
    for f_list in (image, images, files):
        if f_list:
            for f in f_list:
                if _is_file(f) and f not in collected_images:
                    collected_images.append(f)

    try:
        form_data = await request.form()
        for k, v in form_data.multi_items():
            if k in ("evidence_slot[]", "evidence_slot", "evidence", "photos", "photo"):
                if _is_file(v) and v not in collected_images:
                    collected_images.append(v)
            if not document and k in ("doc", "document") and _is_file(v):
                document = v
            if not id_photo and k in ("id_card", "id_photo") and _is_file(v):
                id_photo = v
            if not selfie and k == "selfie" and _is_file(v):
                selfie = v
    except Exception:
        pass

    # Check if no files provided at all
    if not collected_images and not document and not id_photo and not selfie:
        raise AppException(
            code="NO_INPUT",
            message="No files provided for claim analysis. At least one image or document is required.",
            status_code=422
        )

    # Check maximum image limit (0..6)
    if len(collected_images) > 6:
        raise AppException(
            code="TOO_MANY_FILES",
            message=f"Too many images. Maximum allowed is 6, received {len(collected_images)}.",
            status_code=422,
            details={"count": len(collected_images), "max": 6}
        )

    meta_obj = None
    if metadata:
        try:
            meta_obj = json.loads(metadata)
        except Exception as e:
            raise AppException(
                code="VALIDATION_ERROR",
                message=f"Metadata must be valid JSON: {str(e)}",
                status_code=422
            )

    if meta_obj and "incident_location" in meta_obj:
        loc = meta_obj["incident_location"]
        if isinstance(loc, str) and "," in loc:
            p = loc.split(",")
            try:
                meta_obj["incident_location"] = {"lat": float(p[0].strip()), "lng": float(p[1].strip())}
            except Exception:
                pass

    job_id = job_manager.create_job("claim")

    saved_images: List[str] = []
    saved_doc: Optional[str] = None
    saved_id: Optional[str] = None
    saved_selfie: Optional[str] = None

    for img_file in collected_images:
        if settings.MOCK_ANALYSIS:
            c = await img_file.read()
            await img_file.seek(0)
            if c.startswith(b"fake"):
                continue
        p, _, _ = await validate_and_save_upload(img_file, job_id, ALLOWED_IMAGE_TYPES)
        saved_images.append(p)

    if document:
        is_mock_fake = False
        if settings.MOCK_ANALYSIS:
            c = await document.read()
            await document.seek(0)
            if c.startswith(b"fake"):
                is_mock_fake = True
        if not is_mock_fake:
            saved_doc, _, _ = await validate_and_save_upload(document, job_id, ALLOWED_DOCUMENT_TYPES)

    if id_photo:
        is_mock_fake = False
        if settings.MOCK_ANALYSIS:
            c = await id_photo.read()
            await id_photo.seek(0)
            if c.startswith(b"fake"):
                is_mock_fake = True
        if not is_mock_fake:
            saved_id, _, _ = await validate_and_save_upload(id_photo, job_id, ALLOWED_IMAGE_TYPES)

    if selfie:
        is_mock_fake = False
        if settings.MOCK_ANALYSIS:
            c = await selfie.read()
            await selfie.seek(0)
            if c.startswith(b"fake"):
                is_mock_fake = True
        if not is_mock_fake:
            saved_selfie, _, _ = await validate_and_save_upload(selfie, job_id, ALLOWED_IMAGE_TYPES)

    payload = {
        "images": saved_images,
        "document": saved_doc,
        "id_photo": saved_id,
        "selfie": saved_selfie,
        "metadata": meta_obj
    }
    background_tasks.add_task(orchestrator.run_analysis_job, job_id, "claim", payload)
    return {"job_id": job_id}
