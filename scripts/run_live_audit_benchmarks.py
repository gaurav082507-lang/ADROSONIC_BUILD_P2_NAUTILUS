import os
import sys
import time
import json

sys.path.insert(0, os.path.abspath("."))
os.environ["MOCK_ANALYSIS"] = "0"

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.auth import create_access_token
from backend.app.core.config import settings

settings.MOCK_ANALYSIS = False

client = TestClient(app)
token = create_access_token({"sub": "test-inv", "role": "investigator"})
headers = {"Authorization": f"Bearer {token}"}

def run_analysis(endpoint, files_dict, data_dict=None):
    t0 = time.time()
    res = client.post(endpoint, files=files_dict, data=data_dict or {}, headers=headers)
    dur = time.time() - t0
    if res.status_code != 202:
        return {"error": f"HTTP {res.status_code}: {res.text}", "duration": dur}
    job_id = res.json().get("job_id")
    
    # Poll job
    max_wait = 60
    start = time.time()
    while time.time() - start < max_wait:
        j_res = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        if j_res.status_code == 200:
            j_data = j_res.json()
            st = j_data.get("status")
            if st == "done":
                rid = j_data.get("result_id")
                r_res = client.get(f"/api/v1/results/{rid}", headers=headers)
                return {"result": r_res.json(), "duration": time.time() - t0}
            elif st == "failed":
                return {"error": j_data.get("error", "Job failed"), "duration": time.time() - t0}
        time.sleep(0.5)
    return {"error": "Timeout polling job", "duration": time.time() - t0}

def format_row(name, out):
    if "error" in out:
        return f"| {name} | **FAILED** | - | - | {out['error']} | - | {out['duration']:.2f} s |"
    res = out["result"]
    overall = res.get("overall", {})
    score = overall.get("risk", 0.0)
    band = overall.get("band", "UNKNOWN")
    conf = overall.get("confidence", "unknown")
    
    ev_list = res.get("evidence", [])
    top_ev = ", ".join([e.get("id", "") for e in ev_list[:3]]) if ev_list else "None"
    
    checks = res.get("checks_run", [])
    ok_c = sum(1 for c in checks if c.get("status") == "ok")
    sk_c = sum(1 for c in checks if c.get("status") == "skipped")
    fa_c = sum(1 for c in checks if c.get("status") == "failed")
    checks_str = f"ok:{ok_c}, sk:{sk_c}, fa:{fa_c}"
    
    return f"| {name} | {score:.3f} | {band} | {conf} | {top_ev} | {checks_str} | {out['duration']:.2f} s |"

def main():
    print("| File / Sample | Score | Band | Confidence | Top 3 Evidence | Checks Run | Runtime |")
    print("|---|---|---|---|---|---|---|")
    
    # 1. Images
    images = [
        "data/demo_samples/01_ai_generated_car_damage.jpg",
        "data/demo_samples/02_genuine_phone_photo.jpg",
        "data/demo_samples/03_edited_spliced_photo.jpg",
        "data/demo_samples/04_low_res_compressed.jpg",
    ]
    for p in images:
        if os.path.exists(p):
            with open(p, "rb") as f:
                out = run_analysis("/api/v1/analyze/image", {"image": (os.path.basename(p), f.read(), "image/jpeg")})
            print(format_row(os.path.basename(p), out))
        else:
            print(f"| {p} | NOT FOUND |")

    # 2. Demo Docs
    docs = [
        "data/demo_samples/docs/clean_invoice.pdf",
        "data/demo_samples/docs/hospital_bill.pdf",
        "data/demo_samples/docs/scanned_invoice.jpg",
        "data/demo_samples/docs/tampered_invoice.pdf",
    ]
    for p in docs:
        if os.path.exists(p):
            ctype = "application/pdf" if p.endswith(".pdf") else "image/jpeg"
            with open(p, "rb") as f:
                out = run_analysis("/api/v1/analyze/document", {"document": (os.path.basename(p), f.read(), ctype)})
            print(format_row(os.path.basename(p), out))

    # 3. Real world docs
    rw_docs = [
        "data/eval/real_world/ecommerce_amazon_invoice.pdf",
        "data/eval/real_world/hospital_discharge_bill.pdf",
        "data/eval/real_world/pharmacy_apollo_bill.pdf",
        "data/eval/real_world/telecom_airtel_bill.pdf",
        "data/eval/real_world/utility_electricity_bill.pdf",
    ]
    for p in rw_docs:
        if os.path.exists(p):
            with open(p, "rb") as f:
                out = run_analysis("/api/v1/analyze/document", {"document": (os.path.basename(p), f.read(), "application/pdf")})
            print(format_row("rw/" + os.path.basename(p), out))

    # 4. Identity cards
    id_cards = [
        ("01_valid_aadhaar_card.png", "matching_selfie.jpg"),
        ("02_tampered_printed_aadhaar.png", "matching_selfie.jpg"),
        ("03_invalid_signature_aadhaar.png", "matching_selfie.jpg"),
    ]
    for id_name, selfie_name in id_cards:
        id_p = os.path.join("data/demo_samples/identity", id_name)
        sf_p = os.path.join("data/demo_samples/identity", selfie_name)
        if os.path.exists(id_p) and os.path.exists(sf_p):
            with open(id_p, "rb") as f_id, open(sf_p, "rb") as f_sf:
                files = {
                    "id_photo": (id_name, f_id.read(), "image/png"),
                    "selfie": (selfie_name, f_sf.read(), "image/jpeg"),
                }
                out = run_analysis("/api/v1/analyze/claim", files)
            print(format_row(f"identity/{id_name}", out))

    # 5. Full claim
    full_claim_files = {}
    p_img = "data/demo_samples/03_edited_spliced_photo.jpg"
    p_doc = "data/demo_samples/docs/tampered_invoice.pdf"
    p_id = "data/demo_samples/identity/01_valid_aadhaar_card.png"
    p_sf = "data/demo_samples/identity/mismatch_selfie.jpg"
    
    with open(p_img, "rb") as f: full_claim_files["image"] = ("spliced.jpg", f.read(), "image/jpeg")
    with open(p_doc, "rb") as f: full_claim_files["document"] = ("tampered.pdf", f.read(), "application/pdf")
    with open(p_id, "rb") as f: full_claim_files["id_photo"] = ("id.png", f.read(), "image/png")
    with open(p_sf, "rb") as f: full_claim_files["selfie"] = ("selfie.jpg", f.read(), "image/jpeg")
    
    out = run_analysis("/api/v1/analyze/claim", full_claim_files)
    print(format_row("Full Claim (spliced+tampered+id+mismatch)", out))

if __name__ == "__main__":
    main()
