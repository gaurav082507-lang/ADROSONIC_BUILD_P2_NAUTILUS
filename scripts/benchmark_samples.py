import httpx, time, json

client = httpx.Client(base_url="http://localhost:8000/api/v1", timeout=120)
tok = client.post("/auth/login", json={"email": "investigator@demo.in", "password": "demo"}).json()["token"]
hdr = {"Authorization": f"Bearer {tok}"}

samples = [
    ("document", "ecommerce_amazon_invoice.pdf", "data/eval/real_world/ecommerce_amazon_invoice.pdf"),
    ("document", "hospital_discharge_bill.pdf", "data/eval/real_world/hospital_discharge_bill.pdf"),
    ("document", "pharmacy_apollo_bill.pdf", "data/eval/real_world/pharmacy_apollo_bill.pdf"),
    ("document", "telecom_airtel_bill.pdf", "data/eval/real_world/telecom_airtel_bill.pdf"),
]

for mode, name, path in samples:
    t0 = time.time()
    with open(path, "rb") as f:
        r = client.post(f"/analyze/{mode}", files={"file": (name, f.read())}, headers=hdr)
    job_id = r.json()["job_id"]
    while True:
        j = client.get(f"/jobs/{job_id}", headers=hdr).json()
        if j["status"] in ("done", "failed"):
            break
        time.sleep(0.3)
    dt = time.time() - t0
    res_id = j["result_id"]
    res = client.get(f"/results/{res_id}", headers=hdr).json()
    ov = res["overall"]
    ev_ids = [e["id"] for e in res.get("evidence", [])][:3]
    cr = res.get("checks_run", [])
    ok_cnt = sum(1 for c in cr if c["status"] == "ok")
    sk_cnt = sum(1 for c in cr if c["status"] == "skipped")
    fa_cnt = sum(1 for c in cr if c["status"] == "failed")
    print(f"{name} | {ov['risk']:.3f} | {ov['band']} | {ov['confidence']} | {ev_ids} | ok:{ok_cnt},sk:{sk_cnt},fa:{fa_cnt} | {dt:.2f}s")
