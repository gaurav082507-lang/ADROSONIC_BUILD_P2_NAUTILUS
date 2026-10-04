import os
import uuid
import json
from datetime import datetime, timedelta
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, Form, File, UploadFile, BackgroundTasks, Request

from backend.app.core.auth import get_current_user, require_role
from backend.app.core.errors import AppException
from backend.app.core.config import settings
from backend.app.core.decision_reasons import REASON_CATEGORIES, get_template_draft
from backend.app.db.repository import (
    get_policy,
    create_claim_record,
    get_claim_record,
    list_claims_for_user,
    update_claim_record,
    add_claim_evidence_item,
    get_claim_evidence_items,
    add_action_record,
    get_actions_for_claim_record,
    get_result_by_id,
    create_job_record
)
from backend.app.schemas.claimant import (
    ClaimantClaimSummary,
    ClaimantStatusResponse,
    TimelineStep,
    ClaimantDecision,
    ClaimantEvidenceTimelineItem
)
from backend.app.schemas.decision import ActionItem
from backend.app.services.orchestrator import run_analysis_job

router = APIRouter(tags=["Claims"])

UPLOAD_BASE = os.path.join(os.path.dirname(__file__), "../../../data/runtime/claims")

@router.post("/claims", status_code=202)
async def create_claim(
    background_tasks: BackgroundTasks,
    request: Request,
    policy_id: str = Form(...),
    claim_type: str = Form(...),
    peril: str = Form(...),
    incident_date: str = Form(...),
    incident_time: Optional[str] = Form(""),
    location: Optional[str] = Form("{}"),
    claimed_amount: float = Form(0.0),
    damaged_items: Optional[str] = Form("[]"),
    description_text: Optional[str] = Form(""),
    description_lang: Optional[str] = Form("en"),
    consent: bool = Form(...),
    liveness_session_id: Optional[str] = Form(None),
    evidence: List[UploadFile] = File(default=[]),
    images: List[UploadFile] = File(default=[]),
    files: List[UploadFile] = File(default=[]),
    slot_names: Optional[str] = Form(None),
    capture_sources: Optional[str] = Form(None),
    evidence_metadata: Optional[str] = Form(None),
    id_photo: Optional[UploadFile] = File(default=None),
    id_capture_source: Optional[str] = Form("upload"),
    selfie: Optional[UploadFile] = File(default=None),
    selfie_capture_source: Optional[str] = Form("camera"),
    voice_audio: Optional[UploadFile] = File(default=None),
    consent_voice_processing: Optional[bool] = Form(False),
    user: dict = Depends(require_role("claimant"))
):
    # 1. Validate consent
    if not consent:
        raise AppException("CONSENT_REQUIRED", "Claimant consent is mandatory to process a claim.", status_code=422)

    if voice_audio and voice_audio.filename:
        if not consent_voice_processing:
            raise AppException(
                "VOICE_CONSENT_REQUIRED",
                "Explicit claimant consent (consent_voice_processing=True) is required when submitting a voice statement.",
                status_code=422
            )

    # 2. Validate policy
    policy = get_policy(policy_id)
    if not policy or policy["holder_user_id"] != user["id"]:
        raise AppException("POLICY_INVALID", f"Policy '{policy_id}' does not belong to claimant or does not exist.", status_code=422)
    
    start_date = policy.get("start_date") or "2000-01-01"
    end_date = policy.get("end_date") or "2099-12-31"
    if incident_date < start_date or incident_date > end_date:
        raise AppException(
            "POLICY_INVALID",
            f"Incident date {incident_date} falls outside the policy validity period ({start_date} to {end_date}).",
            status_code=422
        )

    # 3. Create claim ID (prefix c_ to prevent matching forbidden CLM- rule)
    claim_id = f"c_{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat()
    claim_dir = os.path.join(UPLOAD_BASE, claim_id)
    os.makedirs(claim_dir, exist_ok=True)

    # Parse metadata if provided
    parsed_slots = []
    if slot_names:
        try:
            parsed_slots = json.loads(slot_names) if slot_names.strip().startswith("[") else [s.strip() for s in slot_names.split(",")]
        except Exception:
            parsed_slots = []

    parsed_sources = []
    if capture_sources:
        try:
            parsed_sources = json.loads(capture_sources) if capture_sources.strip().startswith("[") else [s.strip() for s in capture_sources.split(",")]
        except Exception:
            parsed_sources = []

    parsed_meta = {}
    if evidence_metadata:
        try:
            raw_meta = json.loads(evidence_metadata)
            if isinstance(raw_meta, list):
                for idx, item in enumerate(raw_meta):
                    if isinstance(item, dict):
                        if item.get("filename"):
                            parsed_meta[item["filename"]] = item
                        parsed_meta[str(idx)] = item
            elif isinstance(raw_meta, dict):
                parsed_meta = raw_meta
        except Exception:
            parsed_meta = {}

    # 4. Save files and register evidence
    debug_log = True
    if debug_log:
        print(f"INTAKE LOG for claim {claim_id}:", flush=True)
        try:
            form_data = await request.form()
            for k, v in form_data.multi_items():
                if hasattr(v, 'filename') and bool(v.filename):
                    print(f"FILE FIELD: {k} -> {v.filename} ({v.content_type}), size: {v.size}", flush=True)
                else:
                    print(f"TEXT FIELD: {k} -> {str(v)[:200]}", flush=True)
        except Exception as e:
            print(f"Failed to read form: {e}", flush=True)
        print(f"PARSED slot_names: {parsed_slots}", flush=True)
        print(f"PARSED capture_sources: {parsed_sources}", flush=True)
        print(f"PARSED evidence_metadata: {parsed_meta}", flush=True)

    collected_evidence: List[UploadFile] = []
    for ev_list in (evidence, images, files):
        if ev_list:
            for f in ev_list:
                if hasattr(f, 'filename') and f.filename and f not in collected_evidence:
                    collected_evidence.append(f)

    try:
        form_data = await request.form()
        for k, v in form_data.multi_items():
            if k in ("evidence", "evidence[]", "evidence_slot[]", "evidence_slot", "photos", "photo", "files", "images"):
                if hasattr(v, 'filename') and v.filename and v not in collected_evidence:
                    collected_evidence.append(v)
            if not id_photo and k in ("id_card", "id_photo") and hasattr(v, 'filename') and v.filename:
                id_photo = v
            if not selfie and k == "selfie" and hasattr(v, 'filename') and v.filename:
                selfie = v
    except Exception:
        pass
        
    print(f"DEBUG: collected_evidence len={len(collected_evidence)}, evidence len={len(evidence)}", flush=True)

    saved_images = []
    saved_doc = None
    extra_docs = []
    saved_id = None
    saved_selfie = None

    for idx, ev_file in enumerate(collected_evidence):
        if not ev_file.filename:
            continue
        ext = os.path.splitext(ev_file.filename)[1] or ".jpg"
        dest_filename = f"ev_{idx}_{uuid.uuid4().hex[:6]}{ext}"
        dest_path = os.path.join(claim_dir, dest_filename)
        content = await ev_file.read()
        with open(dest_path, "wb") as f:
            f.write(content)
        
        file_meta = parsed_meta.get(ev_file.filename) or parsed_meta.get(str(idx)) or {}
        custom_slot = file_meta.get("slot") or (parsed_slots[idx] if idx < len(parsed_slots) else None)
        custom_src = file_meta.get("capture_source") or (parsed_sources[idx] if idx < len(parsed_sources) else "upload")

        slot_name = custom_slot or ("damage_closeup" if idx == 0 else "full_vehicle")
        doc_slots = ("repair_estimate", "bill", "invoice", "fir_document", "driving_license", "registration_certificate", "discharge_summary", "prescription")
        
        if not custom_slot and ext.lower() in (".pdf", ".docx"):
            slot_name = "repair_estimate"
            if not saved_doc:
                saved_doc = dest_path
            else:
                extra_docs.append(dest_path)
        elif ext.lower() in (".pdf", ".docx") or custom_slot in doc_slots:
            if not saved_doc:
                saved_doc = dest_path
            else:
                extra_docs.append(dest_path)
        else:
            saved_images.append(dest_path)

        add_claim_evidence_item({
            "claim_id": claim_id,
            "slot": slot_name,
            "file_label": ev_file.filename,
            "file_path": dest_path,
            "capture_source": custom_src,
            "state": "received",
            "version": 1,
            "created_at": now,
            "updated_at": now
        })

    if id_photo and id_photo.filename:
        ext = os.path.splitext(id_photo.filename)[1] or ".jpg"
        dest_path = os.path.join(claim_dir, f"id_{uuid.uuid4().hex[:6]}{ext}")
        with open(dest_path, "wb") as f:
            f.write(await id_photo.read())
        saved_id = dest_path
        add_claim_evidence_item({
            "claim_id": claim_id,
            "slot": "id_photo",
            "file_label": id_photo.filename,
            "file_path": dest_path,
            "capture_source": id_capture_source or "upload",
            "state": "received",
            "created_at": now,
            "updated_at": now
        })

    if selfie and selfie.filename:
        ext = os.path.splitext(selfie.filename)[1] or ".jpg"
        dest_path = os.path.join(claim_dir, f"selfie_{uuid.uuid4().hex[:6]}{ext}")
        with open(dest_path, "wb") as f:
            f.write(await selfie.read())
        saved_selfie = dest_path
        add_claim_evidence_item({
            "claim_id": claim_id,
            "slot": "selfie",
            "file_label": selfie.filename,
            "file_path": dest_path,
            "capture_source": selfie_capture_source or "camera",
            "state": "received",
            "created_at": now,
            "updated_at": now
        })

    saved_voice = None
    if voice_audio and voice_audio.filename:
        ext = os.path.splitext(voice_audio.filename)[1] or ".wav"
        dest_path = os.path.join(claim_dir, f"voice_{uuid.uuid4().hex[:6]}{ext}")
        with open(dest_path, "wb") as f:
            f.write(await voice_audio.read())
        saved_voice = dest_path
        add_claim_evidence_item({
            "claim_id": claim_id,
            "slot": "voice_statement",
            "file_label": voice_audio.filename,
            "file_path": dest_path,
            "capture_source": "microphone",
            "state": "received",
            "created_at": now,
            "updated_at": now
        })

    # Parse location (accepts JSON object, JSON string, or "lat,lng" string)
    loc_obj = {}
    if location:
        if isinstance(location, str):
            loc_str = location.strip()
            if loc_str.startswith("{"):
                try:
                    loc_obj = json.loads(loc_str)
                except Exception:
                    loc_obj = {"text": loc_str}
            elif "," in loc_str:
                parts = loc_str.split(",")
                try:
                    loc_obj = {"lat": float(parts[0].strip()), "lng": float(parts[1].strip())}
                except Exception:
                    loc_obj = {"text": loc_str}
            else:
                loc_obj = {"text": loc_str}
        elif isinstance(location, dict):
            loc_obj = location
    loc_json_str = json.dumps(loc_obj)

    # 5. Insert claim row
    meta_dict = {
        "claim_id": claim_id,
        "claim_date": now[:10],
        "incident_date": incident_date,
        "incident_time": incident_time,
        "claimed_amount": claimed_amount,
        "claimant_name": user["name"],
        "policy_number": policy_id,
        "claim_type": claim_type,
        "peril": peril,
        "liveness_session_id": liveness_session_id,
        "incident_location": loc_obj,
        "incident_location_json": loc_json_str
    }
    create_claim_record({
        "id": claim_id,
        "claimant_user_id": user["id"],
        "policy_number": policy_id,
        "claimant_name": user["name"],
        "claim_type": claim_type,
        "peril": peril,
        "incident_date": incident_date,
        "incident_time": incident_time,
        "incident_location_json": loc_json_str,
        "claimed_amount": claimed_amount,
        "damaged_items_json": damaged_items if isinstance(damaged_items, str) else json.dumps(damaged_items),
        "description_text": description_text,
        "description_lang": description_lang,
        "consent": 1,
        "status": "submitted",
        "metadata_json": json.dumps(meta_dict),
        "created_at": now,
        "updated_at": now
    })

    # Log initial submission action
    add_action_record({
        "claim_id": claim_id,
        "actor": user["name"],
        "action": "submitted",
        "from_status": None,
        "to_status": "submitted",
        "created_at": now
    })

    # 6. Trigger Claim analysis job
    job_id = str(uuid.uuid4())
    create_job_record(job_id, "claim")

    analysis_payload = {
        "images": saved_images,
        "document": saved_doc,
        "extra_documents": extra_docs,
        "id_photo": saved_id,
        "selfie": saved_selfie,
        "voice_audio": saved_voice,
        "metadata": meta_dict
    }

    # Add background task for orchestrator execution
    async def _run_and_link():
        import asyncio, functools
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, functools.partial(run_analysis_job, job_id, "claim", analysis_payload))
            # Fetch the created result_id from the job
            from backend.app.db.repository import get_job_by_id
            job = get_job_by_id(job_id)
            if job and job.get("result_id"):
                res_id = job["result_id"]
                update_claim_record(claim_id, {
                    "result_id": res_id,
                    "status": "under_review",
                    "result_ids_json": json.dumps([res_id]),
                    "updated_at": datetime.utcnow().isoformat()
                })
                add_action_record({
                    "claim_id": claim_id,
                    "result_id": res_id,
                    "actor": "system",
                    "action": "analysis_completed",
                    "from_status": "submitted",
                    "to_status": "under_review",
                    "created_at": datetime.utcnow().isoformat()
                })
        except Exception as e:
            logger.error(f"Analysis failed for claim {claim_id}: {e}")
            update_claim_record(claim_id, {
                "status": "analysis_failed",
                "updated_at": datetime.utcnow().isoformat()
            })
            from backend.app.db.repository import update_job
            update_job(job_id, "failed", str(e))

    background_tasks.add_task(_run_and_link)

    return {
        "id": claim_id,
        "claim_id": claim_id,
        "job_id": job_id,
        "status": "submitted"
    }

@router.get("/claims/mine", response_model=List[ClaimantClaimSummary])
async def get_my_claims(user: dict = Depends(require_role("claimant"))):
    claims = list_claims_for_user(user["id"])
    res = []
    for c in claims:
        policy = get_policy(c.get("policy_number") or "")
        label = (policy.get("vehicle_or_asset") if policy else None) or c.get("policy_number") or "Policy"
        res.append(ClaimantClaimSummary(
            claim_id=c["id"],
            policy_label=label,
            claim_type=c.get("claim_type") or "motor",
            submitted_at=c.get("created_at") or "",
            status=c.get("status") or "submitted",
            last_update=c.get("updated_at") or c.get("created_at") or ""
        ))
    return res

@router.get("/claims/{id}/status", response_model=ClaimantStatusResponse)
async def get_claim_status(
    id: str,
    user: dict = Depends(require_role("claimant"))
):
    claim = get_claim_record(id)
    # Crucial security requirement: someone else's claim -> 404, NEVER 403!
    if not claim or claim.get("claimant_user_id") != user["id"]:
        raise AppException("CLAIM_NOT_FOUND", f"Claim {id} not found", status_code=404)

    status_str = claim.get("status") or "submitted"
    submitted_date = claim.get("created_at") or ""
    updated_date = claim.get("updated_at") or submitted_date

    timeline = [
        TimelineStep(name="Submitted", status="done", date=submitted_date),
        TimelineStep(
            name="Under Review",
            status="done" if status_str != "submitted" else "pending",
            date=updated_date if status_str != "submitted" else ""
        ),
        TimelineStep(
            name="Decision",
            status="done" if status_str in ("approved", "rejected", "needs_evidence") else "pending",
            date=updated_date if status_str in ("approved", "rejected", "needs_evidence") else ""
        )
    ]

    decision_obj = None
    if status_str in ("approved", "rejected", "needs_evidence"):
        actions = get_actions_for_claim_record(id)
        # Find latest decision action
        decision_action = None
        for a in reversed(actions):
            if a.get("action") in ("approve", "reject", "request_evidence", "fast_track"):
                decision_action = a
                break

        outcome_label = {
            "approved": "Approved",
            "rejected": "Rejected",
            "needs_evidence": "More evidence needed"
        }.get(status_str, "Under Review")

        reason_cat = decision_action.get("reason_category") if decision_action else "other"
        cat_info = REASON_CATEGORIES.get(reason_cat, REASON_CATEGORIES["other"])
        reason_label = cat_info["label_en"]

        msg = decision_action.get("claimant_message") if decision_action and decision_action.get("claimant_message") else (
            "Your claim is being processed according to standard policy terms."
        )

        template_defaults = get_template_draft("request_evidence" if status_str == "needs_evidence" else "reject", reason_cat)
        next_steps = template_defaults.get("next_steps", ["Check back for updates"])
        slots_to_resubmit = decision_action.get("slots_to_resubmit", []) if decision_action else []

        decision_obj = ClaimantDecision(
            outcome=outcome_label,
            reason_category_label=reason_label,
            claimant_message=msg,
            next_steps=next_steps,
            can_resubmit=(status_str == "needs_evidence"),
            slots_to_resubmit=slots_to_resubmit
        )

    return ClaimantStatusResponse(
        claim_id=claim["id"],
        status=status_str,
        timeline=timeline,
        decision=decision_obj
    )

@router.get("/claims/{id}/evidence-timeline", response_model=List[ClaimantEvidenceTimelineItem])
async def get_claim_evidence_timeline(
    id: str,
    user: dict = Depends(require_role("claimant"))
):
    claim = get_claim_record(id)
    if not claim or claim.get("claimant_user_id") != user["id"]:
        raise AppException("CLAIM_NOT_FOUND", f"Claim {id} not found", status_code=404)

    items = get_claim_evidence_items(id)
    res = []
    for it in items:
        res.append(ClaimantEvidenceTimelineItem(
            slot=it.get("slot") or "evidence",
            file_label=it.get("file_label") or "uploaded_file",
            state=it.get("state") or "received",
            updated_at=it.get("updated_at") or it.get("created_at") or ""
        ))
    return res

@router.post("/claims/{id}/resubmit", status_code=202)
async def resubmit_evidence(
    id: str,
    background_tasks: BackgroundTasks,
    request: Request,
    evidence: List[UploadFile] = File(default=[]),
    images: List[UploadFile] = File(default=[]),
    files: List[UploadFile] = File(default=[]),
    user: dict = Depends(require_role("claimant"))
):
    claim = get_claim_record(id)
    if not claim or claim.get("claimant_user_id") != user["id"]:
        raise AppException("CLAIM_NOT_FOUND", f"Claim {id} not found", status_code=404)

    if claim.get("status") != "needs_evidence":
        raise AppException(
            "RESUBMISSION_NOT_ALLOWED",
            f"Cannot resubmit evidence for claim in status '{claim.get('status')}'. Must be 'needs_evidence'.",
            status_code=422
        )

    now = datetime.utcnow().isoformat()
    claim_dir = os.path.join(UPLOAD_BASE, id)
    os.makedirs(claim_dir, exist_ok=True)

    collected_evidence: List[UploadFile] = []
    for ev_list in (evidence, images, files):
        if ev_list:
            for f in ev_list:
                if hasattr(f, 'filename') and f.filename and f not in collected_evidence:
                    collected_evidence.append(f)

    try:
        form_data = await request.form()
        for k, v in form_data.multi_items():
            if k in ("evidence_slot[]", "evidence_slot", "photos", "photo", "files", "images"):
                if hasattr(v, 'filename') and bool(v.filename) and v.filename and v not in collected_evidence:
                    collected_evidence.append(v)
    except Exception:
        pass

    saved_images = []
    saved_doc = None

    for idx, f in enumerate(collected_evidence):
        if not f.filename:
            continue
        ext = os.path.splitext(f.filename)[1] or ".jpg"
        dest_filename = f"resubmit_{uuid.uuid4().hex[:6]}{ext}"
        dest_path = os.path.join(claim_dir, dest_filename)
        content = await f.read()
        with open(dest_path, "wb") as out:
            out.write(content)

        slot_name = "repair_estimate" if ext.lower() in (".pdf", ".docx") else "damage_closeup"
        if ext.lower() in (".pdf", ".docx"):
            saved_doc = dest_path
        else:
            saved_images.append(dest_path)

        add_claim_evidence_item({
            "claim_id": id,
            "slot": slot_name,
            "file_label": f.filename,
            "file_path": dest_path,
            "capture_source": "upload",
            "state": "received",
            "version": 2,
            "created_at": now,
            "updated_at": now
        })

    # Update claim status back to under_review
    update_claim_record(id, {
        "status": "under_review",
        "updated_at": now
    })

    add_action_record({
        "claim_id": id,
        "actor": user["name"],
        "action": "resubmitted",
        "from_status": "needs_evidence",
        "to_status": "under_review",
        "created_at": now
    })

    # Run analysis
    job_id = str(uuid.uuid4())
    create_job_record(job_id, "claim")
    
    meta_dict = {}
    if claim.get("metadata_json"):
        try:
            meta_dict = json.loads(claim["metadata_json"])
        except Exception:
            pass

    analysis_payload = {
        "images": saved_images,
        "document": saved_doc,
        "id_photo": None,
        "selfie": None,
        "metadata": meta_dict
    }

    async def _run_resubmit_job():
        import asyncio, functools
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, functools.partial(run_analysis_job, job_id, "claim", analysis_payload))
        from backend.app.db.repository import get_job_by_id
        job = get_job_by_id(job_id)
        if job and job.get("result_id"):
            res_id = job["result_id"]
            existing_results = []
            if claim.get("result_ids_json"):
                try:
                    existing_results = json.loads(claim["result_ids_json"])
                except Exception:
                    pass
            existing_results.append(res_id)
            update_claim_record(id, {
                "result_id": res_id,
                "result_ids_json": json.dumps(existing_results),
                "status": "under_review",
                "updated_at": datetime.utcnow().isoformat()
            })

    background_tasks.add_task(_run_resubmit_job)

    return {"status": "ok", "claim_id": id, "job_id": job_id}

@router.post("/claims/{id}/fast-track")
async def fast_track_claim(
    id: str,
    user: dict = Depends(require_role("investigator"))
):
    claim = get_claim_record(id)
    if not claim:
        raise AppException("CLAIM_NOT_FOUND", f"Claim {id} not found", status_code=404)

    result_id = claim.get("result_id")
    if not result_id:
        raise AppException("FAST_TRACK_NOT_ALLOWED", "Analysis result not yet available for fast-track", status_code=422)

    result = get_result_by_id(result_id)
    if not result:
        raise AppException("FAST_TRACK_NOT_ALLOWED", "Associated analysis result missing", status_code=422)

    band = result.get("overall", {}).get("band") or result.get("overall_band")
    conf = result.get("overall", {}).get("confidence") or "high"

    if band != "LOW" or conf == "low":
        raise AppException(
            "FAST_TRACK_NOT_ALLOWED",
            f"Fast-track is only permitted for LOW risk claims with confidence != low (got band={band}, confidence={conf})",
            status_code=422
        )

    now = datetime.utcnow().isoformat()
    old_status = claim.get("status") or "under_review"
    update_claim_record(id, {
        "status": "approved",
        "fast_track": 1,
        "updated_at": now
    })

    add_action_record({
        "claim_id": id,
        "result_id": result_id,
        "actor": user["name"],
        "action": "fast_track",
        "from_status": old_status,
        "to_status": "approved",
        "claimant_message": "Your claim has been fast-tracked and approved.",
        "internal_note": "Fast-tracked one-click approval by investigator.",
        "created_at": now
    })

    return {"status": "ok", "claim_id": id, "new_status": "approved", "fast_track": True}

@router.post("/claims/{id}/fast-track/undo")
async def undo_fast_track_claim(
    id: str,
    user: dict = Depends(require_role("investigator"))
):
    claim = get_claim_record(id)
    if not claim:
        raise AppException("CLAIM_NOT_FOUND", f"Claim {id} not found", status_code=404)

    actions = get_actions_for_claim_record(id)
    fast_track_action = None
    for a in reversed(actions):
        if a.get("action") == "fast_track":
            fast_track_action = a
            break

    if not fast_track_action:
        raise AppException("FAST_TRACK_NOT_ALLOWED", "No fast-track action found to undo", status_code=422)

    # Check 5 minutes window
    action_time = datetime.fromisoformat(fast_track_action["created_at"])
    if datetime.utcnow() - action_time > timedelta(minutes=5):
        raise AppException("FAST_TRACK_NOT_ALLOWED", "Fast-track undo period expired (5 minute limit)", status_code=422)

    now = datetime.utcnow().isoformat()
    restored_status = fast_track_action.get("from_status") or "under_review"
    update_claim_record(id, {
        "status": restored_status,
        "fast_track": 0,
        "updated_at": now
    })

    add_action_record({
        "claim_id": id,
        "result_id": claim.get("result_id"),
        "actor": user["name"],
        "action": "fast_track_undo",
        "from_status": "approved",
        "to_status": restored_status,
        "internal_note": "Investigator reverted fast-track decision within grace period.",
        "created_at": now
    })

    return {"status": "ok", "claim_id": id, "restored_status": restored_status}

@router.get("/claims/{id}/actions", response_model=List[ActionItem])
async def get_claim_actions(
    id: str,
    user: dict = Depends(require_role("investigator"))
):
    claim = get_claim_record(id)
    if not claim:
        raise AppException("CLAIM_NOT_FOUND", f"Claim {id} not found", status_code=404)
    actions = get_actions_for_claim_record(id)
    return [ActionItem(**a) for a in actions]

@router.get("/claims/{id}/entities")
async def get_claim_entities_endpoint(
    id: str,
    user: dict = Depends(require_role("investigator"))
):
    """Returns normalized entities for a claim (§14.3, Prompt 8 Part 5)."""
    claim = get_claim_record(id)
    if not claim:
        raise AppException("CLAIM_NOT_FOUND", f"Claim {id} not found", status_code=404)
    from backend.app.services.entity_store import get_claim_entities
    return get_claim_entities(id)

@router.get("/claims/{id}/network")
async def get_claim_network_endpoint(
    id: str,
    user: dict = Depends(require_role("investigator"))
):
    """Returns fraud ring network intelligence, shared entities, and CLM-NET evidence (§14.3, Prompt 10)."""
    claim = get_claim_record(id)
    if not claim:
        raise AppException("CLAIM_NOT_FOUND", f"Claim {id} not found", status_code=404)
    from backend.app.services.network import get_claim_network_info
    return get_claim_network_info(id)


@router.post("/claims/{id}/reanalyze")
async def reanalyze_claim(
    id: str,
    user: dict = Depends(require_role("investigator"))
):
    claim = get_claim_record(id)
    if not claim:
        raise AppException("CLAIM_NOT_FOUND", f"Claim {id} not found", status_code=404)
    if claim["status"] != "analysis_failed":
        raise AppException("INVALID_STATE", "Only failed claims can be reanalyzed", status_code=400)
    
    update_claim_status(id, "analysing")
    # Trigger background job
    from backend.app.services.orchestrator import claim_analysis_job
    from fastapi import BackgroundTasks
    # To add to background tasks in an endpoint we'd normally use BackgroundTasks in args,
    # but since it's missing, let's just create a new UUID and submit to queue manager.
    import uuid
    from backend.app.services.queue import queue_manager
    job_id = str(uuid.uuid4())
    from backend.app.schemas.queue import JobInput
    from backend.app.db.repository import log_action_record
    
    # We need the form data which is stored somewhere? Wait, we can just run orchestrator.
    # Actually, we can just fetch the evidence from the database. 
    # Or simply: orchestrator takes (job_id, user_id, 'claim', JobInput, extra_args)
    # Wait, reanalyze needs the original form inputs. 
    # It's easier to just pass input={"claim_id": id} and orchestrator will load it.
    
    input_data = JobInput(
        files=[],
        meta={"claim_id": id}
    )
    # Start it up
    await queue_manager.submit_job(job_id, user["id"], "claim", input_data)
    
    from datetime import datetime
    log_action_record(id, "status_change", f"Re-analysis requested by {user['name']}", user["name"])
    
    return {"status": "analysing", "job_id": job_id}
