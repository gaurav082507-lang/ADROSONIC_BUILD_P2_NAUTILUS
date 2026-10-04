import os
import sys
import time
import json

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

def main():
    settings.MOCK_ANALYSIS = False

    with TestClient(app) as client:
        health = client.get("/api/v1/health").json()
        print("Health Check:", health)
        assert health["models"]["ai_detector"] is True, "AI Detector must be loaded!"

        samples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/demo_samples"))
        samples = [
            "01_ai_generated_car_damage.jpg",
            "02_genuine_phone_photo.jpg",
            "03_edited_spliced_photo.jpg",
            "04_low_res_compressed.jpg"
        ]

        results_summary = []

        for sample_name in samples:
            sample_path = os.path.join(samples_dir, sample_name)
            print("\n" + "=" * 70)
            print(f"BENCHMARKING SAMPLE: {sample_name}")
            print("=" * 70)

            start_total = time.time()
            with open(sample_path, "rb") as f:
                resp = client.post("/api/v1/analyze/image", files={"file": (sample_name, f, "image/jpeg")})
            assert resp.status_code == 202
            job_id = resp.json()["job_id"]

            while True:
                job = client.get(f"/api/v1/jobs/{job_id}").json()
                if job.get("status") in ("done", "failed"):
                    break
                time.sleep(0.02)

            total_duration = time.time() - start_total
            result_id = job["result_id"]
            res = client.get(f"/api/v1/results/{result_id}").json()

            print(f"Job Status: {job['status']} | Total Wall Time: {total_duration:.3f} s")
            print("Step Breakdown:")
            step_timings = {}
            for s in job.get("steps", []):
                ms = s.get("duration_ms", 0)
                print(f"  * {s['name']:15s} : {s['status'].upper():7s} ({ms} ms)")
                step_timings[s["name"]] = ms

            overall = res.get("overall", {})
            print(f"\nScoring Outcome:")
            print(f"  * Risk Score   : {overall.get('risk', 0.0) * 100:.1f}%")
            print(f"  * Risk Band    : {overall.get('band')}")
            print(f"  * Confidence   : {overall.get('confidence')}")
            print(f"  * Summary      : {overall.get('summary')}")
            print(f"  * Evidence IDs : {[e['id'] for e in res.get('evidence', [])]}")
            print(f"  * Artifacts    : {list(res.get('artifacts', {}).keys())}")

            results_summary.append({
                "sample": sample_name,
                "wall_time_s": round(total_duration, 3),
                "step_timings_ms": step_timings,
                "risk": overall.get("risk"),
                "band": overall.get("band"),
                "confidence": overall.get("confidence"),
                "summary": overall.get("summary"),
                "evidence_ids": [e["id"] for e in res.get("evidence", [])],
                "artifacts": res.get("artifacts", {})
            })

        output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../docs/benchmark_results.json"))
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results_summary, f, indent=2)
        print("\n" + "=" * 70)
        print(f"Full benchmark written to: {output_path}")
        print("=" * 70)

if __name__ == "__main__":
    main()
