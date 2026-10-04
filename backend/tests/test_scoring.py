from app.scoring.fusion import compute_fusion, compute_fusion_with_contributions
from app.scoring.overall import compute_overall_score
from app.scoring.overrides import apply_overrides, apply_overrides_with_entries
from app.scoring.bands import get_band, determine_confidence, get_severity

def test_worked_example_15_8():
    # 1. Image (claim photo)
    ev_img = [
        {"id": "IMG-AI-01", "kind": "risk", "effective_weight": 0.70, "calibrated_score": 0.97, "source": "ai_detector"},
        {"id": "IMG-ELA-01", "kind": "risk", "effective_weight": 0.25, "calibrated_score": 0.70, "source": "forensics"},
        {"id": "IMG-EXIF-01", "kind": "risk", "effective_weight": 0.10, "calibrated_score": 0.50, "source": "metadata"}
    ]
    r_img, contribs = compute_fusion_with_contributions(ev_img)
    # terms: 0.97*0.70 = 0.679; 0.70*0.25 = 0.175; 0.50*0.10 = 0.050
    # risk_img = 1 - (1-0.679)(1-0.175)(1-0.050) = 1 - 0.321*0.825*0.95 ≈ 0.748
    assert abs(r_img - 0.748) < 0.005
    assert get_band(r_img) == "HIGH"
    # Contributions must sum to fused risk
    assert abs(sum(contribs.values()) - r_img) < 0.001

    # 2. Document (invoice)
    ev_doc = [
        {"id": "DOC-LOGIC-01", "kind": "risk", "effective_weight": 0.80, "calibrated_score": 1.00, "source": "rules"},
        {"id": "DOC-CNN-01", "kind": "risk", "effective_weight": 0.50, "calibrated_score": 0.75, "source": "forensics"},
        {"id": "DOC-FONT-01", "kind": "risk", "effective_weight": 0.30, "calibrated_score": 0.60, "source": "rules"},
        {"id": "DOC-META-02", "kind": "risk", "effective_weight": 0.15, "calibrated_score": 0.50, "source": "metadata"}
    ]
    r_doc = compute_fusion(ev_doc)
    # P0-5 forensics cap=0.30 applies to DOC-CNN-01 (source=forensics, term=0.375 > 0.30 → capped):
    # forensics_risk = 0.30 (capped from 0.375)
    # rules_risk = 1 - (1-0.80)*(1-0.18) = 0.836
    # metadata_risk = 0.075 (< 0.40 cap, not capped)
    # r_doc = 1 - (1-0.30)*(1-0.836)*(1-0.075) ≈ 0.8938
    assert abs(r_doc - 0.8938) < 0.005
    assert get_band(r_doc) == "HIGH"

    # 3. Overall blend
    # 0.7 * max(0.748, 0.8938) + 0.3 * mean(0.748, 0.8938) ≈ 0.872
    r_overall = compute_overall_score([r_img, r_doc])
    assert abs(r_overall - 0.872) < 0.005
    assert get_band(r_overall) == "HIGH"

    # 4. Genuine image contrast (§15.8)
    # IMG-AI-01 (p 0.05, w 0.65) below 0.2 -> excluded
    # IMG-ELA-01 (p 0.10, w 0.25) below 0.2 -> excluded
    # IMG-EXIF-01 (p 0.50, w 0.10) -> term = 0.05
    ev_genuine = [
        {"id": "IMG-AI-01", "kind": "risk", "effective_weight": 0.65, "calibrated_score": 0.05, "source": "ai_detector"},
        {"id": "IMG-ELA-01", "kind": "risk", "effective_weight": 0.25, "calibrated_score": 0.10, "source": "forensics"},
        {"id": "IMG-EXIF-01", "kind": "risk", "effective_weight": 0.10, "calibrated_score": 0.50, "source": "metadata"}
    ]
    r_genuine = compute_fusion(ev_genuine)
    assert abs(r_genuine - 0.05) < 0.005
    assert get_band(r_genuine) == "LOW"

def test_participation_threshold():
    # p < 0.2 is excluded
    ev1 = [{"id": "E1", "kind": "risk", "effective_weight": 0.8, "calibrated_score": 0.19, "source": "s1"}]
    assert compute_fusion(ev1) == 0.0

    # w * p < 0.02 is excluded
    ev2 = [{"id": "E2", "kind": "risk", "effective_weight": 0.05, "calibrated_score": 0.30, "source": "s1"}]
    assert compute_fusion(ev2) == 0.0

    # Meets both: p >= 0.2 and w*p >= 0.02
    ev3 = [{"id": "E3", "kind": "risk", "effective_weight": 0.10, "calibrated_score": 0.20, "source": "s1"}]
    assert compute_fusion(ev3) == 0.02

def test_per_source_caps():
    # Metadata cap: 0.4
    ev_meta = [
        {"id": "M1", "kind": "risk", "effective_weight": 0.8, "calibrated_score": 0.8, "source": "metadata"},
        {"id": "M2", "kind": "risk", "effective_weight": 0.8, "calibrated_score": 0.8, "source": "metadata"},
    ]
    assert abs(compute_fusion(ev_meta) - 0.40) < 0.005

    # Aadhaar QR cap: 0.85
    ev_qr = [{"id": "Q1", "kind": "risk", "effective_weight": 1.0, "calibrated_score": 1.0, "source": "aadhaar_qr"}]
    assert abs(compute_fusion(ev_qr) - 0.85) < 0.005

    # Liveness cap: 0.75
    ev_live = [{"id": "L1", "kind": "risk", "effective_weight": 1.0, "calibrated_score": 1.0, "source": "liveness"}]
    assert abs(compute_fusion(ev_live) - 0.75) < 0.005

    # Voice cap: 0.55
    ev_voi = [{"id": "V1", "kind": "risk", "effective_weight": 1.0, "calibrated_score": 1.0, "source": "voice"}]
    assert abs(compute_fusion(ev_voi) - 0.55) < 0.005

    # Story cap: 0.25
    ev_story = [{"id": "S1", "kind": "risk", "effective_weight": 1.0, "calibrated_score": 1.0, "source": "llm_story"}]
    assert abs(compute_fusion(ev_story) - 0.25) < 0.005

    # Forensics cap: 0.30 (DOC-CNN-01, P0-5)
    ev_forensics = [{"id": "F1", "kind": "risk", "effective_weight": 1.0, "calibrated_score": 1.0, "source": "forensics"}]
    assert abs(compute_fusion(ev_forensics) - 0.30) < 0.005

    # Forensics cap lifted when source in corroborated_sources
    r_lifted, _ = compute_fusion_with_contributions(ev_forensics, corroborated_sources={"forensics"})
    assert abs(r_lifted - 1.0) < 0.005

def test_band_boundaries():
    assert get_band(0.0) == "LOW"
    assert get_band(0.349) == "LOW"
    assert get_band(0.35) == "MEDIUM"
    assert get_band(0.649) == "MEDIUM"
    assert get_band(0.65) == "HIGH"
    assert get_band(1.0) == "HIGH"

def test_override_rules_o1_to_o7():
    # O1: IMG-C2PA-01 -> >= 0.95
    assert apply_overrides(["IMG-C2PA-01"], 0.20, "image") == 0.95

    # O2: DOC-LOGIC-01 and DOC-CNN-01 -> >= 0.85
    assert apply_overrides(["DOC-LOGIC-01", "DOC-CNN-01"], 0.40, "document") == 0.85
    # O2 does not trigger with only one
    assert apply_overrides(["DOC-LOGIC-01"], 0.40, "document") == 0.40

    # O3: ID-FACE-01 -> >= 0.80
    assert apply_overrides(["ID-FACE-01"], 0.30, "overall") == 0.80

    # O4: IMG-DUP-01 -> >= 0.90
    assert apply_overrides(["IMG-DUP-01"], 0.10, "overall") == 0.90

    # O5: DOC-OVERLAY-01 -> >= 0.80
    assert apply_overrides(["DOC-OVERLAY-01"], 0.25, "document") == 0.80

    # O6: ID-LIVE-01 and ID-FACE-01 -> >= 0.85
    assert apply_overrides(["ID-LIVE-01", "ID-FACE-01"], 0.50, "overall") == 0.85

    # O7: ID-QR-01 -> >= 0.85
    assert apply_overrides(["ID-QR-01"], 0.20, "identity") == 0.85

    # Visible entries recorded
    risk, entries = apply_overrides_with_entries(["IMG-C2PA-01"], 0.20, "image")
    assert len(entries) == 1
    assert entries[0]["rule"] == "O1"

def test_zero_weight_evidence_never_scores():
    # ID-QR-04 (unreadable QR) has weight 0.0 -> must never raise risk
    ev_qr4 = [{"id": "ID-QR-04", "kind": "info", "effective_weight": 0.0, "calibrated_score": 1.0, "source": "aadhaar_qr"}]
    assert compute_fusion(ev_qr4) == 0.0

    # CLM-STORY-00 (story narrative) has weight 0.0, kind="info" -> must never change score
    ev_story = [{"id": "CLM-STORY-00", "kind": "info", "effective_weight": 0.0, "calibrated_score": 0.8, "source": "llm_story"}]
    assert compute_fusion(ev_story) == 0.0

def test_confidence_downgrades():
    # Starts at high
    assert determine_confidence([], initial_conf="high") == "high"

    # Step down on failed detector
    assert determine_confidence([], detector_statuses=[{"status": "failed"}]) == "medium"

    # Step down on QR-04
    assert determine_confidence(["ID-QR-04"], initial_conf="high") == "medium"

    # Step down on liveness missing
    assert determine_confidence([], liveness_missing_on_id=True, initial_conf="high") == "medium"

    # Two adverse conditions step down from high to low
    assert determine_confidence(["ID-QR-04"], detector_statuses=[{"status": "failed"}], initial_conf="high") == "low"

def test_severity_levels():
    assert get_severity(0.8, 0.7) == "high"    # 0.56 >= 0.5
    assert get_severity(0.5, 0.5) == "medium"  # 0.25 >= 0.2
    assert get_severity(0.1, 0.5) == "low"     # 0.05 < 0.2
