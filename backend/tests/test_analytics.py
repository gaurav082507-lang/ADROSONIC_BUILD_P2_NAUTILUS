import pytest
from backend.app.services.analytics import get_analytics_summary, get_analytics_trends


def test_analytics_summary():
    summary = get_analytics_summary()
    assert isinstance(summary, dict)
    for key in ("claims_today", "fast_tracked", "flagged_rate", "top_reasons", "sparkline_7d", "open_rings"):
        assert key in summary
    assert isinstance(summary["sparkline_7d"], list)
    assert len(summary["sparkline_7d"]) == 7
    assert 0.0 <= summary["flagged_rate"] <= 1.0


def test_analytics_trends_ranges():
    trends_7d = get_analytics_trends(range_param="7d")
    assert len(trends_7d["daily"]) == 7

    trends_30d = get_analytics_trends(range_param="30d")
    assert len(trends_30d["daily"]) == 30

    trends_90d = get_analytics_trends(range_param="90d")
    assert len(trends_90d["daily"]) == 90

    # Check structure
    for key in ("daily", "top_signals", "by_type", "by_modality", "recycled_evidence_weekly", "rings_weekly", "decisions_weekly", "spike"):
        assert key in trends_30d

    # Spike alert structure
    assert "detected" in trends_30d["spike"]
    assert isinstance(trends_30d["spike"]["detected"], bool)


def test_analytics_trends_claim_type_filter():
    trends_motor = get_analytics_trends(range_param="30d", claim_type="motor")
    assert "daily" in trends_motor
    # Verify by_type has motor if claims exist
    types_found = [item["type"] for item in trends_motor.get("by_type", [])]
    if types_found:
        assert "motor" in types_found
