import urllib.request
import json
import time
import sys
import os
from pathlib import Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
from backend.app.core.auth import create_access_token

def measure():
    token = create_access_token({"sub": "user_investigator", "role": "investigator", "email": "investigator@demo.in"})
    auth_header = f"Bearer {token}"

    url = "http://127.0.0.1:8000/api/v1/analyze/document"
    pdf_path = Path("data/eval/real_world/ecommerce_amazon_invoice.pdf").resolve()

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = []
    body.append(f"--{boundary}".encode())
    body.append(f'Content-Disposition: form-data; name="file"; filename="{pdf_path.name}"'.encode())
    body.append(b"Content-Type: application/pdf")
    body.append(b"")
    body.append(pdf_path.read_bytes())
    body.append(f"--{boundary}--".encode())
    body.append(b"")
    payload = b"\r\n".join(body)

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": auth_header
        }
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
    job_id = res["job_id"]
    print("Started job:", job_id)

    latencies = []
    # Poll GET /jobs/{job_id} while it runs
    for _ in range(120):
        t0 = time.perf_counter()
        job_req = urllib.request.Request(
            f"http://127.0.0.1:8000/api/v1/jobs/{job_id}",
            headers={"Authorization": auth_header}
        )
        try:
            with urllib.request.urlopen(job_req) as resp:
                data = json.loads(resp.read().decode())
            dt = (time.perf_counter() - t0) * 1000.0
            latencies.append(dt)
            time.sleep(0.02)
            if data.get("status") in ("done", "failed"):
                break
        except Exception as e:
            print("Error polling job:", e)
            break

    lat_arr = np.array(latencies)
    print(f"Count of requests: {len(lat_arr)}")
    print(f"Mean latency: {np.mean(lat_arr):.2f} ms")
    print(f"Median latency: {np.median(lat_arr):.2f} ms")
    print(f"p95 latency: {np.percentile(lat_arr, 95):.2f} ms")
    print(f"Max latency: {np.max(lat_arr):.2f} ms")

if __name__ == "__main__":
    measure()
