import pytest
from backend.app.detectors.story_reviewer import review_claim_story
from backend.app.schemas.result import StoryStatus, Evidence


def test_story_reviewer_consistent():
    narrative = "I was driving my car MH12AB1234 on 2026-05-10 when a bike hit the rear bumper. The repair cost ₹15000."
    form_meta = {
        "incident_date": "2026-05-10",
        "vehicle_number": "MH12AB1234",
        "claimed_amount": 15000.0
    }
    doc_facts = {
        "invoice_total": 15000.0,
        "invoice_date": "2026-05-11"
    }

    story_status, ev = review_claim_story(narrative, form_meta, doc_facts)
    assert isinstance(story_status, StoryStatus)
    assert isinstance(ev, Evidence)
    assert ev.id == "CLM-STORY-00"
    assert ev.weight == 0.0
    assert ev.kind == "info"
    assert len(story_status.consistent_points) > 0
    assert len(story_status.contradictions) == 0


def test_story_reviewer_contradictions():
    # Narrative says ₹85,000 and vehicle DL01AB9999, but form is ₹15,000 and vehicle MH12AB1234
    narrative = "The total repair cost was ₹85000 for vehicle DL01AB9999."
    form_meta = {
        "vehicle_number": "MH12AB1234",
        "claimed_amount": 15000.0
    }

    story_status, ev = review_claim_story(narrative, form_meta)
    assert len(story_status.contradictions) >= 2
    texts = [c["text"] for c in story_status.contradictions]
    assert any("85,000" in t for t in texts)
    assert any("DL01AB9999" in t for t in texts)
    # Evidence score must remain 0.0 (info only)
    assert ev.weight == 0.0
    assert ev.effective_weight == 0.0


def test_story_score_invariance():
    # Story evidence must NEVER increase overall risk score
    narrative = "Contradictory statement"
    form_meta = {"claimed_amount": 1000.0}
    doc_facts = {"invoice_total": 99999.0}

    story_status, ev = review_claim_story(narrative, form_meta, doc_facts)
    assert ev.weight == 0.0
    assert ev.raw_score == 0.0
