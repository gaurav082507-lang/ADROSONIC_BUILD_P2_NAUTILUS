r"""
Capture the Lucen AI backend contract + real response fixtures for lucen-web.

Usage (from the backend repo root, backend running on :8000):
    backend\.venv\Scripts\python.exe capture_fixtures.py --out ..\lucen-web\contract

Options:
    --base   API base (default http://localhost:8000)
    --out    output folder (default ./contract)
Every fixture is attempted independently: failures print SKIP and the rest continue.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import httpx

p = argparse.ArgumentParser()
p.add_argument("--base", default="http://localhost:8000")
p.add_argument("--out", default="contract")
p.add_argument("--inv", default="investigator@demo.in")
p.add_argument("--claimant", default="ravi@demo.in")
p.add_argument("--password", default="demo")
args = p.parse_args()

BASE = args.base.rstrip("/")
API = BASE + "/api/v1"
OUT = Path(args.out)
FIX = OUT / "fixtures"
FIX.mkdir(parents=True, exist_ok=True)
SAMPLES = Path("data/demo_samples")
client = httpx.Client(timeout=180)
ok, skipped = [], []


def save(name, data):
    (FIX / f"{name}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    ok.append(name)
    print(f"  OK    {name}.json")


def skip(name, why):
    skipped.append(name)
    print(f"  SKIP  {name}: {why}")


def find(*keywords):
    """Find a demo sample whose path contains all keywords (case-insensitive)."""
    for f in sorted(SAMPLES.rglob("*")):
        if f.is_file() and all(k.lower() in str(f).lower() for k in keywords):
            return f
    return None


def login(email):
    r = client.post(f"{API}/auth/login", json={"email": email, "password": args.password})
    if r.status_code >= 400:  # fall back to OAuth2 form style
        r = client.post(f"{API}/auth/login", data={"username": email, "password": args.password})
    r.raise_for_status()
    return r.json()


def hdr(tok):
    return {"Authorization": f"Bearer {tok}"} if tok else {}


def run_job(path, files, data, tok, job_prefix=None):
    r = client.post(f"{API}{path}", files=files, data=data, headers=hdr(tok))
    r.raise_for_status()
    job_id = r.json()["job_id"]
    running_saved = False
    for _ in range(240):
        j = client.get(f"{API}/jobs/{job_id}", headers=hdr(tok)).json()
        if job_prefix and j.get("status") == "running" and not running_saved:
            save(f"{job_prefix}_running", j)
            running_saved = True
        if j.get("status") in ("done", "failed"):
            if job_prefix:
                save(f"{job_prefix}_done", j)
            return j.get("result_id"), j
        time.sleep(0.5)
    raise TimeoutError(f"job {job_id} did not finish")


def get(name, url, tok):
    try:
        r = client.get(f"{API}{url}", headers=hdr(tok))
        if r.status_code >= 400:
            return skip(name, f"HTTP {r.status_code} {r.text[:120]}")
        save(name, r.json())
        return r.json()
    except Exception as e:  # noqa: BLE001
        skip(name, repr(e))


print("1) openapi.json")
try:
    spec = client.get(f"{BASE}/openapi.json").json()
    (OUT / "openapi.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
    print(f"  OK    openapi.json ({len(spec.get('paths', {}))} paths)")
except Exception as e:  # noqa: BLE001
    sys.exit(f"Cannot reach {BASE}/openapi.json – is the backend running? ({e})")

print("2) auth")
inv_tok = cl_tok = None
try:
    li = login(args.inv); save("login_investigator", li); inv_tok = li.get("token") or li.get("access_token")
except Exception as e:  # noqa: BLE001
    skip("login_investigator", repr(e))
try:
    lc = login(args.claimant); save("login_claimant", lc); cl_tok = lc.get("token") or lc.get("access_token")
except Exception as e:  # noqa: BLE001
    skip("login_claimant", repr(e))
if inv_tok:
    get("me_investigator", "/auth/me", inv_tok)

print("3) analyses (real pipeline)")
results = {}
cases = [
    ("result_image_high", "/analyze/image", {"file": find("ai_generated")}, "job"),
    ("result_image_low", "/analyze/image", {"file": find("genuine")}, None),
    ("result_document_high", "/analyze/document", {"file": find("tampered_invoice.pdf")}, None),
    ("result_high", "/analyze/claim", {"image": find("ai_generated"), "document": find("tampered_invoice.pdf")}, None),
    ("result_low", "/analyze/claim", {"image": find("genuine"), "document": find("clean_invoice")}, None),
    ("result_identity", "/analyze/claim", {"image": find("genuine"), "id_photo": find("identity", "id_card"),
                                          "selfie": find("identity", "selfie")}, None),
]
for name, path, filemap, prefix in cases:
    missing = [k for k, v in filemap.items() if v is None]
    if missing:
        skip(name, f"sample file not found for {missing} in {SAMPLES}")
        continue
    try:
        files = [(k, (v.name, v.read_bytes())) for k, v in filemap.items()]
        rid, _ = run_job(path, files, {}, inv_tok, prefix)
        results[name] = rid
        get(name, f"/results/{rid}", inv_tok)
    except Exception as e:  # noqa: BLE001
        skip(name, repr(e))

rid = results.get("result_high")
if rid:
    get("result_evidence", f"/results/{rid}/evidence", inv_tok)
    get("timeline", f"/results/{rid}/timeline", inv_tok)
    # decision draft: use the first reason category enum found in the contract
    reason = "photo_unclear"
    for s in spec.get("components", {}).get("schemas", {}).values():
        values = s.get("enum") if isinstance(s, dict) else None
        if values and any("unclear" in str(v) or "verification" in str(v) for v in values):
            reason = values[0]
            break
    try:
        r = client.post(f"{API}/results/{rid}/decision/draft", headers=hdr(inv_tok),
                        json={"action": "request_evidence", "reason_category": reason})
        save("decision_draft", r.json()) if r.status_code < 400 else skip("decision_draft", f"HTTP {r.status_code} {r.text[:150]}")
    except Exception as e:  # noqa: BLE001
        skip("decision_draft", repr(e))

print("4) lists")
get("queue", "/queue", inv_tok)
get("history", "/history", inv_tok)
get("health", "/health", inv_tok)

print("5) claimant")
get("policies", "/policies/mine", cl_tok)
mine = get("claims_mine", "/claims/mine", cl_tok)
items = mine if isinstance(mine, list) else (mine or {}).get("items", []) if isinstance(mine, dict) else []
if items:
    cid = items[0].get("claim_id") or items[0].get("id")
    get("claim_status", f"/claims/{cid}/status", cl_tok)
    get("evidence_timeline", f"/claims/{cid}/evidence-timeline", cl_tok)
    get("claim_actions", f"/claims/{cid}/actions", inv_tok)
    get("claim_entities", f"/claims/{cid}/entities", inv_tok)
else:
    skip("claim_status", "claimant has no claims (run the demo seed first)")

print("6) error shape")
try:
    r = client.get(f"{API}/results/does-not-exist", headers=hdr(inv_tok))
    save("error_not_found", r.json())
except Exception as e:  # noqa: BLE001
    skip("error_not_found", repr(e))

print(f"\nDone: {len(ok)} fixtures saved to {FIX.resolve()}, {len(skipped)} skipped.")
if skipped:
    print("Skipped:", ", ".join(skipped))
