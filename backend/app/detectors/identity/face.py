import os
import json
import logging
import cv2
import numpy as np
from PIL import Image
from typing import Dict, Any, List, Optional, Tuple

from ...core.config import settings
from ...core.model_registry import model_registry
from ...schemas.evidence import Evidence, BBox
from ...scoring.weights import EVIDENCE_CATALOG

logger = logging.getLogger("lucen_ai.identity.face")

CALIBRATION_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../models/calibration.json")
)

def get_face_thresholds(engine: str = "sface") -> Tuple[float, float, str]:
    """Loads (t_low, t_high, source) from calibration.json for the specified engine."""
    default_t_low = 0.30
    default_t_high = 0.40 if engine == "sface" else 0.45
    source = "published operating point"

    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                engine_data = data.get("face_match", {}).get(engine, {})
                t_low = float(engine_data.get("t_low", default_t_low))
                t_high = float(engine_data.get("t_high", default_t_high))
                src = engine_data.get("source", source)
                return t_low, t_high, src
        except Exception as e:
            logger.warning(f"Could not read calibration.json: {e}")

    return default_t_low, default_t_high, source

def detect_faces(image_bgr: np.ndarray, engine: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Detects faces in BGR image.
    Returns list of dicts sorted by bounding box area (largest first).
    Each dict contains:
      - bbox: [x, y, w, h] (pixels)
      - norm_bbox: [x/w, y/h, w/w, h/h] (0..1)
      - score: float
      - landmarks: list of (x, y) 5 landmarks
      - raw_data: engine-specific detection object
    """
    active_engine = engine or settings.FACE_ENGINE
    if model_registry.arcface_app is None and model_registry.yunet_detector is None:
        model_registry.load_face_engine()
    h, w = image_bgr.shape[:2]
    faces_out = []

    if active_engine == "arcface" and model_registry.arcface_app is not None:
        try:
            raw_faces = model_registry.arcface_app.get(image_bgr)
            for f in raw_faces:
                bx = f.bbox.astype(int)
                x1, y1, x2, y2 = max(0, bx[0]), max(0, bx[1]), min(w, bx[2]), min(h, bx[3])
                fw, fh = x2 - x1, y2 - y1
                if fw <= 0 or fh <= 0:
                    continue
                kps = f.kps.tolist() if hasattr(f, "kps") else []
                emb = f.embedding
                if emb is not None:
                    norm = np.linalg.norm(emb)
                    if norm > 1e-6:
                        emb = emb / norm
                faces_out.append({
                    "bbox": [x1, y1, fw, fh],
                    "norm_bbox": [x1 / w, y1 / h, fw / w, fh / h],
                    "score": float(f.det_score) if hasattr(f, "det_score") else 0.9,
                    "landmarks": kps,
                    "embedding": emb,
                    "raw_data": f,
                    "engine": "arcface"
                })
        except Exception as e:
            logger.error(f"ArcFace detection failed: {e}")

    # Fallback or default to SFace (YuNet)
    if not faces_out and model_registry.yunet_detector is not None:
        try:
            detector = model_registry.yunet_detector
            detector.setInputSize((w, h))
            _, detections = detector.detect(image_bgr)
            if detections is not None:
                for d in detections:
                    score = float(d[-1])
                    if score < 0.4:
                        continue
                    x, y, fw, fh = int(d[0]), int(d[1]), int(d[2]), int(d[3])
                    x = max(0, min(w - 1, x))
                    y = max(0, min(h - 1, y))
                    fw = max(1, min(w - x, fw))
                    fh = max(1, min(h - y, fh))
                    # 5 landmarks in YuNet: right eye, left eye, nose tip, right mouth corner, left mouth corner
                    landmarks = [
                        (float(d[4]), float(d[5])),
                        (float(d[6]), float(d[7])),
                        (float(d[8]), float(d[9])),
                        (float(d[10]), float(d[11])),
                        (float(d[12]), float(d[13]))
                    ]
                    faces_out.append({
                        "bbox": [x, y, fw, fh],
                        "norm_bbox": [x / w, y / h, fw / w, fh / h],
                        "score": score,
                        "landmarks": landmarks,
                        "raw_data": d,
                        "engine": "sface"
                    })
        except Exception as e:
            logger.error(f"YuNet detection failed: {e}")

    # Sort largest face first
    faces_out.sort(key=lambda item: item["bbox"][2] * item["bbox"][3], reverse=True)
    return faces_out

def extract_aligned_face_and_embedding(
    image_bgr: np.ndarray,
    face_info: Dict[str, Any],
    engine: Optional[str] = None
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Extracts aligned face crop (112x112) and L2-normalized embedding.
    Returns (aligned_face_bgr, embedding).
    """
    active_engine = face_info.get("engine") or engine or settings.FACE_ENGINE
    if model_registry.arcface_app is None and model_registry.sface_recognizer is None:
        model_registry.load_face_engine()
    aligned_face = None
    embedding = None

    if active_engine == "arcface":
        if "embedding" in face_info and face_info["embedding"] is not None:
            embedding = face_info["embedding"]
        elif "raw_data" in face_info and hasattr(face_info["raw_data"], "normed_embedding"):
            embedding = face_info["raw_data"].normed_embedding
        # Crop face from bbox
        x, y, fw, fh = face_info["bbox"]
        h_img, w_img = image_bgr.shape[:2]
        crop = image_bgr[max(0, y):min(h_img, y + fh), max(0, x):min(w_img, x + fw)]
        if crop.size > 0:
            aligned_face = cv2.resize(crop, (112, 112))
        return aligned_face, embedding

    # SFace
    if model_registry.sface_recognizer is not None and "raw_data" in face_info:
        try:
            recognizer = model_registry.sface_recognizer
            raw_d = face_info["raw_data"]
            aligned = recognizer.alignCrop(image_bgr, raw_d)
            aligned_face = aligned
            feat = recognizer.feature(aligned)
            feat = feat.flatten()
            norm = np.linalg.norm(feat)
            if norm > 1e-6:
                embedding = (feat / norm).astype(np.float32)
        except Exception as e:
            logger.error(f"SFace alignment and feature extraction failed: {e}")

    return aligned_face, embedding

def compute_face_quality(face_crop_bgr: np.ndarray, face_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes size, blur (Laplacian variance), and brightness on face crop.
    """
    fw, fh = face_info["bbox"][2], face_info["bbox"][3]
    size_ok = (fw >= 60 and fh >= 60)
    
    if face_crop_bgr is None or face_crop_bgr.size == 0:
        return {"size_ok": False, "blur_var": 0.0, "sharp_ok": False, "brightness": 0.0, "is_good": False}

    gray = cv2.cvtColor(face_crop_bgr, cv2.COLOR_BGR2GRAY)
    blur_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(np.mean(gray))

    sharp_ok = blur_var >= 40.0
    bright_ok = 35.0 <= brightness <= 225.0
    is_good = bool(size_ok and sharp_ok and bright_ok)

    return {
        "width": fw,
        "height": fh,
        "size_ok": size_ok,
        "blur_var": round(blur_var, 1),
        "sharp_ok": sharp_ok,
        "brightness": round(brightness, 1),
        "bright_ok": bright_ok,
        "is_good": is_good
    }

def check_selfie_ai(selfie_face_bgr: np.ndarray) -> Tuple[float, float]:
    """
    Runs SigLIP AI detector on the selfie face crop.
    Returns (raw_p_ai, calibrated_p_ai).
    """
    if selfie_face_bgr is None or selfie_face_bgr.size == 0:
        return 0.0, 0.0

    model = model_registry.ai_model
    processor = model_registry.ai_processor
    ai_idx = model_registry.ai_class_idx

    if model is None or processor is None:
        return 0.0, 0.0

    try:
        rgb = cv2.cvtColor(selfie_face_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)

        inputs = processor(images=pil_img, return_tensors="pt")
        import torch
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits[0]
            probs = torch.softmax(logits, dim=-1)
            raw_p = float(probs[ai_idx].item())
            
            # Apply temperature scaling
            t = 1.0
            if os.path.exists(CALIBRATION_FILE):
                try:
                    with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
                        cdata = json.load(f)
                        t = float(cdata.get("temperature", {}).get("ai_detector", 1.0))
                except Exception:
                    pass
            cal_logits = logits / t
            cal_probs = torch.softmax(cal_logits, dim=-1)
            cal_p = float(cal_probs[ai_idx].item())
            return raw_p, cal_p
    except Exception as e:
        logger.error(f"Selfie AI check failed: {e}")
        return 0.0, 0.0

def analyze_faces(
    id_photo_bgr: Optional[np.ndarray],
    selfie_bgr: Optional[np.ndarray],
    engine: Optional[str] = None
) -> Dict[str, Any]:
    """
    Performs full identity face analysis between ID card and live selfie:
    - Detects faces in both images
    - Quality checks
    - Cosine similarity matching
    - Selfie deepfake check
    - Emits evidence objects
    """
    active_engine = engine or settings.FACE_ENGINE
    t_low, t_high, source = get_face_thresholds(active_engine)
    evidence: List[Evidence] = []
    
    result = {
        "status": "ok",
        "evidence": evidence,
        "engine": active_engine,
        "id_face": None,
        "selfie_face": None,
        "similarity": None,
        "verdict": None,
        "id_face_crop": None,
        "selfie_face_crop": None,
        "details": {}
    }

    if id_photo_bgr is None or selfie_bgr is None:
        result["status"] = "skipped"
        result["verdict"] = "SKIPPED"
        return result

    # 1. Detect faces in ID photo
    id_faces = detect_faces(id_photo_bgr, active_engine)
    if not id_faces:
        evidence.append(Evidence(
            id="ID-QUAL-01",
            kind="warning",
            weight=0.0,
            effective_weight=0.0,
            calibrated_score=0.5,
            severity="low",
            title=EVIDENCE_CATALOG["ID-QUAL-01"]["title"],
            reason="No usable face detected on the ID document.",
            details={"location": "id_photo", "faces_found": 0}
        ))
        result["status"] = "skipped"
        result["verdict"] = "NO_FACE_ON_ID"
        return result

    # 2. Detect faces in selfie
    selfie_faces = detect_faces(selfie_bgr, active_engine)
    if not selfie_faces:
        evidence.append(Evidence(
            id="ID-QUAL-01",
            kind="warning",
            weight=0.0,
            effective_weight=0.0,
            calibrated_score=0.5,
            severity="low",
            title=EVIDENCE_CATALOG["ID-QUAL-01"]["title"],
            reason="No usable face detected in the selfie image.",
            details={"location": "selfie", "faces_found": 0}
        ))
        result["status"] = "skipped"
        result["verdict"] = "NO_FACE_ON_SELFIE"
        return result

    # Check for multiple faces
    if len(id_faces) > 1:
        evidence.append(Evidence(
            id="ID-QUAL-01",
            kind="warning",
            weight=0.0,
            effective_weight=0.0,
            calibrated_score=0.4,
            severity="low",
            title=EVIDENCE_CATALOG["ID-QUAL-01"]["title"],
            reason=f"Multiple faces ({len(id_faces)}) detected on ID photo; using the largest face.",
            details={"location": "id_photo", "face_count": len(id_faces)}
        ))

    # Take largest face on ID and selfie
    primary_id_face = id_faces[0]
    primary_selfie_face = selfie_faces[0]

    # Align & extract embeddings
    id_crop, id_emb = extract_aligned_face_and_embedding(id_photo_bgr, primary_id_face, active_engine)
    selfie_crop, selfie_emb = extract_aligned_face_and_embedding(selfie_bgr, primary_selfie_face, active_engine)

    result["id_face"] = primary_id_face["bbox"]
    result["selfie_face"] = primary_selfie_face["bbox"]
    result["id_face_crop"] = id_crop
    result["selfie_face_crop"] = selfie_crop

    # Quality check
    id_quality = compute_face_quality(id_crop, primary_id_face)
    selfie_quality = compute_face_quality(selfie_crop, primary_selfie_face)
    result["details"]["id_quality"] = id_quality
    result["details"]["selfie_quality"] = selfie_quality

    if id_emb is None or selfie_emb is None:
        evidence.append(Evidence(
            id="ID-QUAL-01",
            kind="warning",
            weight=0.0,
            effective_weight=0.0,
            calibrated_score=0.5,
            severity="low",
            title=EVIDENCE_CATALOG["ID-QUAL-01"]["title"],
            reason="Could not compute facial feature embedding from detected face.",
            details={"engine": active_engine}
        ))
        result["status"] = "skipped"
        result["verdict"] = "EMBEDDING_FAILED"
        return result

    # Compute cosine similarity
    sim = float(np.dot(id_emb.flatten(), selfie_emb.flatten()))
    sim = max(-1.0, min(1.0, sim))
    result["similarity"] = round(sim, 4)

    # Decision zones
    if sim >= t_high:
        verdict = "MATCH"
    elif sim >= t_low:
        verdict = "AMBIGUOUS"
    else:
        verdict = "MISMATCH"

    result["verdict"] = verdict
    result["details"]["thresholds"] = {"t_low": t_low, "t_high": t_high, "source": source}

    # Weight discounting if poor quality
    quality_discount = 1.0
    if not id_quality["is_good"] or not selfie_quality["is_good"]:
        quality_discount = 0.7

    if verdict == "MISMATCH":
        w = round(EVIDENCE_CATALOG["ID-FACE-01"]["weight"] * quality_discount, 2)
        evidence.append(Evidence(
            id="ID-FACE-01",
            kind="risk",
            weight=EVIDENCE_CATALOG["ID-FACE-01"]["weight"],
            effective_weight=w,
            calibrated_score=0.90,
            severity="high",
            title=EVIDENCE_CATALOG["ID-FACE-01"]["title"],
            reason=f"The face on the ID does not match the selfie (similarity {sim:.2f}, below threshold {t_low:.2f}).",
            field="face_match",
            bbox=BBox(page=1, x=primary_id_face["norm_bbox"][0], y=primary_id_face["norm_bbox"][1], w=primary_id_face["norm_bbox"][2], h=primary_id_face["norm_bbox"][3]),
            details={"sim": round(sim, 4), "t_low": t_low, "engine": active_engine, "verdict": "mismatch"}
        ))
    elif verdict == "AMBIGUOUS":
        w = round(EVIDENCE_CATALOG["ID-FACE-02"]["weight"] * quality_discount, 2)
        evidence.append(Evidence(
            id="ID-FACE-02",
            kind="risk",
            weight=EVIDENCE_CATALOG["ID-FACE-02"]["weight"],
            effective_weight=w,
            calibrated_score=0.55,
            severity="medium",
            title=EVIDENCE_CATALOG["ID-FACE-02"]["title"],
            reason=f"Face match is ambiguous between the ID and selfie (similarity {sim:.2f}); possible morph or low quality photo.",
            field="face_match",
            bbox=BBox(page=1, x=primary_id_face["norm_bbox"][0], y=primary_id_face["norm_bbox"][1], w=primary_id_face["norm_bbox"][2], h=primary_id_face["norm_bbox"][3]),
            details={"sim": round(sim, 4), "t_low": t_low, "t_high": t_high, "engine": active_engine, "verdict": "ambiguous"}
        ))
    else:
        # Match - info evidence
        evidence.append(Evidence(
            id="ID-FACE-00",
            kind="info",
            weight=0.0,
            effective_weight=0.0,
            calibrated_score=0.05,
            severity="low",
            title="Face Match Verified",
            reason=f"Face on ID matches selfie with similarity {sim:.2f} (above threshold {t_high:.2f}).",
            field="face_match",
            bbox=BBox(page=1, x=primary_id_face["norm_bbox"][0], y=primary_id_face["norm_bbox"][1], w=primary_id_face["norm_bbox"][2], h=primary_id_face["norm_bbox"][3]),
            details={"sim": round(sim, 4), "t_high": t_high, "engine": active_engine, "verdict": "match"}
        ))

    # 3. Selfie Deepfake / AI Check
    if selfie_crop is not None:
        raw_p_ai, cal_p_ai = check_selfie_ai(selfie_crop)
        result["details"]["selfie_ai"] = {"raw": raw_p_ai, "calibrated": cal_p_ai}
        if cal_p_ai >= 0.50:
            evidence.append(Evidence(
                id="ID-DEEP-01",
                kind="risk",
                weight=EVIDENCE_CATALOG["ID-DEEP-01"]["weight"],
                effective_weight=EVIDENCE_CATALOG["ID-DEEP-01"]["weight"],
                calibrated_score=cal_p_ai,
                severity="high" if cal_p_ai >= 0.65 else "medium",
                title=EVIDENCE_CATALOG["ID-DEEP-01"]["title"],
                reason=f"The selfie image appears to be AI-generated ({cal_p_ai:.0%} likelihood after calibration).",
                field="selfie_ai",
                bbox=BBox(page=1, x=primary_selfie_face["norm_bbox"][0], y=primary_selfie_face["norm_bbox"][1], w=primary_selfie_face["norm_bbox"][2], h=primary_selfie_face["norm_bbox"][3]),
                details={"p": round(cal_p_ai, 4), "raw_p": round(raw_p_ai, 4)}
            ))

    return result
