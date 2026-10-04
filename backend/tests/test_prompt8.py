import os
import io
import json
import pytest
import numpy as np
from PIL import Image, ImageEnhance
import piexif
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.auth import create_access_token
from backend.app.detectors.image.duplicates import (
    index_image,
    find_image_duplicates,
    remove_result_from_index,
    get_index_stats
)
from backend.app.pipelines.claim_pipeline import (
    run_claim_pipeline,
    haversine_distance_km
)
from backend.app.detectors.image.metadata import (
    dms_to_decimal,
    parse_exif_gps
)
from backend.app.services.timeline import build_evidence_timeline
from backend.app.services.orchestrator import compute_overall_score
from backend.app.scoring.quality import apply_quality_gate
from backend.app.db.database import get_connection
from backend.app.db.repository import (
    create_claim_record,
    add_claim_evidence_item,
    add_action_record
)

client = TestClient(app)

# Helper to create synthetic images
def create_test_pattern_image(color=(120, 80, 200), size=(200, 200)):
    arr = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    arr[:, :] = color
    # Add identifiable features
    arr[40:160, 40:160] = [240, 200, 50]
    arr[70:130, 70:130] = [20, 180, 240]
    return Image.fromarray(arr)

# ══════════════════════════════════════════════════════════════════
# 1. DUPLICATE & NEAR-DUPLICATE TESTS
# ══════════════════════════════════════════════════════════════════

def test_duplicates_engine_variations():
    from backend.app.detectors.image.duplicates import rebuild_duplicate_index
    rebuild_duplicate_index()
    # Clean previous runs
    remove_result_from_index("RES-TEST-101")

    # Base image from Ravi, Claim 101
    img_base = create_test_pattern_image((100, 50, 150))
    idx_id = index_image(
        image=img_base,
        claim_id="CLM-TEST-101",
        claimant_id="user_ravi",
        result_id="RES-TEST-101",
        slot="damage_front"
    )
    assert idx_id is not None

    # A) Exact copy from another claimant (Sunita, Claim 202) -> Match found
    dups_exact = find_image_duplicates(
        image=img_base,
        current_claim_id="CLM-TEST-202",
        current_claimant_id="user_sunita",
        current_slot="damage_front"
    )
    dups_exact = [d for d in dups_exact if d['other_claim_id'].startswith('CLM-TEST')]
    assert len(dups_exact) > 0
    assert dups_exact[0]["match_type"] == "exact"
    assert dups_exact[0]["other_claim_id"] == "CLM-TEST-101"

    # B) Resized copy (e.g. 150x150)
    img_resized = img_base.resize((150, 150))
    dups_resized = find_image_duplicates(
        image=img_resized,
        current_claim_id="CLM-TEST-203",
        current_claimant_id="user_sunita"
    )
    dups_resized = [d for d in dups_resized if d['other_claim_id'].startswith('CLM-TEST')]
    assert len(dups_resized) > 0
    assert dups_resized[0]["other_claim_id"] == "CLM-TEST-101"

    # C) Cropped copy (center crop 80%)
    w, h = img_base.size
    img_cropped = img_base.crop((int(w * 0.1), int(h * 0.1), int(w * 0.9), int(h * 0.9)))
    dups_cropped = find_image_duplicates(
        image=img_cropped,
        current_claim_id="CLM-TEST-204",
        current_claimant_id="user_sunita"
    )
    dups_cropped = [d for d in dups_cropped if d['other_claim_id'].startswith('CLM-TEST')]
    assert len(dups_cropped) > 0
    assert dups_cropped[0]["other_claim_id"] == "CLM-TEST-101"

    # D) Recoloured / Brightened copy
    enhancer = ImageEnhance.Brightness(img_base)
    img_recoloured = enhancer.enhance(1.2)
    dups_recoloured = find_image_duplicates(
        image=img_recoloured,
        current_claim_id="CLM-TEST-205",
        current_claimant_id="user_sunita"
    )
    dups_recoloured = [d for d in dups_recoloured if d['other_claim_id'].startswith('CLM-TEST')]
    assert len(dups_recoloured) > 0
    assert dups_recoloured[0]["other_claim_id"] == "CLM-TEST-101"

    # E) Horizontally flipped copy
    img_flipped = img_base.transpose(Image.FLIP_LEFT_RIGHT)
    dups_flipped = find_image_duplicates(
        image=img_flipped,
        current_claim_id="CLM-TEST-206",
        current_claimant_id="user_sunita"
    )
    dups_flipped = [d for d in dups_flipped if d['other_claim_id'].startswith('CLM-TEST')]
    assert len(dups_flipped) > 0
    assert dups_flipped[0]["other_claim_id"] == "CLM-TEST-101"

    # F) Completely unrelated image -> NOT found
    unrelated_arr = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
    img_unrelated = Image.fromarray(unrelated_arr)
    dups_unrelated = find_image_duplicates(
        image=img_unrelated,
        current_claim_id="CLM-TEST-207",
        current_claimant_id="user_sunita"
    )
    dups_unrelated = [d for d in dups_unrelated if d['other_claim_id'].startswith('CLM-TEST')]
    assert len(dups_unrelated) == 0

    # G) Same claim match MUST be ignored
    dups_same_claim = find_image_duplicates(
        image=img_base,
        current_claim_id="CLM-TEST-101",
        current_claimant_id="user_ravi",
        current_slot="damage_side"
    )
    dups_same_claim = [d for d in dups_same_claim if d['other_claim_id'].startswith('CLM-TEST')]
    dups_same_claim = [d for d in dups_same_claim if d["other_claim_id"].startswith("CLM-TEST")]
    assert len(dups_same_claim) == 0

    # H) Same claimant resubmission of SAME slot MUST be ignored
    dups_same_claimant_slot = find_image_duplicates(
        image=img_base,
        current_claim_id="CLM-TEST-102",
        current_claimant_id="user_ravi",
        current_slot="damage_front"
    )
    dups_same_claimant_slot = [d for d in dups_same_claimant_slot if d['other_claim_id'].startswith('CLM-TEST')]
    assert len(dups_same_claimant_slot) == 0

    # I) Deleting result removes index entries
    remove_result_from_index("RES-TEST-101")
    dups_after_delete = find_image_duplicates(
        image=img_base,
        current_claim_id="CLM-TEST-202",
        current_claimant_id="user_sunita"
    )
    dups_after_delete = [d for d in dups_after_delete if d['other_claim_id'].startswith('CLM-TEST')]
    assert len(dups_after_delete) == 0

# ══════════════════════════════════════════════════════════════════
# 2. CROSS-CHECKS & MATHEMATICAL UNIT TESTS (§14)
# ══════════════════════════════════════════════════════════════════

def test_haversine_known_distances():
    # Mumbai to Delhi: ~1148 km
    dist_mum_del = haversine_distance_km(19.0760, 72.8777, 28.6139, 77.2090)
    assert 1130 <= dist_mum_del <= 1170

    # Delhi to Bangalore: ~1740 km
    dist_del_blr = haversine_distance_km(28.6139, 77.2090, 12.9716, 77.5946)
    assert 1720 <= dist_del_blr <= 1760

    # Same location: 0 km
    assert haversine_distance_km(12.9716, 77.5946, 12.9716, 77.5946) == 0.0

def test_dms_to_decimal_conversions():
    # 12 deg 58 min 17.76 sec North -> 12.9716
    deg = dms_to_decimal(((12, 1), (58, 1), (1776, 100)), 'N')
    assert round(deg, 4) == 12.9716

    # South must be negative
    deg_s = dms_to_decimal(((12, 1), (58, 1), (1776, 100)), 'S')
    assert round(deg_s, 4) == -12.9716

    # 77 deg 35 min 40.56 sec East -> 77.5946
    deg_e = dms_to_decimal(((77, 1), (35, 1), (4056, 100)), 'E')
    assert round(deg_e, 4) == 77.5946

    # West must be negative
    deg_w = dms_to_decimal(((77, 1), (35, 1), (4056, 100)), 'W')
    assert round(deg_w, 4) == -77.5946

def test_all_claim_pipeline_rules():
    # 1. CLM-X-01: Photo date before incident
    res_x01 = run_claim_pipeline(
        claim_metadata={"incident_date": "2026-06-15"},
        images_metadata=[{"exif_datetime": "2026-05-10 14:00:00", "slot": "front"}]
    )
    ids_x01 = [e.id for e in res_x01.evidence]
    assert "CLM-X-01" in ids_x01
    assert any("36 days" in e.reason for e in res_x01.evidence if e.id == "CLM-X-01")

    # 2. CLM-X-06: GPS distance > 50km
    res_x06 = run_claim_pipeline(
        claim_metadata={
            "incident_location": {"lat": 19.0760, "lng": 72.8777} # Mumbai
        },
        images_metadata=[{
            "gps_lat": 12.9716, "gps_lng": 77.5946, "slot": "photo_1" # Bangalore (~842 km)
        }]
    )
    ids_x06 = [e.id for e in res_x06.evidence]
    assert "CLM-X-06" in ids_x06
    ev_x06 = next(e for e in res_x06.evidence if e.id == "CLM-X-06")
    assert ev_x06.details["distance_km"] > 800

    # 3. CLM-X-02: Claimed amount exceeds bill total
    res_x02 = run_claim_pipeline(
        claim_metadata={"claimed_amount": 75000.0},
        doc_extracted_fields={"total_amount": 45000.0}
    )
    ids_x02 = [e.id for e in res_x02.evidence]
    assert "CLM-X-02" in ids_x02
    ev_x02 = next(e for e in res_x02.evidence if e.id == "CLM-X-02")
    assert ev_x02.details["delta"] == 30000.0

    # 4. CLM-X-08: Invoice date before incident date
    res_x08 = run_claim_pipeline(
        claim_metadata={"incident_date": "2026-07-20"},
        doc_extracted_fields={"invoice_date": "2026-07-10"}
    )
    ids_x08 = [e.id for e in res_x08.evidence]
    assert "CLM-X-08" in ids_x08

    # 5. CLM-CHRONO-01: Medical chronology contradiction (discharge before admission)
    res_chrono = run_claim_pipeline(
        doc_extracted_fields={
            "admission_date": "2026-08-15",
            "discharge_date": "2026-08-10"
        }
    )
    ids_chrono = [e.id for e in res_chrono.evidence]
    assert "CLM-CHRONO-01" in ids_chrono

    # 6. CLM-X-03: Bill name mismatch vs policyholder
    res_x03 = run_claim_pipeline(
        claim_metadata={"claimant_name": "Ravi Kumar"},
        doc_extracted_fields={"patient_name": "Suresh Raina"}
    )
    ids_x03 = [e.id for e in res_x03.evidence]
    assert "CLM-X-03" in ids_x03

    # 7. CLM-X-07: Incident date outside policy validity
    res_x07 = run_claim_pipeline(
        claim_metadata={
            "incident_date": "2026-10-01",
            "policy_start": "2025-01-01",
            "policy_end": "2025-12-31"
        }
    )
    ids_x07 = [e.id for e in res_x07.evidence]
    assert "CLM-X-07" in ids_x07

    # 8. CLM-VEH-01: Vehicle number mismatch
    res_veh = run_claim_pipeline(
        claim_metadata={"policy_number": "POL-MOT-8821", "vehicle_registration": "KA-01-MJ-5000"},
        doc_extracted_fields={"vehicle_registration": "MH-02-CB-1234"}
    )
    ids_veh = [e.id for e in res_veh.evidence]
    assert "CLM-VEH-01" in ids_veh

    # 9. CLM-ID-01: ID name vs policyholder mismatch
    res_id = run_claim_pipeline(
        claim_metadata={"claimant_name": "Ravi Kumar"},
        identity_info={"verified_name": "Amit Shah"}
    )
    ids_id = [e.id for e in res_id.evidence]
    assert "CLM-ID-01" in ids_id

    # 10. Missing data skipped, never failing
    res_empty = run_claim_pipeline(
        claim_metadata={},
        images_metadata=[],
        doc_extracted_fields={},
        identity_info={}
    )
    assert len(res_empty.evidence) == 0
    assert res_empty.score.risk == 0.05
    # Checks run should report skipped
    skipped_checks = [c for c in res_empty.checks_run if c.status == "skipped"]
    assert len(skipped_checks) > 0

# ══════════════════════════════════════════════════════════════════
# 3. EVIDENCE TIMELINE & CONTRADICTION TESTS (§14.3)
# ══════════════════════════════════════════════════════════════════

def test_evidence_timeline_ordering_and_contradictions():
    events_raw = [
        {"timestamp": "2026-06-15T14:30:00", "label": "Claimed Incident", "kind": "incident", "source": "claimant"},
        {"timestamp": "2026-05-10T10:00:00", "label": "Photo Captured", "kind": "photo_captured", "source": "exif"},
        {"timestamp": "2026-07-01", "label": "Repair Estimate Issued", "kind": "document_date", "source": "document text"},
        {"timestamp": None, "label": "Undated Tow Receipt", "kind": "receipt", "source": "document text"}
    ]
    contradictions_raw = [
        {
            "from_rule": "CLM-X-01",
            "message": "Photo timestamp is 36 days before claimed incident",
            "evidence_id": "CLM-X-01"
        }
    ]

    timeline = build_evidence_timeline(events_raw, contradictions_raw)
    
    # 1. Chronological sorting: 2026-05-10 must come first, then 2026-06-15, then 2026-07-01
    dated_events = timeline["events"]
    assert len(dated_events) == 3
    assert dated_events[0]["label"] == "Photo Captured"
    assert dated_events[1]["label"] == "Claimed Incident"
    assert dated_events[2]["label"] == "Repair Estimate Issued"

    # 2. Undated items grouped separately
    assert len(timeline["undated"]) == 1
    assert timeline["undated"][0]["label"] == "Undated Tow Receipt"

    # 3. Contradiction connector linked
    assert len(timeline["contradictions"]) == 1
    c_link = timeline["contradictions"][0]
    assert c_link["from_event"] == 0 # Photo Captured
    assert c_link["to_event"] == 1   # Claimed Incident

# ══════════════════════════════════════════════════════════════════
# 4. R_CLAIM FUSION & OVERALL SCORE BLEND (§15.5)
# ══════════════════════════════════════════════════════════════════

def test_r_claim_participates_in_blend():
    # Overall blend formula: 0.7 * max(R_i) + 0.3 * mean(R_i)
    # Suppose image risk is 0.10, doc risk is 0.10, but claim cross-check R_claim is 0.90
    pipeline_risks = {
        "image": 0.10,
        "document": 0.10,
        "claim": 0.90
    }
    # max = 0.90, mean = (0.10 + 0.10 + 0.90) / 3 = 1.10 / 3 = 0.3667
    # blend = 0.7 * 0.90 + 0.3 * 0.3667 = 0.63 + 0.11 = 0.74
    overall_risk = compute_overall_score(pipeline_risks)
    assert round(overall_risk, 2) == 0.74

def test_quality_gates_apply_to_r_claim():
    # When high_ocr_failure_rate is set, CLM-X-02 weight is discounted by 50% (0.5 gate)
    eff_weight, factor = apply_quality_gate("CLM-X-02", raw_weight=0.60, quality_flags={"high_ocr_failure_rate": True})
    assert factor == 0.5
    assert eff_weight == 0.30

# ══════════════════════════════════════════════════════════════════
# 5. STRICT CLAIMANT PRIVACY / SAFETY SCAN
# ══════════════════════════════════════════════════════════════════

FORBIDDEN_PROMPT8_TERMS = [
    "duplicate", "gps", "timeline contradiction", "contradiction",
    "recycled", "cross-check", "clm-x-", "img-dup-", "doc-dup-"
]

def assert_no_leaks(data, path=""):
    if isinstance(data, dict):
        for k, v in data.items():
            curr_path = f"{path}.{k}" if path else str(k)
            for t in FORBIDDEN_PROMPT8_TERMS:
                assert t not in str(k).lower(), f"Leaked '{t}' in key {curr_path}"
            assert_no_leaks(v, curr_path)
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            assert_no_leaks(item, f"{path}[{idx}]")
    elif isinstance(data, str):
        for t in FORBIDDEN_PROMPT8_TERMS:
            assert t not in data.lower(), f"Leaked '{t}' in string: {data}"

def test_claimant_safety_endpoints_prompt8():
    token = create_access_token({"sub": "user_ravi", "role": "claimant"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. GET /claims/mine
    res_mine = client.get("/api/v1/claims/mine", headers=headers)
    assert res_mine.status_code == 200
    assert_no_leaks(res_mine.json(), "/claims/mine")

    # 2. GET /claims/claim_demo_01/status
    res_status = client.get("/api/v1/claims/claim_demo_01/status", headers=headers)
    if res_status.status_code == 200:
        assert_no_leaks(res_status.json(), "/claims/{id}/status")

    # 3. GET /claims/claim_demo_01/evidence-timeline
    res_tl = client.get("/api/v1/claims/claim_demo_01/evidence-timeline", headers=headers)
    if res_tl.status_code == 200:
        assert_no_leaks(res_tl.json(), "/claims/{id}/evidence-timeline")
