import os
import uuid
import json
import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import cv2
import numpy as np

from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel

from ...core.config import settings
from ...core.auth import get_current_user, require_role
from ...db.repository import create_liveness_session, get_liveness_session
from ...detectors.identity.liveness import verify_liveness

router = APIRouter(prefix="/identity", tags=["Identity & Liveness"])

ALL_CHALLENGES = ["blink", "turn_left", "turn_right", "look_up"]


class LivenessSessionResponse(BaseModel):
    session_id: str
    nonce: str
    challenges: List[str]
    spoken_code: str
    expires_at: str


# P2-14: Both session issue and verify require claimant OR investigator auth
_LIVENESS_ROLES = Depends(require_role("claimant", "investigator"))


@router.post("/liveness/session", response_model=LivenessSessionResponse)
async def issue_liveness_session(
    _user: Dict[str, Any] = _LIVENESS_ROLES
):
    """
    Issues a single-use random liveness session with 3 randomised challenges.
    Valid for 120 seconds. Requires claimant or investigator auth (P2-14).
    """
    session_id = f"live_{uuid.uuid4().hex[:12]}"
    nonce = uuid.uuid4().hex
    challenges = random.sample([c for c in ALL_CHALLENGES if c != 'spoken_code'], 3)
    spoken_code = ""
    expires_at = (datetime.utcnow() + timedelta(seconds=settings.LIVENESS_SESSION_S)).isoformat()

    create_liveness_session(session_id, nonce, challenges, spoken_code, expires_at)

    return LivenessSessionResponse(
        session_id=session_id,
        nonce=nonce,
        challenges=challenges,
        spoken_code=spoken_code,
        expires_at=expires_at
    )


@router.post("/liveness/verify")
async def verify_liveness_endpoint(
    request: Request,
    session_id: str = Form(...),
    nonce: str = Form(...),
    frame_metadata: Optional[str] = Form(None),
    frames: List[UploadFile] = File(default=[]),
    _user: Dict[str, Any] = _LIVENESS_ROLES  # P2-14: auth required
):
    """
    Verifies 8-40 captured liveness frames against the issued session challenges.
    Requires claimant or investigator auth (P2-14).
    """
    collected_frames = []
    if frames:
        for f in frames:
            if hasattr(f, 'filename') and bool(f.filename):
                collected_frames.append(f)
    
    try:
        form_data = await request.form()
        for k, v in form_data.multi_items():
            if k in ("frames", "frames[]", "frame[]", "frame"):
                if hasattr(v, 'filename') and bool(v.filename) and v not in collected_frames:
                    collected_frames.append(v)
    except Exception:
        pass

    if len(collected_frames) < 8 or len(collected_frames) > 40:
        raise HTTPException(
            status_code=422,
            detail=f"Frame count must be between 8 and 40. Received {len(collected_frames)} frames."
        )

    meta = {}
    if frame_metadata:
        try:
            raw_fmeta = json.loads(frame_metadata)
            if isinstance(raw_fmeta, list):
                for item in raw_fmeta:
                    if isinstance(item, dict):
                        idx = item.get("index")
                        if idx is not None:
                            meta[str(idx)] = item
            elif isinstance(raw_fmeta, dict):
                meta = raw_fmeta
        except Exception:
            pass

    session = get_liveness_session(session_id)
    challenges_order = session.get("challenges", ["blink", "turn_left", "turn_right"]) if session else ["blink", "turn_left", "turn_right"]

    decoded_frames = []
    num_frames = len(collected_frames)
    frames_per_challenge = max(1, num_frames // max(1, len(challenges_order)))

    for idx, f in enumerate(collected_frames):
        content = await f.read()
        nparr = np.frombuffer(content, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_bgr is None:
            continue

        f_meta = meta.get(f.filename) or meta.get(str(idx)) or {}
        ch_name = f_meta.get("challenge")
        if not ch_name:
            ch_idx = min(idx // frames_per_challenge, len(challenges_order) - 1)
            ch_name = challenges_order[ch_idx]
        ts = float(f_meta.get("timestamp", idx * 0.15))
        decoded_frames.append((img_bgr, ch_name, ts))

    result = verify_liveness(session_id, nonce, decoded_frames)

    ev_list = []
    for ev in result.get("evidence", []):
        ev_list.append(ev.model_dump() if hasattr(ev, "model_dump") else ev.dict())

    best_frame_url = None
    best_img = result.get("best_frontal_frame")
    if best_img is not None:
        try:
            from .artifacts import make_signed_artifact_url
            art_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../data/runtime/artifacts", session_id))
            os.makedirs(art_dir, exist_ok=True)
            best_path = os.path.join(art_dir, "best_frame.jpg")
            cv2.imwrite(best_path, best_img)
            best_frame_url = make_signed_artifact_url(session_id, "best_frame.jpg")
        except Exception:
            best_frame_url = None

    return {
        "session_id": session_id,
        "passed": result["passed"],
        "best_frame": best_frame_url,
        "reasons": result["reasons"],
        "per_challenge": result["per_challenge"],
        "evidence": ev_list,
        "limitation_note": result.get("limitation_note")
    }
