import requests
import time
import json

base_url = 'http://127.0.0.1:5173/api/v1'

print("=== 1. Health check via Frontend Proxy (port 5173 -> 8000) ===")
r_health = requests.get(f"{base_url}/health")
print("Status:", r_health.status_code, r_health.json())
assert r_health.status_code == 200

print("\n=== 2. Submitting Claim Analysis (damage photo + tampered invoice) ===")
with open('data/demo_samples/01_ai_generated_car_damage.jpg', 'rb') as f_img, \
     open('data/demo_samples/docs/tampered_invoice.pdf', 'rb') as f_doc:
    files = [
        ('image', ('ai_damage_car.jpg', f_img, 'image/jpeg')),
        ('document', ('tampered_invoice.pdf', f_doc, 'application/pdf')),
    ]
    data = {'metadata': json.dumps({'policy_number': 'POL-2026-LIVE', 'claimed_amount': 88500.0, 'peril': 'motor'})}
    r_submit = requests.post(f"{base_url}/analyze/claim", files=files, data=data)

print("Submit HTTP Status:", r_submit.status_code)
assert r_submit.status_code == 202
job_id = r_submit.json()['job_id']
print(f"Created Job ID: {job_id}")

print("\n=== 3. Polling Job Progress via Frontend Proxy ===")
result_id = None
for i in range(60):
    r_job = requests.get(f"{base_url}/jobs/{job_id}")
    job_data = r_job.json()
    status = job_data.get('status')
    steps = job_data.get('steps', [])
    done_steps = [s['name'] for s in steps if s.get('status') == 'done']
    running_steps = [s['name'] for s in steps if s.get('status') == 'running']
    print(f"[{i*0.8:.1f}s] Status: {status} | Running: {running_steps} | Done ({len(done_steps)}): {done_steps[-2:] if done_steps else []}")
    if status == 'done':
        result_id = job_data['result_id']
        break
    time.sleep(0.8)

assert result_id is not None
print(f"\n=== 4. Fetching Complete Result ({result_id}) ===")
r_res = requests.get(f"{base_url}/results/{result_id}")
assert r_res.status_code == 200
res = r_res.json()

print(f"Overall Band: {res['overall']['band']} | Risk: {res['overall']['risk'] * 100:.1f}% | Confidence: {res['overall']['confidence']}")
print(f"Summary: {res['overall']['summary']}")
print(f"Recommended Action: {res.get('recommended_action')}")
print(f"\nTop Reasons ({len(res.get('top_reasons', []))}):")
for r in res.get('top_reasons', []):
    print(f"  - {r}")

print("\nWhy This Score (Overall Formula):")
print(" ", res.get('why_this_score', {}).get('overall', {}).get('formula'))

print(f"\nArtifacts Available ({len(res.get('artifacts', {}))}):")
for k, v in res.get('artifacts', {}).items():
    if isinstance(v, list):
        print(f"  - {k}: {len(v)} items")
    else:
        print(f"  - {k}: {v}")

print("\n=== 5. Verifying PDF Report Download via Frontend Proxy ===")
r_pdf = requests.get(f"{base_url}/results/{result_id}/report.pdf")
print("PDF Status:", r_pdf.status_code, "| Content-Length:", len(r_pdf.content), "bytes | Type:", r_pdf.headers.get('content-type'))
assert r_pdf.status_code == 200
assert r_pdf.content.startswith(b'%PDF-')

print("\n=== 6. Verifying History Page Data via Frontend Proxy ===")
r_hist = requests.get(f"{base_url}/history?page=1&page_size=5")
hist = r_hist.json()
print(f"History total cases: {hist['total']} | Returned items on page 1: {len(hist['items'])}")
latest = hist['items'][0]
print(f"Latest case: ID={latest['id']}, Mode={latest['mode']}, Risk={latest['overall_risk']}, Band={latest['overall_band']}")

print("\n=======================================================")
print("SUCCESS: FRONTEND AND BACKEND ARE WORKING TOGETHER 100%!")
print("=======================================================")
