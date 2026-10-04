import json
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.auth import create_access_token
from backend.app.core.decision_reasons import validate_draft_guardrails
from backend.app.db.repository import (
    create_claim_record,
    update_claim_record,
    get_claim_record,
    get_actions_for_claim_record,
    add_action_record
)

client = TestClient(app)

def test_auth_login_ok_and_bad_password():
    # OK login
    res = client.post("/api/v1/auth/login", json={"email": "ravi@demo.in", "password": "demo"})
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert data["user"]["email"] == "ravi@demo.in"
    assert data["user"]["role"] == "claimant"

    # Bad password
    res_bad = client.post("/api/v1/auth/login", json={"email": "ravi@demo.in", "password": "wrongpassword"})
    assert res_bad.status_code == 401
    err = res_bad.json()
    assert err["error"]["code"] == "NOT_AUTHENTICATED"

def test_role_guards():
    claimant_token = create_access_token({"sub": "user_ravi", "role": "claimant"})
    investigator_token = create_access_token({"sub": "user_investigator", "role": "investigator"})

    # 1. Unauthenticated request to /queue -> 401
    res = client.get("/api/v1/queue")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "NOT_AUTHENTICATED"

    # 2. Claimant accessing investigator route (/queue) -> 403
    res = client.get("/api/v1/queue", headers={"Authorization": f"Bearer {claimant_token}"})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN_ROLE"

    # 3. Investigator accessing /queue -> 200
    res = client.get("/api/v1/queue", headers={"Authorization": f"Bearer {investigator_token}"})
    assert res.status_code == 200

    # 4. Investigator accessing claimant route (/claims/mine) -> 403
    res = client.get("/api/v1/claims/mine", headers={"Authorization": f"Bearer {investigator_token}"})
    assert res.status_code == 403

def test_claimant_cannot_read_another_claimant_claim():
    # Create claim for Ravi
    cid = "claim_ravi_private"
    create_claim_record({
        "id": cid,
        "claimant_user_id": "user_ravi",
        "policy_number": "POL-MOT-8821",
        "claimant_name": "Ravi Kumar",
        "claim_type": "motor",
        "status": "under_review",
        "created_at": "2026-06-01T10:00:00"
    })

    # Sunita tries to access Ravi's claim
    sunita_token = create_access_token({"sub": "user_sunita", "role": "claimant"})
    res = client.get(f"/api/v1/claims/{cid}/status", headers={"Authorization": f"Bearer {sunita_token}"})
    # MUST BE 404, NEVER 403 (does not leak existence)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "CLAIM_NOT_FOUND"

def test_policy_invalid_and_consent_required():
    token = create_access_token({"sub": "user_ravi", "role": "claimant"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Consent false -> CONSENT_REQUIRED 422
    res = client.post(
        "/api/v1/claims",
        data={
            "policy_id": "POL-MOT-8821",
            "claim_type": "motor",
            "peril": "collision",
            "incident_date": "2026-06-15",
            "consent": "false"
        },
        headers=headers
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "CONSENT_REQUIRED"

    # 2. Expired incident date outside policy period (policy ends 2026-12-31) -> POLICY_INVALID 422
    res = client.post(
        "/api/v1/claims",
        data={
            "policy_id": "POL-MOT-8821",
            "claim_type": "motor",
            "peril": "collision",
            "incident_date": "2029-01-01",
            "consent": "true"
        },
        headers=headers
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "POLICY_INVALID"

    # 3. Policy belonging to Sunita submitted by Ravi -> POLICY_INVALID 422
    res = client.post(
        "/api/v1/claims",
        data={
            "policy_id": "POL-MOT-3319",
            "claim_type": "motor",
            "peril": "collision",
            "incident_date": "2026-06-15",
            "consent": "true"
        },
        headers=headers
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "POLICY_INVALID"

def test_draft_guardrails():
    # Allowed numbers
    allowed = {"2026", "05", "10", "15000", "8821"}

    # Clean message
    clean = "We could not verify the vehicle damage from the photos provided. Please upload clear photos taken in daylight."
    assert validate_draft_guardrails(clean, allowed) is True

    # Message with banned words
    assert validate_draft_guardrails("This photo appears to be fake and manipulated.", allowed) is False
    assert validate_draft_guardrails("AI-generated content detected by deepfake scanner.", allowed) is False
    assert validate_draft_guardrails("Score was 0.95 with HIGH risk.", allowed) is False
    assert validate_draft_guardrails("Tampered text found in repair estimate.", allowed) is False

    # Message with unallowed hallucinated number (e.g. 999999)
    assert validate_draft_guardrails("Your claim for 999999 is pending.", allowed) is False

def test_fast_track_allowed_and_blocked_and_undo():
    inv_token = create_access_token({"sub": "user_investigator", "role": "investigator"})
    headers = {"Authorization": f"Bearer {inv_token}"}

    # 1. High risk claim fast-track -> BLOCKED (422)
    cid_high = "claim_ft_high"
    create_claim_record({
        "id": cid_high,
        "claimant_user_id": "user_ravi",
        "policy_number": "POL-MOT-8821",
        "result_id": "mock_high_result",
        "status": "under_review"
    })
    res = client.post(f"/api/v1/claims/{cid_high}/fast-track", headers=headers)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "FAST_TRACK_NOT_ALLOWED"

    # Insert fake results for the test since MOCK_ANALYSIS is off
    import sqlite3
    from backend.app.core.config import settings
    import json
    with sqlite3.connect(settings.SQLITE_DB_PATH) as conn:
        conn.execute("INSERT OR REPLACE INTO results (id, overall_band, overall_risk, json, created_at) VALUES (?, ?, ?, ?, ?)",
            ("mock_high_result", "HIGH", 0.9, json.dumps({"overall": {"band": "HIGH"}}), "2026-01-01"))
        conn.execute("INSERT OR REPLACE INTO results (id, overall_band, overall_risk, json, created_at) VALUES (?, ?, ?, ?, ?)",
            ("mock_low_result", "LOW", 0.1, json.dumps({"overall": {"band": "LOW", "confidence": "high"}}), "2026-01-01"))
        conn.execute("INSERT OR REPLACE INTO results (id, overall_band, overall_risk, json, created_at) VALUES (?, ?, ?, ?, ?)",
            ("mock_high_result_flow", "HIGH", 0.9, json.dumps({"overall": {"band": "HIGH"}}), "2026-01-01"))

    # 1. High risk claim fast-track -> BLOCKED (422)
    cid_high = "claim_ft_high"
    create_claim_record({
        "id": cid_high,
        "claimant_user_id": "user_ravi",
        "policy_number": "POL-MOT-8821",
        "result_id": "mock_high_result",
        "status": "under_review"
    })
    res = client.post(f"/api/v1/claims/{cid_high}/fast-track", headers=headers)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "FAST_TRACK_NOT_ALLOWED"

    # 2. Low risk claim fast-track -> ALLOWED (200)
    cid_low = "claim_ft_low"
    create_claim_record({
        "id": cid_low,
        "claimant_user_id": "user_ravi",
        "policy_number": "POL-MOT-8821",
        "result_id": "mock_low_result",
        "status": "under_review"
    })
    res_ok = client.post(f"/api/v1/claims/{cid_low}/fast-track", headers=headers)
    assert res_ok.status_code == 200
    assert res_ok.json()["new_status"] == "approved"

    # 3. Undo fast-track -> RESTORED
    res_undo = client.post(f"/api/v1/claims/{cid_low}/fast-track/undo", headers=headers)
    assert res_undo.status_code == 200
    assert res_undo.json()["restored_status"] == "under_review"

def test_decision_and_resubmit_flow():
    inv_token = create_access_token({"sub": "user_investigator", "role": "investigator"})
    claimant_token = create_access_token({"sub": "user_ravi", "role": "claimant"})

    cid = "claim_decision_flow"
    create_claim_record({
        "id": cid,
        "claimant_user_id": "user_ravi",
        "policy_number": "POL-MOT-8821",
        "result_id": "mock_high_result_flow",
        "status": "under_review"
    })

    import sqlite3
    from backend.app.core.config import settings
    import json
    with sqlite3.connect(settings.SQLITE_DB_PATH) as conn:
        conn.execute("INSERT OR REPLACE INTO results (id, overall_band, overall_risk, json, created_at) VALUES (?, ?, ?, ?, ?)",
            ("mock_high_result_flow", "HIGH", 0.9, json.dumps({"overall": {"band": "HIGH"}}), "2026-01-01"))

    # 1. Investigator drafts decision
    draft_res = client.post(
        "/api/v1/results/mock_high_result_flow/decision/draft",
        json={"action": "request_evidence", "reason_category": "photo_unclear"},
        headers={"Authorization": f"Bearer {inv_token}"}
    )
    assert draft_res.status_code == 200
    draft_data = draft_res.json()
    assert "claimant_message_en" in draft_data
    assert "damage_closeup" in draft_data["slots_to_resubmit"]

    # 2. Investigator submits decision -> status becomes needs_evidence
    sub_res = client.post(
        "/api/v1/results/mock_high_result_flow/decision",
        json={
            "action": "request_evidence",
            "reason_category": "photo_unclear",
            "claimant_message": draft_data["claimant_message_en"],
            "slots_to_resubmit": ["damage_closeup"]
        },
        headers={"Authorization": f"Bearer {inv_token}"}
    )
    assert sub_res.status_code == 200
    assert sub_res.json()["new_status"] == "needs_evidence"

    # Verify claim status and action row
    claim = get_claim_record(cid)
    assert claim["status"] == "needs_evidence"
    actions = get_actions_for_claim_record(cid)
    assert len(actions) > 0
    assert actions[-1]["action"] == "request_evidence"

    # 3. Claimant resubmits requested slot
    resubmit_res = client.post(
        f"/api/v1/claims/{cid}/resubmit",
        files=[("evidence", ("new_damage_photo.jpg", b"\xff\xd8\xff\xe0dummy_photo", "image/jpeg"))],
        headers={"Authorization": f"Bearer {claimant_token}"}
    )
    assert resubmit_res.status_code == 202
    claim_after = get_claim_record(cid)
    assert claim_after["status"] == "under_review"
