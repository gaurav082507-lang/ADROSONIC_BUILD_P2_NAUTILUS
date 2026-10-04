import json
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.auth import create_access_token
from backend.app.db.repository import (
    create_claim_record,
    update_claim_record,
    add_claim_evidence_item,
    add_action_record
)

client = TestClient(app)

FORBIDDEN_TERMS = [
    "risk", "band", "score", "confidence", "evidence_id",
    "img-", "doc-", "id-", "voice-", "clm-", "voi-",
    "heatmap", "ai_detector", "tamper", "fraud", "deepfake", "synthetic",
    "voice clone", "spoof", "cloned",
    "liveness", "face match", "morph", "signature", "aadhaar qr", "biometric",
    "duplicate", "gps", "timeline contradiction", "contradiction", "recycled", "cross-check",
    "network", "ring", "linked claims"
]

def scan_for_forbidden_terms(data, path=""):
    if isinstance(data, dict):
        for k, v in data.items():
            curr_path = f"{path}.{k}" if path else str(k)
            k_lower = str(k).lower()
            for term in FORBIDDEN_TERMS:
                assert term not in k_lower, f"Forbidden term '{term}' leaked in key: {curr_path}"
            scan_for_forbidden_terms(v, curr_path)
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            scan_for_forbidden_terms(item, f"{path}[{idx}]")
    elif isinstance(data, str):
        if path.endswith("claim_id") or path.endswith(".id"):
            return
        v_lower = data.lower()
        for term in FORBIDDEN_TERMS:
            assert term not in v_lower, f"Forbidden term '{term}' leaked in value at {path}: '{data}'"

def test_claimant_views_safety_across_bands():
    # Setup claims for user_ravi with LOW, MEDIUM, and HIGH backend states
    token = create_access_token({"sub": "user_ravi", "role": "claimant"})
    headers = {"Authorization": f"Bearer {token}"}

    test_claims = [
        {"id": "claim_low_01", "status": "approved", "msg": "Your claim has been accepted."},
        {"id": "claim_med_02", "status": "needs_evidence", "msg": "Please provide a clear invoice copy."},
        {"id": "claim_high_03", "status": "rejected", "msg": "The submitted repair invoice could not be verified."}
    ]

    for tc in test_claims:
        cid = tc["id"]
        create_claim_record({
            "id": cid,
            "claimant_user_id": "user_ravi",
            "policy_number": "POL-MOT-8821",
            "claimant_name": "Ravi Kumar",
            "claim_type": "motor",
            "peril": "collision",
            "incident_date": "2026-05-10",
            "claimed_amount": 15000.0,
            "status": tc["status"],
            "created_at": "2026-05-11T10:00:00",
            "updated_at": "2026-05-11T12:00:00"
        })
        add_claim_evidence_item({
            "claim_id": cid,
            "slot": "damage_closeup",
            "file_label": "bumper_photo.jpg",
            "file_path": f"/tmp/{cid}_bumper.jpg",
            "capture_source": "camera",
            "state": "checked" if tc["status"] == "approved" else "needs_replacing",
            "created_at": "2026-05-11T10:00:00",
            "updated_at": "2026-05-11T12:00:00"
        })
        add_action_record({
            "claim_id": cid,
            "actor": "Pooja Mehta",
            "action": "request_evidence" if tc["status"] == "needs_evidence" else ("reject" if tc["status"] == "rejected" else "approve"),
            "from_status": "under_review",
            "to_status": tc["status"],
            "reason_category": "document_needs_verification",
            "claimant_message": tc["msg"],
            "slots_to_resubmit_json": json.dumps(["repair_estimate"]),
            "created_at": "2026-05-11T12:00:00"
        })

    # 1. Test GET /claims/mine
    res = client.get("/api/v1/claims/mine", headers=headers)
    assert res.status_code == 200
    mine_data = res.json()
    scan_for_forbidden_terms(mine_data, "GET /claims/mine")

    # 2. Test GET /claims/{id}/status for all 3 claims
    for tc in test_claims:
        cid = tc["id"]
        status_res = client.get(f"/api/v1/claims/{cid}/status", headers=headers)
        assert status_res.status_code == 200
        status_json = status_res.json()
        scan_for_forbidden_terms(status_json, f"GET /claims/{cid}/status")

    # 3. Test GET /claims/{id}/evidence-timeline for all 3 claims
    for tc in test_claims:
        cid = tc["id"]
        ev_res = client.get(f"/api/v1/claims/{cid}/evidence-timeline", headers=headers)
        assert ev_res.status_code == 200
        ev_json = ev_res.json()
        scan_for_forbidden_terms(ev_json, f"GET /claims/{cid}/evidence-timeline")


def test_claimant_voice_transcribe_safety():
    token = create_access_token({"sub": "user_ravi", "role": "claimant"})
    headers = {"Authorization": f"Bearer {token}"}
    res = client.post(
        "/api/v1/voice/transcribe",
        data={"language": "en", "text": "I had a minor car accident yesterday near the signal. Broken front bumper."},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    scan_for_forbidden_terms(data, "POST /voice/transcribe")
    # Verify no spoof or risk score is returned in response
    assert "spoof" not in str(data).lower()
    assert "cloned" not in str(data).lower()
    assert "synthetic" not in str(data).lower()
    assert "risk" not in data
    assert "score" not in data

