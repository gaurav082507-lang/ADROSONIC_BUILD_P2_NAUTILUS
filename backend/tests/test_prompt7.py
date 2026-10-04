import os
import json
import time
import pytest
import cv2
import numpy as np
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.auth import create_access_token
from backend.app.db.database import get_connection
from backend.app.db.repository import (
    create_liveness_session,
    get_liveness_session,
    mark_liveness_session_used,
)
from backend.app.detectors.identity.face import analyze_faces
from backend.app.detectors.identity.liveness import verify_liveness
from backend.app.detectors.identity.aadhaar_qr import analyze_aadhaar_qr
from backend.app.scoring.overrides import apply_overrides_with_entries
from backend.app.scoring.overall import compute_overall_score

_token = create_access_token({"sub": "user_investigator", "role": "investigator"})
client = TestClient(app, headers={"Authorization": f"Bearer {_token}"})

DEMO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/demo_samples/identity"))


# ══════════════════════════════════════════════════════
# 1. FACE ENGINE & MATCHING TESTS
# ══════════════════════════════════════════════════════

def test_face_match_same_person():
    id_p = os.path.join(DEMO_DIR, "id_photo.jpg")
    selfie_p = os.path.join(DEMO_DIR, "matching_selfie.jpg")
    assert os.path.exists(id_p), f"Missing {id_p}"
    assert os.path.exists(selfie_p), f"Missing {selfie_p}"

    img_id = cv2.imread(id_p)
    img_selfie = cv2.imread(selfie_p)

    res = analyze_faces(img_id, img_selfie)
    assert res["status"] == "ok"
    assert res["verdict"] == "MATCH"
    assert res["similarity"] is not None
    assert res["similarity"] >= 0.35

    ev_ids = [e.id for e in res["evidence"]]
    assert "ID-FACE-00" in ev_ids
    assert "ID-FACE-01" not in ev_ids


def test_face_mismatch_different_person():
    id_p = os.path.join(DEMO_DIR, "id_photo.jpg")
    selfie_p = os.path.join(DEMO_DIR, "mismatch_selfie.jpg")
    assert os.path.exists(id_p), f"Missing {id_p}"
    assert os.path.exists(selfie_p), f"Missing {selfie_p}"

    img_id = cv2.imread(id_p)
    img_selfie = cv2.imread(selfie_p)

    res = analyze_faces(img_id, img_selfie)
    assert res["status"] == "ok"
    assert res["verdict"] in ("MISMATCH", "AMBIGUOUS")
    assert res["similarity"] is not None
    assert res["similarity"] < 0.40

    ev_ids = [e.id for e in res["evidence"]]
    assert any(ev_id in ("ID-FACE-01", "ID-FACE-02") for ev_id in ev_ids)
    assert "ID-FACE-00" not in ev_ids


def test_face_no_face_reports_skipped():
    blank = np.zeros((300, 300, 3), dtype=np.uint8)
    id_p = os.path.join(DEMO_DIR, "id_photo.jpg")
    img_id = cv2.imread(id_p)

    res = analyze_faces(img_id, blank)
    assert res["status"] == "skipped"
    assert res["verdict"] in ("NO_FACE_ON_SELFIE", "NO_FACE_ON_ID")

    ev_ids = [e.id for e in res["evidence"]]
    assert "ID-QUAL-01" in ev_ids
    assert "ID-FACE-01" not in ev_ids  # Never mismatch on quality failure


# ══════════════════════════════════════════════════════
# 2. SERVER-VERIFIED LIVENESS TESTS
# ══════════════════════════════════════════════════════

def test_liveness_session_issue_and_anti_replay():
    # 1. Issue session
    resp = client.post("/api/v1/identity/liveness/session")
    assert resp.status_code == 200
    sess = resp.json()

    assert "session_id" in sess
    assert "nonce" in sess
    assert len(sess["challenges"]) == 3
    assert "expires_at" in sess
    session_id = sess["session_id"]
    nonce = sess["nonce"]

    # 2. Check session in DB
    db_sess = get_liveness_session(session_id)
    assert db_sess is not None
    assert db_sess["used"] == 0

    # 3. Simulate frames
    selfie_p = os.path.join(DEMO_DIR, "matching_selfie.jpg")
    selfie_bgr = cv2.imread(selfie_p)
    _, buf = cv2.imencode(".jpg", selfie_bgr)
    frame_bytes = buf.tobytes()

    frames = [("frames", (f"f_{i}.jpg", frame_bytes, "image/jpeg")) for i in range(12)]
    meta = json.dumps({f"f_{i}.jpg": {"challenge": sess["challenges"][i // 4], "timestamp": i * 0.15} for i in range(12)})

    v_resp = client.post(
        "/api/v1/identity/liveness/verify",
        data={"session_id": session_id, "nonce": nonce, "frame_metadata": meta},
        files=frames
    )
    assert v_resp.status_code == 200
    v_data = v_resp.json()
    assert "passed" in v_data
    assert "per_challenge" in v_data

    # 4. Anti-replay: second verification must fail/reject session already used
    reused_resp = client.post(
        "/api/v1/identity/liveness/verify",
        data={"session_id": session_id, "nonce": nonce, "frame_metadata": meta},
        files=frames
    )
    reused_data = reused_resp.json()
    assert reused_data["passed"] is False
    assert any("already used" in r for r in reused_data["reasons"])


def test_liveness_expired_session():
    # Create expired session directly
    sess_id = f"exp_{int(time.time())}"
    nonce = "testnonce"
    expires_past = (datetime.utcnow() - timedelta(seconds=10)).isoformat()
    create_liveness_session(sess_id, nonce, ["blink", "turn_left", "turn_right"], "1234", expires_past)

    selfie_p = os.path.join(DEMO_DIR, "matching_selfie.jpg")
    selfie_bgr = cv2.imread(selfie_p)
    _, buf = cv2.imencode(".jpg", selfie_bgr)
    frame_bytes = buf.tobytes()

    frames = [("frames", (f"f_{i}.jpg", frame_bytes, "image/jpeg")) for i in range(10)]

    resp = client.post(
        "/api/v1/identity/liveness/verify",
        data={"session_id": sess_id, "nonce": nonce},
        files=frames
    )
    data = resp.json()
    assert data["passed"] is False
    assert any("expired" in r for r in data["reasons"])


# ══════════════════════════════════════════════════════
# 3. AADHAAR SECURE QR FORENSICS TESTS
# ══════════════════════════════════════════════════════

def test_aadhaar_qr_valid_card():
    valid_card_p = os.path.join(DEMO_DIR, "01_valid_aadhaar_card.png")
    assert os.path.exists(valid_card_p)
    card_bgr = cv2.imread(valid_card_p)

    res = analyze_aadhaar_qr(card_bgr)
    assert res["has_qr"] is True
    assert res["is_secure_qr"] is True
    assert res["signature_valid"] is True
    assert len(res["mismatches"]) == 0

    ev_ids = [e.id for e in res["evidence"]]
    assert "ID-QR-00" in ev_ids
    assert "ID-QR-01" not in ev_ids
    assert "ID-QR-02" not in ev_ids


def test_aadhaar_qr_tampered_printed_details():
    tampered_card_p = os.path.join(DEMO_DIR, "02_tampered_printed_aadhaar.png")
    assert os.path.exists(tampered_card_p)
    card_bgr = cv2.imread(tampered_card_p)

    res = analyze_aadhaar_qr(card_bgr)
    assert res["has_qr"] is True
    assert res["signature_valid"] is True  # Cryptographic signature is valid
    assert any(m["field"].lower() == "name" for m in res["mismatches"])

    ev_ids = [e.id for e in res["evidence"]]
    assert "ID-QR-02" in ev_ids


def test_aadhaar_qr_corrupted_signature():
    corrupted_card_p = os.path.join(DEMO_DIR, "03_invalid_signature_aadhaar.png")
    assert os.path.exists(corrupted_card_p)
    card_bgr = cv2.imread(corrupted_card_p)

    res = analyze_aadhaar_qr(card_bgr)
    assert res["has_qr"] is True
    assert res["signature_valid"] is False

    ev_ids = [e.id for e in res["evidence"]]
    assert "ID-QR-01" in ev_ids


def test_aadhaar_qr_document_without_qr():
    blank = np.ones((500, 500, 3), dtype=np.uint8) * 240
    res = analyze_aadhaar_qr(blank)
    assert res["has_qr"] is False

    ev_ids = [e.id for e in res["evidence"]]
    assert "ID-QR-04" in ev_ids


# ══════════════════════════════════════════════════════
# 4. DECISIVE OVERRIDES (O3, O6, O7)
# ══════════════════════════════════════════════════════

def test_decisive_overrides_o3_o6_o7():
    # O3: ID-FACE-01 floors risk at 0.80
    r_o3, app_o3 = apply_overrides_with_entries(["ID-FACE-01"], 0.15, "identity")
    assert r_o3 >= 0.80
    assert any(entry["rule"] == "O3" for entry in app_o3)

    # O6: ID-LIVE-01 and ID-FACE-01 floors risk at 0.85 in overall
    r_o6, app_o6 = apply_overrides_with_entries(["ID-LIVE-01", "ID-FACE-01"], 0.20, "overall")
    assert r_o6 >= 0.85
    assert any(entry["rule"] == "O6" for entry in app_o6)

    # O7: ID-QR-01 floors risk at 0.85
    r_o7, app_o7 = apply_overrides_with_entries(["ID-QR-01"], 0.10, "identity")
    assert r_o7 >= 0.85
    assert any(entry["rule"] == "O7" for entry in app_o7)


# ══════════════════════════════════════════════════════
# 5. CLAIM MODE PIPELINE BLENDING & INTEGRATION
# ══════════════════════════════════════════════════════

def test_claim_mode_identity_blending_and_artifacts():
    # Create claim with image + id_photo + selfie
    id_p = os.path.join(DEMO_DIR, "id_photo.jpg")
    selfie_p = os.path.join(DEMO_DIR, "matching_selfie.jpg")
    assert os.path.exists(id_p) and os.path.exists(selfie_p)

    token = create_access_token({"sub": "user_investigator", "role": "investigator"})
    headers = {"Authorization": f"Bearer {token}"}

    with open(id_p, "rb") as f_id, open(selfie_p, "rb") as f_selfie:
        files = [
            ("image", ("car_damage.jpg", f_id.read(), "image/jpeg")),
        ]
        f_id.seek(0)
        files.append(("id_photo", ("my_id.jpg", f_id.read(), "image/jpeg")))
        files.append(("selfie", ("my_selfie.jpg", f_selfie.read(), "image/jpeg")))

    from backend.app.core.rate_limit import _REQUEST_TIMESTAMPS
    _REQUEST_TIMESTAMPS.clear()

    resp = client.post("/api/v1/analyze/claim", files=files, headers=headers)
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    for _ in range(60):
        j_resp = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert j_resp.status_code == 200
        j_data = j_resp.json()
        if j_data["status"] in ("done", "failed"):
            break
        time.sleep(0.05)

    assert j_data["status"] == "done"
    res_id = j_data["result_id"]

    res_resp = client.get(f"/api/v1/results/{res_id}", headers=headers)
    assert res_resp.status_code == 200
    res = res_resp.json()

    # Identity pipeline must have participated
    assert res["identity"] is not None
    assert "risk" in res["identity"]
    assert "authenticity" in res["identity"]

    # Verify §15.5 blending: Overall risk accounts for all active pipelines
    why_overall = res["why_this_score"]["overall"]
    assert "identity" in why_overall["pipeline_risks"]
    assert "image" in why_overall["pipeline_risks"]

    # Verify side-by-side artifact was created
    assert "identity_face_comparison" in res["artifacts"]


# ══════════════════════════════════════════════════════
# 6. UIDAI PRIVACY COMPLIANCE (§20)
# ══════════════════════════════════════════════════════

def test_privacy_no_raw_qr_or_aadhaar_in_database():
    conn = get_connection()
    c = conn.cursor()

    # Query all results and evidence json
    rows = c.execute("SELECT json FROM results").fetchall()
    for row in rows:
        content = row[0] or ""
        # Assert no 12-digit continuous numeric sequence (Aadhaar number)
        import re
        content_no_uuids = re.sub(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", "", content)
        aadhaar_matches = re.findall(r"\b\d{12}\b", content_no_uuids)
        assert len(aadhaar_matches) == 0, f"Found raw 12-digit Aadhaar in database result: {aadhaar_matches}"

    conn.close()
