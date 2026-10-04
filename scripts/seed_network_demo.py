"""
Seed Network & Analytics Demo Data (§14.3, §16, Prompt 10 Part 6).
Creates honest demo scenarios and labelled synthetic history:
1. Scenario A (Ring): 3 claimants share one bank account + damage photo reused.
2. Scenario B (No Ring): 2 claimants share only the same garage (proves weak edge rule).
3. Scenario C: Clean independent claims.
4. ~300 longitudinal claims across 90 days labelled data_source="synthetic_history".
"""

import os
import sys
import json
import random
import time
import asyncio
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.config import settings
from backend.app.db.database import get_connection
from backend.app.services import orchestrator, job_manager
from backend.app.services.network import detect_fraud_rings
from backend.app.services.entity_store import extract_and_store_entities

DATA_DEMO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/demo_samples"))


async def seed_live_demo_claims(force: bool = False):
    conn = get_connection()
    c_count = conn.execute("SELECT COUNT(*) as c FROM rings WHERE data_source = 'real'").fetchone()["c"]
    if c_count > 0 and not force:
        print(f"Rings already present ({c_count}); skipping live demo seeding.")
        conn.close()
        return

    if force:
        print("Cleaning up old demo claims and rings...")
        conn.execute("DELETE FROM image_hashes WHERE claim_id LIKE 'CLM-%'")
        conn.execute("DELETE FROM entities WHERE claim_id LIKE 'CLM-%'")
        conn.execute("DELETE FROM claims WHERE id LIKE 'CLM-%' AND data_source = 'real'")
        conn.execute("DELETE FROM rings WHERE data_source = 'real'")
        conn.execute("DELETE FROM ring_members")
        conn.execute("DELETE FROM ring_audits")
        conn.commit()

    print("Seeding live demo claims for network analysis...")
    settings.MOCK_ANALYSIS = False

    demo_claims_def = [
        # ── SCENARIO A: Fraud Ring (3 claimants, shared bank, reused photo) ──────
        {
            "id": "CLM-RING-01",
            "claimant_id": "user_vikram",
            "claimant_name": "Vikram Malhotra",
            "policy": "POL-MOT-8821",
            "type": "motor",
            "amount": 150000.0,
            "images": [os.path.join(DATA_DEMO_DIR, "03_edited_spliced_photo.jpg")],
            "doc": None,
            "bank": "98765432104417",
            "phone": "9876542210",
            "vehicle": "MH12AB1234",
            "image_cluster": "cluster_damage_spliced_car",
            "garage": "Speedway Motors Mumbai",
            "created_at": (datetime.utcnow() - timedelta(days=12)).isoformat()
        },
        {
            "id": "CLM-RING-02",
            "claimant_id": "user_priya",
            "claimant_name": "Priya Sharma",
            "policy": "POL-MOT-8822",
            "type": "motor",
            "amount": 175000.0,
            "images": [os.path.join(DATA_DEMO_DIR, "03_edited_spliced_photo.jpg")],  # Reused photo!
            "doc": None,
            "bank": "98765432104417",  # Same bank account!
            "phone": "9876542210",      # Same phone!
            "vehicle": "MH12AB1234",   # Same vehicle!
            "image_cluster": "cluster_damage_spliced_car",
            "garage": "Speedway Motors Mumbai",
            "created_at": (datetime.utcnow() - timedelta(days=8)).isoformat()
        },
        {
            "id": "CLM-RING-03",
            "claimant_id": "user_amit",
            "claimant_name": "Amit Verma",
            "policy": "POL-MOT-8823",
            "type": "motor",
            "amount": 160000.0,
            "images": [os.path.join(DATA_DEMO_DIR, "01_ai_generated_car_damage.jpg")],
            "doc": None,
            "bank": "98765432104417",  # Same bank account!
            "phone": "9811223344",
            "vehicle": "MH12AB9999",
            "garage": "City Auto Workshop",
            "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat()
        },

        # ── SCENARIO B: Shared Garage Only (2 claimants, NO ring) ───────────────
        {
            "id": "CLM-GARAGE-01",
            "claimant_id": "user_neha",
            "claimant_name": "Neha Gupta",
            "policy": "POL-MOT-8824",
            "type": "motor",
            "amount": 42000.0,
            "images": [os.path.join(DATA_DEMO_DIR, "04_low_res_compressed.jpg")],
            "doc": None,
            "bank": "11223344550001",
            "phone": "9711002233",
            "vehicle": "MH01CD5678",
            "garage": "National Service Center",  # Shared garage ONLY
            "created_at": (datetime.utcnow() - timedelta(days=5)).isoformat()
        },
        {
            "id": "CLM-GARAGE-02",
            "claimant_id": "user_rahul",
            "claimant_name": "Rahul Mehta",
            "policy": "POL-MOT-8825",
            "type": "motor",
            "amount": 38000.0,
            "images": [os.path.join(DATA_DEMO_DIR, "02_genuine_phone_photo.jpg")],
            "doc": None,
            "bank": "11223344550002",
            "phone": "9722003344",
            "vehicle": "MH02EF9012",
            "garage": "National Service Center",  # Shared garage ONLY
            "created_at": (datetime.utcnow() - timedelta(days=4)).isoformat()
        },

        # ── SCENARIO C: Clean Claims ───────────────────────────────────────────
        {
            "id": "CLM-CLEAN-01",
            "claimant_id": "user_sunita",
            "claimant_name": "Sunita Patel",
            "policy": "POL-HLT-9901",
            "type": "health",
            "amount": 25000.0,
            "images": [],
            "doc": os.path.join(DATA_DEMO_DIR, "docs/clean_invoice.pdf"),
            "bank": "55667788990001",
            "phone": "9833445566",
            "vehicle": None,
            "garage": "Apollo Hospital Delhi",
            "created_at": (datetime.utcnow() - timedelta(days=15)).isoformat()
        },
        {
            "id": "CLM-CLEAN-02",
            "claimant_id": "user_vikram",
            "claimant_name": "Vikram Singh",
            "policy": "POL-MOT-8826",
            "type": "motor",
            "amount": 18000.0,
            "images": [os.path.join(DATA_DEMO_DIR, "02_genuine_phone_photo.jpg")],
            "doc": None,
            "bank": "55667788990002",
            "phone": "9844556677",
            "vehicle": "DL04GH1122",
            "garage": "Express Car Care",
            "created_at": (datetime.utcnow() - timedelta(days=10)).isoformat()
        },
        {
            "id": "CLM-CLEAN-03",
            "claimant_id": "user_anita",
            "claimant_name": "Anita Desai",
            "policy": "POL-PRP-7701",
            "type": "property",
            "amount": 65000.0,
            "images": [],
            "doc": os.path.join(DATA_DEMO_DIR, "docs/clean_invoice.pdf"),
            "bank": "55667788990003",
            "phone": "9855667788",
            "vehicle": None,
            "garage": "Reliable Property Repairs",
            "created_at": (datetime.utcnow() - timedelta(days=2)).isoformat()
        }
    ]

    for d in demo_claims_def:
        cid = d["id"]
        # Create claim row in database first
        conn.execute("""
            INSERT INTO claims (
                id, claimant_user_id, claimant_name, policy_number, claim_type,
                claimed_amount, status, data_source, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'real', ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                claimant_user_id=excluded.claimant_user_id,
                claimant_name=excluded.claimant_name,
                policy_number=excluded.policy_number,
                claim_type=excluded.claim_type,
                claimed_amount=excluded.claimed_amount,
                status=excluded.status,
                data_source=excluded.data_source,
                updated_at=excluded.updated_at
        """, (
            cid, d["claimant_id"], d["claimant_name"], d["policy"], d["type"],
            d["amount"], "under_review", d["created_at"], d["created_at"]
        ))

        # Store entities
        claim_data = {
            "bank_account": d["bank"],
            "phone": d["phone"],
            "facility_name": d["garage"],
            "vehicle_number": d.get("vehicle"),
            "image_cluster": d.get("image_cluster")
        }
        extract_and_store_entities(
            claim_id=cid,
            result_id=f"res_{cid}",
            claim_data=claim_data,
            user_data={"id": d["claimant_id"], "email": f"{d['claimant_id']}@demo.in"}
        )

        # Run real orchestrator pipeline on the images/doc
        job_id = job_manager.create_job("claim")
        payload = {
            "claim_id": cid,
            "claimant_id": d["claimant_id"],
            "images": d["images"],
            "document": d["doc"],
            "id_photo": None,
            "selfie": None,
            "metadata": {
                "claim_id": cid,
                "claimant_user_id": d["claimant_id"],
                "claimed_amount": d["amount"],
                "vehicle_number": d.get("vehicle")
            }
        }
        res = await orchestrator._execute_analysis_job(job_id, "claim", payload)
        if res:
            conn.execute("UPDATE claims SET result_id = ? WHERE id = ?", (res.id, cid))

    conn.commit()
    conn.close()

    # Rebuild network & detect rings
    rings = detect_fraud_rings(rebuild=True)
    print(f"Network demo claims processed. Rings found: {len(rings)}.")


def seed_synthetic_history(count: int = 300, force: bool = False):
    """
    Seeds ~300 longitudinal claims across 90 days with data_source='synthetic_history'.
    Includes realistic weekend dips and a 2-day spike.
    """
    conn = get_connection()
    c_exist = conn.execute("SELECT COUNT(*) as c FROM claims WHERE data_source = 'synthetic_history'").fetchone()["c"]
    if c_exist > 0 and not force:
        print(f"Synthetic history already present ({c_exist} claims); skipping.")
        conn.close()
        return

    if force:
        conn.execute("DELETE FROM evidence WHERE result_id LIKE 'RES-SYN-%'")
        conn.execute("DELETE FROM results WHERE data_source = 'synthetic_history' OR id LIKE 'RES-SYN-%'")
        conn.execute("DELETE FROM claims WHERE data_source = 'synthetic_history' OR id LIKE 'CLM-SYN-%'")
        conn.commit()

    print(f"Generating {count} synthetic history claims across 90 days...")
    random.seed(42)

    claim_types = ["motor", "health", "property"]
    type_weights = [0.55, 0.35, 0.10]
    base_date = datetime.utcnow()

    # Day 14 and 15 ago have a spike
    spike_days = {14, 15}

    for i in range(count):
        # Pick random day in last 90 days
        days_ago = random.randint(1, 90)
        # Spike clustering
        if random.random() < 0.18:
            days_ago = random.choice([14, 15])

        created_dt = base_date - timedelta(days=days_ago, hours=random.randint(1, 23), minutes=random.randint(0, 59))
        weekday = created_dt.weekday()
        # Weekend dip: lower probability of claim
        if weekday in (5, 6) and random.random() < 0.40:
            created_dt = created_dt - timedelta(days=2)

        c_type = random.choices(claim_types, weights=type_weights)[0]
        
        # Risk distribution: ~75% LOW, ~18% MEDIUM, ~7% HIGH
        r_roll = random.random()
        if days_ago in spike_days and random.random() < 0.50:
            band = "HIGH"
            risk = round(random.uniform(0.68, 0.95), 4)
            status = "rejected"
        elif r_roll < 0.75:
            band = "LOW"
            risk = round(random.uniform(0.02, 0.28), 4)
            status = "approved"
        elif r_roll < 0.93:
            band = "MEDIUM"
            risk = round(random.uniform(0.36, 0.62), 4)
            status = "needs_evidence"
        else:
            band = "HIGH"
            risk = round(random.uniform(0.66, 0.92), 4)
            status = "rejected"

        cid = f"CLM-SYN-{i+1:04d}"
        rid = f"RES-SYN-{i+1:04d}"
        claimant = f"user_syn_{random.randint(1, 150)}"
        amount = round(random.uniform(8000, 250000), -2)
        created_iso = created_dt.isoformat()

        # Insert claim
        conn.execute("""
            INSERT INTO claims (
                id, result_id, claimant_user_id, claimant_name, policy_number,
                claim_type, claimed_amount, status, fast_track, data_source,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'synthetic_history', ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                result_id=excluded.result_id,
                claimant_user_id=excluded.claimant_user_id,
                claimant_name=excluded.claimant_name,
                policy_number=excluded.policy_number,
                claim_type=excluded.claim_type,
                claimed_amount=excluded.claimed_amount,
                status=excluded.status,
                fast_track=excluded.fast_track,
                data_source=excluded.data_source,
                updated_at=excluded.updated_at
        """, (
            cid, rid, claimant, f"Claimant {claimant[-3:]}", f"POL-SYN-{random.randint(1000, 9999)}",
            c_type, amount, status, 1 if band == "LOW" and random.random() < 0.35 else 0,
            created_iso, created_iso
        ))

        # Insert result
        conn.execute("""
            INSERT INTO results (
                id, mode, overall_risk, overall_band, summary, data_source, created_at
            ) VALUES (?, 'claim', ?, ?, 'Historical synthetic claim record.', 'synthetic_history', ?)
            ON CONFLICT(id) DO UPDATE SET
                mode=excluded.mode,
                overall_risk=excluded.overall_risk,
                overall_band=excluded.overall_band,
                summary=excluded.summary,
                data_source=excluded.data_source
        """, (rid, risk, band, created_iso))

        # Add risk evidence for medium/high claims
        if band in ("MEDIUM", "HIGH"):
            ev_id = random.choice(["IMG-AI-01", "DOC-LOGIC-01", "IMG-DUP-01", "CLM-X-02", "DOC-CNN-01"])
            conn.execute("""
                INSERT INTO evidence (
                    result_id, evidence_id, pipeline, source, kind,
                    raw_score, calibrated_score, weight, effective_weight, severity,
                    title, reason
                ) VALUES (?, ?, 'claim', 'synthetic', 'risk', ?, ?, 0.5, 0.5, 'high', ?, 'Synthetic anomaly signal')
            """, (rid, ev_id, risk, risk, f"Historical Signal {ev_id}"))

    conn.commit()
    conn.close()
    print("Synthetic history generation complete.")


if __name__ == "__main__":
    asyncio.run(seed_live_demo_claims())
    seed_synthetic_history(300)
