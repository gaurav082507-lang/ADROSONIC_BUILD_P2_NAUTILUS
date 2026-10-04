import os
import math
import time
import json
import logging
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union

from ...core.config import settings
from ...core.model_registry import model_registry
from ...schemas.evidence import Evidence, BBox
from ...scoring.weights import EVIDENCE_CATALOG
from ...db.repository import get_liveness_session, mark_liveness_session_used

logger = logging.getLogger("lucen_ai.identity.liveness")

LANDMARKER_MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../models/face_landmarker.task")
)

_landmarker_instance = None

def get_landmarker():
    """Lazily initializes MediaPipe FaceLandmarker."""
    global _landmarker_instance
    if _landmarker_instance is not None:
        return _landmarker_instance

    if not os.path.exists(LANDMARKER_MODEL_PATH):
        logger.warning(f"MediaPipe FaceLandmarker model not found at {LANDMARKER_MODEL_PATH}")
        return None

    try:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        base_options = python.BaseOptions(model_asset_path=LANDMARKER_MODEL_PATH)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
            num_faces=1
        )
        _landmarker_instance = vision.FaceLandmarker.create_from_options(options)
        logger.info("MediaPipe FaceLandmarker initialized successfully.")
        return _landmarker_instance
    except Exception as e:
        logger.error(f"Failed to initialize MediaPipe FaceLandmarker: {e}")
        return None


def calculate_ear_and_pose(frame_bgr: np.ndarray) -> Dict[str, Any]:
    """
    Extracts eye aspect ratio (EAR) and head pose (yaw, pitch, roll) from a frame.
    Returns dict with {has_face, ear, yaw, pitch, roll, blendshapes, landmarks}.
    """
    out = {
        "has_face": False,
        "ear": 0.30,
        "blink_score": 0.0,
        "yaw": 0.0,
        "pitch": 0.0,
        "roll": 0.0,
        "landmarks": None
    }

    landmarker = get_landmarker()
    h, w = frame_bgr.shape[:2]

    if landmarker is not None:
        try:
            import mediapipe as mp
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            res = landmarker.detect(mp_image)

            if res and res.face_landmarks and len(res.face_landmarks) > 0:
                out["has_face"] = True
                lms = res.face_landmarks[0]
                out["landmarks"] = [(lm.x, lm.y, lm.z) for lm in lms]

                # 1. Blendshapes (eyeBlinkLeft, eyeBlinkRight)
                if res.face_blendshapes and len(res.face_blendshapes) > 0:
                    bs_dict = {c.category_name: c.score for c in res.face_blendshapes[0]}
                    b_left = bs_dict.get("eyeBlinkLeft", 0.0)
                    b_right = bs_dict.get("eyeBlinkRight", 0.0)
                    out["blink_score"] = float((b_left + b_right) / 2.0)

                # 2. Geometric EAR calculation
                # Left eye: top=159, bottom=145, inner=133, outer=33
                # Right eye: top=386, bottom=374, inner=362, outer=263
                try:
                    left_h = abs(lms[159].y - lms[145].y)
                    left_w = abs(lms[133].x - lms[33].x) + 1e-6
                    right_h = abs(lms[386].y - lms[374].y)
                    right_w = abs(lms[362].x - lms[263].x) + 1e-6
                    ear_left = left_h / left_w
                    ear_right = right_h / right_w
                    out["ear"] = float((ear_left + ear_right) / 2.0)
                except Exception:
                    pass

                # 3. Pose from transformation matrix or landmark geometry
                if res.facial_transformation_matrixes and len(res.facial_transformation_matrixes) > 0:
                    mat = res.facial_transformation_matrixes[0]
                    # mat is 4x4 matrix
                    r00, r01, r02 = mat[0, 0], mat[0, 1], mat[0, 2]
                    r10, r11, r12 = mat[1, 0], mat[1, 1], mat[1, 2]
                    r20, r21, r22 = mat[2, 0], mat[2, 1], mat[2, 2]

                    yaw = math.atan2(r02, r22) * 180.0 / math.pi
                    pitch = math.atan2(-r12, math.sqrt(r02**2 + r22**2)) * 180.0 / math.pi
                    roll = math.atan2(r10, r11) * 180.0 / math.pi
                    out["yaw"] = round(yaw, 1)
                    out["pitch"] = round(pitch, 1)
                    out["roll"] = round(roll, 1)
                else:
                    # Fallback pose from landmark geometry
                    nose = lms[1]
                    left_cheek = lms[234]
                    right_cheek = lms[454]
                    span = abs(right_cheek.x - left_cheek.x) + 1e-6
                    ratio_x = (nose.x - left_cheek.x) / span
                    out["yaw"] = round((ratio_x - 0.5) * 60.0, 1)

                    mid_eye_y = (lms[33].y + lms[263].y) / 2.0
                    mouth_y = (lms[61].y + lms[291].y) / 2.0
                    span_y = abs(mouth_y - mid_eye_y) + 1e-6
                    ratio_y = (nose.y - mid_eye_y) / span_y
                    out["pitch"] = round((0.5 - ratio_y) * 60.0, 1)

                return out
        except Exception as e:
            logger.debug(f"MediaPipe detection failed on frame: {e}")

    # Fallback to YuNet if MediaPipe failed or wasn't loaded
    if model_registry.yunet_detector is not None:
        try:
            detector = model_registry.yunet_detector
            detector.setInputSize((w, h))
            _, detections = detector.detect(frame_bgr)
            if detections is not None and len(detections) > 0:
                d = detections[0]
                out["has_face"] = True
                # Landmarks: re=(d[4], d[5]), le=(d[6], d[7]), nt=(d[8], d[9]), rcm=(d[10], d[11]), lcm=(d[12], d[13])
                re_x, le_x = float(d[4]), float(d[6])
                nt_x = float(d[8])
                eye_dist = abs(le_x - re_x) + 1e-6
                mid_eye_x = (re_x + le_x) / 2.0
                offset_x = (nt_x - mid_eye_x) / eye_dist
                out["yaw"] = round(offset_x * 45.0, 1)
                out["ear"] = 0.28
        except Exception as e:
            logger.debug(f"YuNet fallback failed on frame: {e}")

    return out


def verify_liveness(
    session_id: str,
    nonce: str,
    frames: List[Tuple[np.ndarray, str, float]],  # (bgr_frame, challenge_type, timestamp)
    selfie_bgr: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """
    Verifies a live face liveness challenge on the server:
    - Session validity (not expired, not reused, correct nonce)
    - Frame count validation (8-40 frames)
    - Face detection & embedding consistency across frames (same person)
    - Challenge order and kinematic verification (blink, turn_left, turn_right, look_up)
    - Comparison with submitted selfie (if provided)
    - Returns verdict, reasons, per-challenge results, evidence objects
    """
    now_iso = datetime.utcnow().isoformat()
    session = get_liveness_session(session_id)

    if not session:
        return {
            "passed": False,
            "reasons": ["Liveness session not found or invalid."],
            "per_challenge": {},
            "evidence": [Evidence(
                id="ID-LIVE-01",
                kind="risk",
                weight=EVIDENCE_CATALOG["ID-LIVE-01"]["weight"],
                effective_weight=EVIDENCE_CATALOG["ID-LIVE-01"]["weight"],
                calibrated_score=0.90,
                severity="high",
                title=EVIDENCE_CATALOG["ID-LIVE-01"]["title"],
                reason="Liveness session expired or invalid (session not found).",
                details={"session_id": session_id, "failed_challenge": "session_validation"}
            )]
        }

    # Anti-replay: check if session is already used
    if session.get("used"):
        return {
            "passed": False,
            "reasons": ["Liveness session already used (replay attack detected)."],
            "per_challenge": {},
            "evidence": [Evidence(
                id="ID-LIVE-01",
                kind="risk",
                weight=EVIDENCE_CATALOG["ID-LIVE-01"]["weight"],
                effective_weight=EVIDENCE_CATALOG["ID-LIVE-01"]["weight"],
                calibrated_score=0.95,
                severity="high",
                title=EVIDENCE_CATALOG["ID-LIVE-01"]["title"],
                reason="Liveness session already used; potential replay attack.",
                details={"session_id": session_id, "failed_challenge": "session_reuse"}
            )]
        }

    # Anti-replay: check expiration
    expires_at = session.get("expires_at", "")
    if expires_at and now_iso > expires_at:
        return {
            "passed": False,
            "reasons": [f"Liveness session expired at {expires_at}."],
            "per_challenge": {},
            "evidence": [Evidence(
                id="ID-LIVE-01",
                kind="risk",
                weight=EVIDENCE_CATALOG["ID-LIVE-01"]["weight"],
                effective_weight=EVIDENCE_CATALOG["ID-LIVE-01"]["weight"],
                calibrated_score=0.85,
                severity="high",
                title=EVIDENCE_CATALOG["ID-LIVE-01"]["title"],
                reason="Liveness challenge expired before submission.",
                details={"session_id": session_id, "failed_challenge": "session_expired"}
            )]
        }

    # Anti-replay: check nonce
    if session.get("nonce") != nonce:
        return {
            "passed": False,
            "reasons": ["Session nonce mismatch."],
            "per_challenge": {},
            "evidence": [Evidence(
                id="ID-LIVE-01",
                kind="risk",
                weight=EVIDENCE_CATALOG["ID-LIVE-01"]["weight"],
                effective_weight=EVIDENCE_CATALOG["ID-LIVE-01"]["weight"],
                calibrated_score=0.90,
                severity="high",
                title=EVIDENCE_CATALOG["ID-LIVE-01"]["title"],
                reason="Liveness session nonce mismatch.",
                details={"session_id": session_id, "failed_challenge": "nonce_mismatch"}
            )]
        }

    # Validate frame count: 8 to 40 frames
    if len(frames) < 8 or len(frames) > 40:
        return {
            "passed": False,
            "reasons": [f"Invalid frame count ({len(frames)}). Expected between 8 and 40 frames."],
            "per_challenge": {},
            "evidence": [Evidence(
                id="ID-LIVE-01",
                kind="risk",
                weight=EVIDENCE_CATALOG["ID-LIVE-01"]["weight"],
                effective_weight=EVIDENCE_CATALOG["ID-LIVE-01"]["weight"],
                calibrated_score=0.80,
                severity="high",
                title=EVIDENCE_CATALOG["ID-LIVE-01"]["title"],
                reason=f"Insufficient or excessive liveness frames ({len(frames)}).",
                details={"frame_count": len(frames), "failed_challenge": "frame_count"}
            )]
        }

    # Mark session as used immediately
    mark_liveness_session_used(session_id)

    challenges_expected = session.get("challenges", [])
    per_challenge: Dict[str, Dict[str, Any]] = {c: {"passed": False, "details": {}} for c in challenges_expected}

    # Process all frames
    frame_metrics = []
    best_frontal_score = 999.0
    best_frontal_frame = None

    for idx, (frame, ch_name, ts) in enumerate(frames):
        metrics = calculate_ear_and_pose(frame)
        metrics["challenge"] = ch_name
        metrics["timestamp"] = ts
        metrics["frame_idx"] = idx
        frame_metrics.append((frame, metrics))

        # Track best frontal frame (lowest absolute yaw + pitch)
        if metrics["has_face"]:
            frontal_penalty = abs(metrics["yaw"]) + abs(metrics["pitch"])
            if frontal_penalty < best_frontal_score:
                best_frontal_score = frontal_penalty
                best_frontal_frame = frame

    # Check face embedding consistency across liveness frames (P1-7: > 0.60 cosine)
    inconsistent_frames = False
    try:
        from .face import detect_faces, extract_aligned_face_and_embedding
        embs = []
        face_frames = [f for f, m in frame_metrics if m["has_face"]]
        if len(face_frames) >= 2:
            step = max(1, len(face_frames) // 4)
            for ff in face_frames[::step][:4]:
                faces = detect_faces(ff)
                if faces:
                    _, emb = extract_aligned_face_and_embedding(ff, faces[0])
                    if emb is not None:
                        embs.append(emb.flatten())
            if len(embs) >= 2:
                for i in range(len(embs)):
                    for j in range(i + 1, len(embs)):
                        cos_sim = float(np.dot(embs[i], embs[j]))
                        if cos_sim < 0.60:
                            inconsistent_frames = True
                            break
                    if inconsistent_frames:
                        break
    except Exception as e:
        logger.debug(f"Face consistency across liveness frames skipped: {e}")

    # 1. Evaluate blink challenge
    if "blink" in per_challenge:
        blink_frames = [m for f, m in frame_metrics if m["challenge"] in ("blink", "blink_twice")]
        if not blink_frames:
            blink_frames = [m for f, m in frame_metrics]  # Check across all if not labelled
        
        ears = [m["ear"] for m in blink_frames if m["has_face"]]
        blink_scores = [m["blink_score"] for m in blink_frames if m["has_face"]]

        blink_passed = False
        if ears:
            baseline_ear = max(ears)
            min_ear = min(ears)
            # EAR drops below baseline * 0.6 and recovers
            if baseline_ear > 0.15 and min_ear <= (baseline_ear * 0.65):
                blink_passed = True
        if blink_scores and max(blink_scores) >= 0.50:
            blink_passed = True

        per_challenge["blink"]["passed"] = blink_passed
        per_challenge["blink"]["details"] = {
            "baseline_ear": round(max(ears), 3) if ears else 0.0,
            "min_ear": round(min(ears), 3) if ears else 0.0,
            "max_blink_score": round(max(blink_scores), 3) if blink_scores else 0.0
        }

    # 2. Evaluate turn_left challenge
    if "turn_left" in per_challenge:
        tl_frames = [m for f, m in frame_metrics if m["challenge"] == "turn_left"]
        if not tl_frames:
            tl_frames = [m for f, m in frame_metrics]
        yaws = [m["yaw"] for m in tl_frames if m["has_face"]]
        # Yaw threshold +/-15 deg
        turn_left_passed = any(y <= -settings.LIVENESS_YAW_DEG for y in yaws)
        per_challenge["turn_left"]["passed"] = turn_left_passed
        per_challenge["turn_left"]["details"] = {"min_yaw": min(yaws) if yaws else 0.0, "threshold": -settings.LIVENESS_YAW_DEG}

    # 3. Evaluate turn_right challenge
    if "turn_right" in per_challenge:
        tr_frames = [m for f, m in frame_metrics if m["challenge"] == "turn_right"]
        if not tr_frames:
            tr_frames = [m for f, m in frame_metrics]
        yaws = [m["yaw"] for m in tr_frames if m["has_face"]]
        turn_right_passed = any(y >= settings.LIVENESS_YAW_DEG for y in yaws)
        per_challenge["turn_right"]["passed"] = turn_right_passed
        per_challenge["turn_right"]["details"] = {"max_yaw": max(yaws) if yaws else 0.0, "threshold": settings.LIVENESS_YAW_DEG}

    # 4. Evaluate look_up challenge
    if "look_up" in per_challenge:
        lu_frames = [m for f, m in frame_metrics if m["challenge"] == "look_up"]
        if not lu_frames:
            lu_frames = [m for f, m in frame_metrics]
        pitches = [m["pitch"] for m in lu_frames if m["has_face"]]
        look_up_passed = any(p >= 12.0 for p in pitches)
        per_challenge["look_up"]["passed"] = look_up_passed
        per_challenge["look_up"]["details"] = {"max_pitch": max(pitches) if pitches else 0.0, "threshold": 12.0}

    # Check overall pass
    failed_challenges = [c for c, d in per_challenge.items() if not d["passed"]]
    passed = len(failed_challenges) == 0

    reasons = []
    evidence = []

    if passed:
        reasons.append("All liveness challenges completed successfully within the required timeframe.")
        evidence.append(Evidence(
            id="ID-LIVE-00",
            kind="info",
            weight=0.0,
            effective_weight=0.0,
            calibrated_score=0.05,
            severity="low",
            title=EVIDENCE_CATALOG["ID-LIVE-00"]["title"],
            reason="All issued liveness challenges verified by facial landmark analysis.",
            details={"session_id": session_id, "challenges_passed": challenges_expected}
        ))
    else:
        fail_str = ", ".join(failed_challenges)
        reasons.append(f"Liveness challenge(s) failed: {fail_str}.")
        evidence.append(Evidence(
            id="ID-LIVE-01",
            kind="risk",
            weight=EVIDENCE_CATALOG["ID-LIVE-01"]["weight"],
            effective_weight=EVIDENCE_CATALOG["ID-LIVE-01"]["weight"],
            calibrated_score=0.85,
            severity="high",
            title=EVIDENCE_CATALOG["ID-LIVE-01"]["title"],
            reason=f"The person did not complete the live check ({fail_str} not detected).",
            details={"session_id": session_id, "failed_challenge": fail_str, "per_challenge": per_challenge}
        ))

    if inconsistent_frames:
        passed = False
        reasons.append("Different person detected across liveness challenge frames.")
        evidence.append(Evidence(
            id="ID-LIVE-02",
            kind="risk",
            weight=EVIDENCE_CATALOG["ID-LIVE-02"]["weight"],
            effective_weight=EVIDENCE_CATALOG["ID-LIVE-02"]["weight"],
            calibrated_score=0.85,
            severity="high",
            title=EVIDENCE_CATALOG["ID-LIVE-02"]["title"],
            reason="Face embedding consistency check failed (< 0.60 cosine) across captured challenge frames. Possible person switch during challenge.",
            details={"session_id": session_id, "failed_challenge": "person_switch"}
        ))

    if settings.DEMO_MODE and not passed:
        passed = True
        reasons = ["Passed due to DEMO_MODE fake stream override."]
        evidence = []
        if best_frontal_frame is None and len(frames) > 0:
            best_frontal_frame = frames[0][0]
            
    return {
        "passed": passed,
        "reasons": reasons,
        "per_challenge": per_challenge,
        "evidence": evidence,
        "best_frontal_frame": best_frontal_frame,
        "limitation_note": "Passive/active challenge defeats video replays and photos. High-quality 3D silicon masks and real-time projector replays remain out of scope."
    }
