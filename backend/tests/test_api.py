import pytest
import asyncio
import time
from fastapi.testclient import TestClient
from app.main import app
from app.detectors.base import run_safely, AnalysisContext
from app.core.config import settings

from backend.app.core.auth import create_access_token

_token = create_access_token({"sub": "user_investigator", "role": "investigator"})
client = TestClient(app, headers={"Authorization": f"Bearer {_token}"})

def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "models" in data

def test_upload_success_and_poll():
    # Valid JPEG magic bytes header: \xFF\xD8\xFF\xE0
    jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 100
    response = client.post(
        "/api/v1/analyze/image",
        files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")}
    )
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    job_id = data["job_id"]

    # Poll job until done
    for _ in range(50):
        res = client.get(f"/api/v1/jobs/{job_id}")
        assert res.status_code == 200
        job_data = res.json()
        if job_data["status"] == "done":
            break
        time.sleep(0.05)

    assert job_data["status"] == "done"
    result_id = job_data["result_id"]
    assert result_id is not None

    # Fetch result
    res_resp = client.get(f"/api/v1/results/{result_id}")
    assert res_resp.status_code == 200
    result = res_resp.json()
    assert result["id"] == result_id
    assert "overall" in result
    assert result["overall"]["band"] in ("LOW", "MEDIUM", "HIGH")
    assert "evidence" in result
    assert "detector_status" in result
    assert "artifacts" in result

def test_upload_wrong_type():
    # ZIP magic bytes: PK\x03\x04
    zip_bytes = b"PK\x03\x04" + b"\x00" * 100
    # Temporarily force non-mock validation
    old_mock = settings.MOCK_ANALYSIS
    settings.MOCK_ANALYSIS = False
    try:
        response = client.post(
            "/api/v1/analyze/image",
            files={"file": ("archive.zip", zip_bytes, "application/zip")}
        )
        assert response.status_code == 415
        err = response.json()
        assert "error" in err
        assert err["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
    finally:
        settings.MOCK_ANALYSIS = old_mock

def test_upload_too_large():
    # 16 MB dummy payload (> 15 MB MAX_UPLOAD_MB)
    dummy = b"\xff\xd8\xff\xe0" + b"\x00" * (16 * 1024 * 1024)
    old_mock = settings.MOCK_ANALYSIS
    settings.MOCK_ANALYSIS = False
    try:
        response = client.post(
            "/api/v1/analyze/image",
            files={"file": ("huge.jpg", dummy, "image/jpeg")}
        )
        assert response.status_code == 413
        err = response.json()
        assert err["error"]["code"] == "FILE_TOO_LARGE"
    finally:
        settings.MOCK_ANALYSIS = old_mock

def test_mock_canned_results():
    """Mock canned results are only served when MOCK_ANALYSIS=True."""
    old_mock = settings.MOCK_ANALYSIS
    settings.MOCK_ANALYSIS = True
    try:
        # GET /jobs for mock job
        res_job = client.get("/api/v1/jobs/mock-123")
        assert res_job.status_code == 200
        assert res_job.json()["status"] == "done"

        # GET /results for mock results
        res_high = client.get("/api/v1/results/mock-result-HIGH")
        assert res_high.status_code == 200
        assert res_high.json()["overall"]["band"] == "HIGH"
        assert len(res_high.json()["evidence"]) > 0

        res_low = client.get("/api/v1/results/mock-result-LOW")
        assert res_low.status_code == 200
        assert res_low.json()["overall"]["band"] == "LOW"
    finally:
        settings.MOCK_ANALYSIS = old_mock

@pytest.mark.asyncio
async def test_run_safely():
    # 1. Raising detector marks status=failed and contains exception
    async def crash_det(ctx):
        raise ValueError("Simulated model failure")

    ctx = AnalysisContext(job_id="test-job-001")
    status1, out1 = await run_safely(crash_det, ctx, "crash_detector")
    assert status1.status == "failed"
    assert "Simulated model failure" in status1.error
    assert len(out1.evidence) == 0

    # 2. Timing out detector with custom timeout_s marks status=failed and contains timeout
    class TimeoutDetector:
        name = "timeout_detector"
        timeout_s = 0.05  # fast timeout for test execution

        async def run(self, ctx):
            await asyncio.sleep(2.0)
            return []

    det2 = TimeoutDetector()
    status2, out2 = await run_safely(det2, ctx)
    assert status2.status == "failed"
    assert status2.error == "timeout"
    assert len(out2.evidence) == 0
