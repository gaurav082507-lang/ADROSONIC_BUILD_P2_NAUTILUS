import os
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
import cv2
import numpy as np

from ..schemas.evidence import Evidence, BBox
from ..schemas.result import DetectorStatus
from ..detectors.base import AnalysisContext, run_safely
from ..detectors.identity.face import analyze_faces
from ..detectors.identity.aadhaar_qr import analyze_aadhaar_qr
from ..services import job_manager
from ..db.repository import get_liveness_session

logger = logging.getLogger("lucen_ai.identity_pipeline")

# ---------------------------------------------------------------------------
# P1-10: Load calibrated scores for identity evidence from calibration.json
# Fallback defaults match audit-verified values.
# ---------------------------------------------------------------------------
_CALIBRATION_FILE = Path(__file__).resolve().parents[3] / "models" / "calibration.json"

_IDENTITY_SCORE_DEFAULTS = {
    "ID-LIVE-00": 0.05,
    "ID-LIVE-01": 0.90,
    "ID-LIVE-02": 0.80,
    "ID-LIVE-03": 0.35,
    "ID-DEEP-01": 0.85,
    "ID-QUAL-01": 0.10,
}

def _load_identity_scores() -> Dict[str, float]:
    try:
        data = json.loads(_CALIBRATION_FILE.read_text(encoding="utf-8"))
        block = data.get("identity_evidence", {})
        return {
            k: float(v["calibrated_score"])
            for k, v in block.items()
            if not k.startswith("_") and isinstance(v, dict) and "calibrated_score" in v
        }
    except Exception:
        return {}

_ID_SCORES: Dict[str, float] = {**_IDENTITY_SCORE_DEFAULTS, **_load_identity_scores()}


def get_identity_evidence_score(ev_id: str) -> float:
    """Return calibrated_score for an identity evidence id from calibration.json."""
    return _ID_SCORES.get(ev_id, _IDENTITY_SCORE_DEFAULTS.get(ev_id, 0.5))

@dataclass
class IdentityPipelineOutput:
    evidence: List[Evidence] = field(default_factory=list)
    status: List[DetectorStatus] = field(default_factory=list)
    artifacts: Dict[str, Path] = field(default_factory=dict)
    extras: Dict[str, Any] = field(default_factory=dict)


def create_side_by_side_artifact(
    id_crop: Optional[np.ndarray],
    selfie_crop: Optional[np.ndarray],
    similarity: Optional[float],
    verdict: Optional[str],
    dest_path: str
):
    """
    Renders a side-by-side face comparison image with verdict banner.
    """
    canvas_w, canvas_h = 420, 260
    canvas = np.ones((canvas_h, canvas_w, 3), dtype=np.uint8) * 30  # Dark slate background

    crop_size = 140
    y_crop = 50

    # ID face
    if id_crop is not None and id_crop.size > 0:
        c1 = cv2.resize(id_crop, (crop_size, crop_size))
        canvas[y_crop:y_crop + crop_size, 40:40 + crop_size] = c1
        cv2.rectangle(canvas, (39, y_crop - 1), (40 + crop_size, y_crop + crop_size), (80, 80, 80), 1)
    else:
        cv2.rectangle(canvas, (40, y_crop), (40 + crop_size, y_crop + crop_size), (50, 50, 50), -1)

    # Selfie face
    if selfie_crop is not None and selfie_crop.size > 0:
        c2 = cv2.resize(selfie_crop, (crop_size, crop_size))
        canvas[y_crop:y_crop + crop_size, 240:240 + crop_size] = c2
        cv2.rectangle(canvas, (239, y_crop - 1), (240 + crop_size, y_crop + crop_size), (80, 80, 80), 1)
    else:
        cv2.rectangle(canvas, (240, y_crop), (240 + crop_size, y_crop + crop_size), (50, 50, 50), -1)

    # Labels
    cv2.putText(canvas, "ID Photo", (60, y_crop + crop_size + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
    cv2.putText(canvas, "Selfie", (280, y_crop + crop_size + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

    # Header / Verdict banner
    sim_str = f"Similarity: {similarity:.2f}" if similarity is not None else "Similarity: N/A"
    verdict_str = f"{verdict or 'ANALYZED'}"
    color = (80, 220, 100) if verdict == "MATCH" else ((50, 150, 255) if verdict == "AMBIGUOUS" else (80, 80, 240))

    cv2.putText(canvas, verdict_str, (40, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
    cv2.putText(canvas, sim_str, (240, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    cv2.imwrite(dest_path, canvas)


async def run_identity_pipeline(
    ctx: AnalysisContext,
    prefix: str = "id:"
) -> IdentityPipelineOutput:
    """
    Executes the identity verification pipeline:
    1. Face detection & quality assessment
    2. Face matching (ID photo vs live selfie)
    3. Selfie AI / deepfake check (SigLIP)
    4. Liveness verification check
    5. Aadhaar Secure QR forensic validation
    """
    job_id = ctx.job_id
    all_evidence: List[Evidence] = []
    all_statuses: List[DetectorStatus] = []
    all_artifacts: Dict[str, Path] = {}
    pipeline_extras: Dict[str, Any] = {}

    id_photo_path = ctx.scratch.get("id_photo_path")
    selfie_path = ctx.scratch.get("selfie_path")
    liveness_session_id = ctx.scratch.get("liveness_session_id")
    artifacts_dir = ctx.scratch.get("artifacts_dir") or "data/runtime/artifacts/temp"

    id_bgr = cv2.imread(id_photo_path) if (id_photo_path and os.path.exists(id_photo_path)) else None
    selfie_bgr = cv2.imread(selfie_path) if (selfie_path and os.path.exists(selfie_path)) else None

    # Step 1 & 2: Face Quality, Matching & Selfie AI Check
    step1_name = "id_photo_match"
    if job_id:
        job_manager.start_step(job_id, step1_name)

    import time
    start_t = time.time()
    try:
        face_res = analyze_faces(id_bgr, selfie_bgr)
        dur = int((time.time() - start_t) * 1000)
        all_statuses.append(DetectorStatus(
            detector=step1_name,
            status="ok" if face_res["status"] == "ok" else "skipped",
            duration_ms=dur,
            reason=face_res.get("verdict")
        ))
        if job_id:
            job_manager.finish_step(job_id, step1_name, "ok", dur)

        all_evidence.extend(face_res.get("evidence", []))
        pipeline_extras["face"] = {
            "similarity": face_res.get("similarity"),
            "verdict": face_res.get("verdict"),
            "engine": face_res.get("engine"),
            "id_face": face_res.get("id_face"),
            "selfie_face": face_res.get("selfie_face"),
            "details": face_res.get("details", {})
        }

        # Save artifacts
        if face_res.get("id_face_crop") is not None and artifacts_dir:
            id_crop_p = os.path.join(artifacts_dir, "id_face_crop.jpg")
            cv2.imwrite(id_crop_p, face_res["id_face_crop"])
            all_artifacts["id_face_crop"] = Path(id_crop_p)

        if face_res.get("selfie_face_crop") is not None and artifacts_dir:
            selfie_crop_p = os.path.join(artifacts_dir, "selfie_face_crop.jpg")
            cv2.imwrite(selfie_crop_p, face_res["selfie_face_crop"])
            all_artifacts["selfie_face_crop"] = Path(selfie_crop_p)

        # Composite side by side
        if artifacts_dir:
            sbs_p = os.path.join(artifacts_dir, "identity_face_comparison.jpg")
            create_side_by_side_artifact(
                face_res.get("id_face_crop"),
                face_res.get("selfie_face_crop"),
                face_res.get("similarity"),
                face_res.get("verdict"),
                sbs_p
            )
            all_artifacts["identity_face_comparison"] = Path(sbs_p)

    except Exception as e:
        dur = int((time.time() - start_t) * 1000)
        logger.error(f"Face match step failed: {e}", exc_info=True)
        all_statuses.append(DetectorStatus(detector=step1_name, status="failed", duration_ms=dur, error=str(e)))
        if job_id:
            job_manager.finish_step(job_id, step1_name, "failed", dur)

    # Step 3: Liveness Verification Evaluation
    step2_name = "selfie_liveness"
    if job_id:
        job_manager.start_step(job_id, step2_name)

    start_t = time.time()
    try:
        liv_status = "ok"
        liv_reason = None
        if liveness_session_id:
            s = get_liveness_session(liveness_session_id)
            if s and s.get("used"):
                all_evidence.append(Evidence(
                    id="ID-LIVE-00",
                    kind="info",
                    weight=0.0,
                    effective_weight=0.0,
                    calibrated_score=get_identity_evidence_score("ID-LIVE-00"),
                    severity="low",
                    title="Liveness Passed",
                    reason="Server-verified liveness challenge completed successfully.",
                    details={"session_id": liveness_session_id}
                ))
                pipeline_extras["liveness"] = {"status": "passed", "session_id": liveness_session_id}
                liv_status = "ok"
            elif s and s.get("status") == "failed":
                # Session was started and challenges were actively failed
                all_evidence.append(Evidence(
                    id="ID-LIVE-01",
                    kind="risk",
                    weight=0.75,
                    effective_weight=0.75,
                    calibrated_score=get_identity_evidence_score("ID-LIVE-01"),
                    severity="high",
                    title="Liveness Failed",
                    reason="Liveness challenge was attempted but challenges were not passed.",
                    details={"session_id": liveness_session_id, "session_status": s.get("status")}
                ))
                pipeline_extras["liveness"] = {"status": "failed", "session_id": liveness_session_id}
                liv_status = "skipped"
                liv_reason = "liveness challenge actively failed"
            else:
                # Session exists but expired, unused, or in unknown state — info-only (P1-9)
                _sess_status = s.get("status", "unknown") if s else "not_found"
                all_evidence.append(Evidence(
                    id="ID-LIVE-03",
                    kind="risk",
                    weight=0.15,
                    effective_weight=0.15,
                    calibrated_score=get_identity_evidence_score("ID-LIVE-03"),
                    severity="low",
                    title="Liveness Not Performed",
                    reason=f"Liveness session was not completed (session status: {_sess_status}).",
                    details={"session_id": liveness_session_id, "session_status": _sess_status}
                ))
                pipeline_extras["liveness"] = {"status": "not_completed", "session_id": liveness_session_id}
                liv_status = "skipped"
                liv_reason = f"liveness session not completed (status: {_sess_status})"
        elif selfie_bgr is not None:
            # Liveness not attempted (static selfie uploaded) -> ID-LIVE-03
            all_evidence.append(Evidence(
                id="ID-LIVE-03",
                kind="risk",
                weight=0.15,
                effective_weight=0.15,
                calibrated_score=get_identity_evidence_score("ID-LIVE-03"),
                severity="low",
                title="Liveness Not Attempted",
                reason="Live camera check was not performed; static selfie uploaded instead.",
                details={"fallback": "static_selfie"}
            ))
            pipeline_extras["liveness"] = {"status": "not_attempted"}
            liv_status = "skipped"
            liv_reason = "static selfie uploaded; live challenge not attempted"
        else:
            pipeline_extras["liveness"] = {"status": "no_selfie"}
            liv_status = "skipped"
            liv_reason = "no selfie provided"

        dur = int((time.time() - start_t) * 1000)
        all_statuses.append(DetectorStatus(detector=step2_name, status=liv_status, duration_ms=dur, reason=liv_reason))
        if job_id:
            job_manager.finish_step(job_id, step2_name, liv_status, dur)
    except Exception as e:
        dur = int((time.time() - start_t) * 1000)
        logger.error(f"Liveness step failed: {e}", exc_info=True)
        all_statuses.append(DetectorStatus(detector=step2_name, status="failed", duration_ms=dur, error=str(e)))
        if job_id:
            job_manager.finish_step(job_id, step2_name, "failed", dur)

    # Step 4: Aadhaar Secure QR Forensic Check
    step3_name = f"{prefix}aadhaar_qr"
    if job_id:
        job_manager.start_step(job_id, step3_name)

    start_t = time.time()
    try:
        qr_res = analyze_aadhaar_qr(id_bgr, selfie_bgr)
        dur = int((time.time() - start_t) * 1000)
        all_statuses.append(DetectorStatus(
            detector=step3_name,
            status="ok" if qr_res.get("has_qr") else "skipped",
            duration_ms=dur,
            reason=qr_res.get("signature_status")
        ))
        if job_id:
            job_manager.finish_step(job_id, step3_name, "ok", dur)

        all_evidence.extend(qr_res.get("evidence", []))
        pipeline_extras["aadhaar_qr"] = {
            "has_qr": qr_res.get("has_qr"),
            "is_secure_qr": qr_res.get("is_secure_qr"),
            "signature_valid": qr_res.get("signature_valid"),
            "signature_status": qr_res.get("signature_status"),
            "key_label": qr_res.get("key_label"),
            "masked_reference": qr_res.get("masked_reference"),
            "mismatches": qr_res.get("mismatches", []),
            "comparisons": qr_res.get("comparisons", {})
        }
    except Exception as e:
        dur = int((time.time() - start_t) * 1000)
        logger.error(f"Aadhaar QR step failed: {e}", exc_info=True)
        all_statuses.append(DetectorStatus(detector=step3_name, status="failed", duration_ms=dur, error=str(e)))
        if job_id:
            job_manager.finish_step(job_id, step3_name, "failed", dur)

    return IdentityPipelineOutput(
        evidence=all_evidence,
        status=all_statuses,
        artifacts=all_artifacts,
        extras=pipeline_extras
    )
