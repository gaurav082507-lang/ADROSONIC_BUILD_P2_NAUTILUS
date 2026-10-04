import httpx
import sys
import time
import json
import os
import shutil
from PIL import Image, ImageDraw

def create_sample_img(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img = Image.new('RGB', (400, 300), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((10,10), text, fill=(255,255,0))
    img.save(path)
    return path

def main():
    print("Logging in...")
    r = httpx.post('http://localhost:8000/api/v1/auth/login', json={'email': 'investigator@lucen.ai', 'password': 'Password123!'})
    if r.status_code != 200:
        print(f"Failed to login investigator: {r.text}")
        sys.exit(1)
    
    inv_token = r.json().get('token')

    r_c = httpx.post('http://localhost:8000/api/v1/auth/login', json={'email': 'ravi@demo.in', 'password': 'demo'})
    if r_c.status_code != 200:
        print(f"Failed to login claimant: {r_c.text}")
        sys.exit(1)
    c_token = r_c.json().get('token')

    print("Calling POST /api/v1/admin/reset-demo...")
    r2 = httpx.post('http://localhost:8000/api/v1/admin/reset-demo', headers={'Authorization': f'Bearer {inv_token}'}, timeout=30.0)
    if r2.status_code != 200:
        print(f"Failed to wipe demo data: {r2.text}")
        sys.exit(1)

    print("Demo data wiped. Now submitting 6 claims...")

    claims_data = [
        # Normal
        {"policy": "POL-MOT-8821", "type": "motor", "amount": 1000, "meta": {"0": {"slot": "damage_closeup"}}, "file": "img1.jpg"},
        # Duplicate 1 (Ring)
        {"policy": "POL-MOT-8821", "type": "motor", "amount": 2500, "meta": {"0": {"slot": "damage_closeup"}}, "file": "ring.jpg", "bank": "****4417"},
        # Duplicate 2 (Ring)
        {"policy": "POL-MOT-8821", "type": "motor", "amount": 2500, "meta": {"0": {"slot": "damage_closeup"}}, "file": "ring.jpg", "bank": "****4417"},
        # Duplicate 3 (Ring)
        {"policy": "POL-MOT-8821", "type": "motor", "amount": 2500, "meta": {"0": {"slot": "damage_closeup"}}, "file": "ring.jpg", "bank": "****4417"},
        # Health claim
        {"policy": "POL-HLT-4402", "type": "health", "amount": 50000, "meta": {"0": {"slot": "bill"}}, "file": "health.jpg"},
        # Property claim
        {"policy": "POL-PRP-1093", "type": "property", "amount": 8000, "meta": {"0": {"slot": "wide_shot"}}, "file": "prop.jpg"}
    ]

    os.makedirs("tmp", exist_ok=True)
    create_sample_img("tmp/img1.jpg", "Car Damage 1")
    create_sample_img("tmp/ring.jpg", "Shared Ring Photo")
    create_sample_img("tmp/health.jpg", "Health Bill")
    create_sample_img("tmp/prop.jpg", "Property Damage")

    claim_ids = []
    for c in claims_data:
        fpath = f"tmp/{c['file']}"
        with open(fpath, "rb") as f:
            files = {
                "evidence": (c['file'], f, "image/jpeg")
            }
            data = {
                "policy_id": c["policy"],
                "claim_type": c["type"],
                "peril": "accident" if c["type"] == "motor" else "illness",
                "incident_date": "2026-10-01",
                "claimed_amount": str(c["amount"]),
                "consent": "true",
                "evidence_metadata": json.dumps(c["meta"])
            }
            res = httpx.post("http://localhost:8000/api/v1/claims", headers={"Authorization": f"Bearer {c_token}"}, data=data, files=files, timeout=30.0)
            if res.status_code == 200 or res.status_code == 201:
                cid = res.json()["claim_id"]
                claim_ids.append(cid)
                print(f"Submitted claim {cid}")
            else:
                print(f"Failed to submit claim: {res.text}")

    print("Waiting for orchestrator to finish...")
    for _ in range(30):
        all_done = True
        for cid in claim_ids:
            res = httpx.get(f"http://localhost:8000/api/v1/claims/{cid}/status", headers={"Authorization": f"Bearer {c_token}"})
            if res.status_code == 200:
                if res.json().get("status") in ("submitted", "analysing"):
                    all_done = False
        if all_done:
            break
        time.sleep(2)

    q = httpx.get('http://localhost:8000/api/v1/queue?sort=newest&limit=50', headers={'Authorization': f'Bearer {inv_token}'})
    if q.status_code == 200:
        items = q.json().get('items', [])
        print("\n--- Seeded Claims ---")
        print(f"{'Claimant':<20} | {'Band':<8} | {'Score':<5} | {'Top Reason'}")
        print("-" * 80)
        for i in items:
            name = i.get('claimant_name', '')
            band = i.get('band', '')
            score = i.get('overall_risk', 0.0)
            reason = str(i.get('top_reason', ''))[:40]
            print(f"{name:<20} | {band:<8} | {score:<5.2f} | {reason}")

if __name__ == '__main__':
    main()
