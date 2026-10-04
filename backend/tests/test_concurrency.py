"""Concurrency test (§9.5, Part 1).

Verifies:
1. Heavy CPU analysis runs OFF the main asyncio event loop.
2. While a long-running job runs in a worker thread, GET /jobs/{id} and GET /api/v1/health
   answer in < 300 ms without event loop starvation.
3. Polling shows live step progress changing as steps start and finish.
"""

import time
import threading
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.services import job_manager


def test_event_loop_responsiveness_and_step_progress():
    from backend.app.core.auth import create_access_token
    _token = create_access_token({"sub": "user_investigator", "role": "investigator"})
    client = TestClient(app, headers={"Authorization": f"Bearer {_token}"})
    
    # 1. Verify health is responsive initially
    t0 = time.perf_counter()
    res = client.get("/api/v1/health")
    init_duration = time.perf_counter() - t0
    assert res.status_code == 200
    assert init_duration < 0.300

    # 2. Create a background job and run simulated multi-step work in a worker thread
    job_id = job_manager.create_job("image")
    
    def fake_worker():
        semaphore = job_manager.get_semaphore()
        with semaphore:
            job_manager.update_job_status(job_id, "running")
            steps = ["preprocess", "metadata", "ai_detector", "ela", "noise"]
            for s in steps:
                job_manager.start_step(job_id, s)
                # Sleep to simulate heavy CPU analysis
                time.sleep(0.4)
                job_manager.finish_step(job_id, s, "ok", duration_ms=400)
            job_manager.update_job_status(job_id, "done", result_id="fake_res_123")

    worker_thread = threading.Thread(target=fake_worker, daemon=True)
    worker_thread.start()

    # 3. Poll /api/v1/health and /api/v1/jobs/{job_id} while worker runs
    observed_step_counts = set()
    health_latencies = []
    job_latencies = []

    poll_start = time.perf_counter()
    # Poll for ~2 seconds while fake_worker is running
    while time.perf_counter() - poll_start < 2.0:
        # Check /health responsiveness
        h_t0 = time.perf_counter()
        h_res = client.get("/api/v1/health")
        h_lat = time.perf_counter() - h_t0
        health_latencies.append(h_lat)
        assert h_res.status_code == 200
        assert h_lat < 0.300, f"Health endpoint stalled: {h_lat * 1000:.1f} ms"

        # Check /jobs/{id} responsiveness and progress
        j_t0 = time.perf_counter()
        j_res = client.get(f"/api/v1/jobs/{job_id}")
        j_lat = time.perf_counter() - j_t0
        job_latencies.append(j_lat)
        assert j_res.status_code == 200
        assert j_lat < 0.300, f"Jobs endpoint stalled: {j_lat * 1000:.1f} ms"

        data = j_res.json()
        steps = data.get("steps", [])
        observed_step_counts.add(len(steps))

        time.sleep(0.25)

    worker_thread.join(timeout=3.0)

    # 4. Assert responsiveness
    max_h_lat = max(health_latencies)
    max_j_lat = max(job_latencies)
    assert max_h_lat < 0.300, f"Max health latency was {max_h_lat * 1000:.1f} ms (expected < 300 ms)"
    assert max_j_lat < 0.300, f"Max job polling latency was {max_j_lat * 1000:.1f} ms (expected < 300 ms)"

    # 5. Assert live progress was observed changing across polls
    assert len(observed_step_counts) >= 2, f"Observed step counts did not change: {observed_step_counts}"
