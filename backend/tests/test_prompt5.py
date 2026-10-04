import io
import time
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import settings
from backend.app.services.orchestrator import RESULTS_DB, get_result
from backend.app.api.v1.mock_data import get_canned_result

from backend.app.core.auth import create_access_token

_token = create_access_token({"sub": "user_investigator", "role": "investigator"})
client = TestClient(app, headers={"Authorization": f"Bearer {_token}"})

def make_dummy_jpeg() -> bytes:
    # Minimal 1x1 valid JPEG
    from PIL import Image
    buf = io.BytesIO()
    im = Image.new("RGB", (10, 10), color="red")
    im.save(buf, format="JPEG")
    return buf.getvalue()

def make_dummy_png() -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    im = Image.new("RGB", (10, 10), color="blue")
    im.save(buf, format="PNG")
    return buf.getvalue()

def test_claim_no_input_error():
    resp = client.post("/api/v1/analyze/claim")
    assert resp.status_code == 422
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "NO_INPUT"

def test_claim_too_many_files_error():
    img_bytes = make_dummy_jpeg()
    files = [("image", (f"img_{i}.jpg", img_bytes, "image/jpeg")) for i in range(7)]
    resp = client.post("/api/v1/analyze/claim", files=files)
    assert resp.status_code == 422
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "TOO_MANY_FILES"
    assert data["error"]["details"]["count"] == 7

def test_claim_successful_submission_and_result():
    img_bytes = make_dummy_jpeg()
    files = [
        ("image", ("damage_1.jpg", img_bytes, "image/jpeg")),
        ("image", ("damage_2.jpg", img_bytes, "image/jpeg")),
        ("document", ("bill.jpg", img_bytes, "image/jpeg")),
        ("id_photo", ("id.jpg", img_bytes, "image/jpeg")),
    ]
    resp = client.post("/api/v1/analyze/claim", files=files)
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    job_id = data["job_id"]

    # Poll until job completes
    for _ in range(60):
        j_resp = client.get(f"/api/v1/jobs/{job_id}")
        assert j_resp.status_code == 200
        j_data = j_resp.json()
        if j_data["status"] in ("done", "failed"):
            break
        time.sleep(0.05)

    assert j_data["status"] == "done"
    result_id = j_data["result_id"]

    # Verify result payload structure (Part 2)
    res_resp = client.get(f"/api/v1/results/{result_id}")
    assert res_resp.status_code == 200
    res = res_resp.json()

    assert res["id"] == result_id
    assert res["mode"] == "claim"
    assert "overall" in res
    assert "why_this_score" in res
    assert "checks_run" in res
    assert "top_reasons" in res
    assert "recommended_action" in res
    assert res["summary_source"] == "template"
    assert "versions" in res

    # Verify why_this_score structure
    why = res["why_this_score"]
    assert "overall" in why
    assert "formula" in why["overall"]

    # Verify checks_run includes skipped identity detectors
    check_detectors = [c["detector"] for c in res["checks_run"]]
    assert "id_photo_match" in check_detectors
    assert "selfie_liveness" in check_detectors
    for c in res["checks_run"]:
        if c["detector"] in ("id_photo_match", "selfie_liveness"):
            assert c["status"] == "skipped"

    # Verify image_results list
    assert res["image_results"] is not None
    assert len(res["image_results"]) >= 1

    # Verify artifacts structure
    assert "artifacts" in res
    assert "preview_img_1" in res["artifacts"]

def test_evidence_filter_endpoint():
    res = get_canned_result(variant="HIGH", result_id="mock-ev-test")
    RESULTS_DB["mock-ev-test"] = res

    # Filter by pipeline=image
    resp = client.get("/api/v1/results/mock-ev-test/evidence?pipeline=image")
    assert resp.status_code == 200
    items = resp.json()
    assert all("IMG" in item["id"] or item.get("pipeline_input", "").startswith("img") for item in items)

    # Filter by severity=high
    resp_sev = client.get("/api/v1/results/mock-ev-test/evidence?severity=high")
    assert resp_sev.status_code == 200
    sev_items = resp_sev.json()
    assert all(item["severity"] == "high" for item in sev_items)

def test_history_endpoint():
    resp = client.get("/api/v1/history?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert data["page"] == 1

def test_delete_result_endpoint():
    # Insert or use a mock result
    res = get_canned_result(variant="LOW", result_id="mock-del-test")
    RESULTS_DB["mock-del-test"] = res

    # Delete result
    del_resp = client.delete("/api/v1/results/mock-del-test")
    assert del_resp.status_code == 204

    # Deleting non-existent should be 404
    non_del = client.delete("/api/v1/results/non-existent-uid-999")
    assert non_del.status_code == 404
    assert non_del.json()["error"]["code"] == "RESULT_NOT_FOUND"

def test_report_json_and_pdf_exports():
    res = get_canned_result(variant="HIGH", result_id="mock-report-test")
    RESULTS_DB["mock-report-test"] = res

    # Test JSON export
    json_resp = client.get("/api/v1/results/mock-report-test/report.json")
    assert json_resp.status_code == 200
    j_data = json_resp.json()
    assert "audit" in j_data
    assert "sha256" in j_data["audit"]
    assert len(j_data["audit"]["sha256"]) == 64

    # Test PDF export
    pdf_resp = client.get("/api/v1/results/mock-report-test/report.pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in pdf_resp.headers["content-disposition"]
    assert pdf_resp.content.startswith(b"%PDF-")

def test_not_found_error_codes():
    job_resp = client.get("/api/v1/jobs/non-existent-job-xyz")
    assert job_resp.status_code == 404
    assert job_resp.json()["error"]["code"] == "JOB_NOT_FOUND"

    res_resp = client.get("/api/v1/results/non-existent-res-xyz")
    assert res_resp.status_code == 404
    assert res_resp.json()["error"]["code"] == "RESULT_NOT_FOUND"

def test_rate_limiting():
    # Make requests until rate limit triggers
    triggered = False
    for _ in range(25):
        resp = client.post("/api/v1/analyze/claim")
        if resp.status_code == 429:
            triggered = True
            err = resp.json()
            assert err["error"]["code"] == "RATE_LIMITED"
            assert "limit" in err["error"]["details"]
            break
    assert triggered, "Expected rate limiter to trigger 429"
