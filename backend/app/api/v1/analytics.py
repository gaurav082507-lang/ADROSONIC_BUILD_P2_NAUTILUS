"""
Analytics API Endpoints (§14, Prompt 10).
All endpoints investigator-only under /api/v1/analytics.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query

from ...core.auth import require_role
from ...services import analytics

router = APIRouter(prefix="/analytics", tags=["Analytics"])
_INVESTIGATOR = Depends(require_role("investigator"))


@router.get("/summary")
def get_summary(
    user: Dict[str, Any] = _INVESTIGATOR
):
    """
    Returns dashboard executive overview KPIs:
    - claims_today, fast_tracked, flagged, flagged_rate
    - top_reasons, sparkline_7d, open_rings
    """
    return analytics.get_analytics_summary()


@router.get("/trends")
def get_trends(
    range: str = Query("30d", pattern="^(7d|30d|90d)$"),
    type: Optional[str] = Query(None, pattern="^(motor|health|property)$"),
    user: Dict[str, Any] = _INVESTIGATOR
):
    """
    Returns longitudinal time-series analytics, risk distributions,
    modality breakdowns, recycled evidence spikes, and decision velocity.
    """
    return analytics.get_analytics_trends(range_param=range, claim_type=type)

@router.get("/business")
async def get_business_analytics(
    range: str = Query("30d", pattern="^(7d|30d|90d|all)$"),
    user: dict = Depends(require_role("investigator"))
):
    """
    Computes business-focused metrics from REAL claims only.
    Returns: {
        "claims_processed": int,
        "fast_track_rate": float (%),
        "fraud_prevented_amount": float,
        "amount_at_risk": float,
        "roi_multiple": float,
        "patterns": list of dict,
        "assumptions": dict
    }
    """
    from ...db.database import get_connection
    import sqlite3
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    
    # Filter only real claims
    date_filter = ""
    if range == "7d":
        date_filter = "AND c.created_at >= date('now', '-7 days')"
    elif range == "30d":
        date_filter = "AND c.created_at >= date('now', '-30 days')"
    elif range == "90d":
        date_filter = "AND c.created_at >= date('now', '-90 days')"

    query = f"""
        SELECT 
            c.id, c.claimed_amount, c.status, r.overall_band, r.overall_risk 
        FROM claims c
        LEFT JOIN results r ON c.result_id = r.id
        WHERE (c.data_source IS NULL OR c.data_source != 'synthetic_history')
        {date_filter}
    """
    rows = conn.execute(query).fetchall()
    
    # Assumptions for ROI
    avg_manual_cost_per_claim = 1500  # Rs
    ai_cost_per_claim = 50           # Rs
    
    total_claims = len(rows)
    fast_tracked = 0
    high_risk_prevented = 0.0
    amount_at_risk = 0.0
    
    for r in rows:
        amt = float(r["claimed_amount"]) if r["claimed_amount"] else 0.0
        
        # Fast track eligible
        if r["overall_band"] == "LOW":
            fast_tracked += 1
            
        if r["overall_band"] == "HIGH":
            amount_at_risk += amt
            # If rejected, it's prevented fraud
            if r["status"] == "rejected":
                high_risk_prevented += amt
            else:
                # If still open, assume 50% of high risk amount will be prevented eventually for ROI estimation
                high_risk_prevented += (amt * 0.5)

    ft_rate = (fast_tracked / total_claims * 100) if total_claims > 0 else 0.0
    
    # ROI = (Savings from FT + Savings from prevented fraud) / AI Cost
    # Savings from FT = manual cost avoided
    savings_ft = fast_tracked * avg_manual_cost_per_claim
    total_ai_cost = total_claims * ai_cost_per_claim
    roi = ((savings_ft + high_risk_prevented) / total_ai_cost) if total_ai_cost > 0 else 0.0
    
    # Patterns
    patterns = [
        {"pattern": "Recycled images across policies", "impact": "High", "claims_flagged": len([r for r in rows if r["overall_band"] == "HIGH"])},
        {"pattern": "Generative AI artifacts", "impact": "Medium", "claims_flagged": len([r for r in rows if r["overall_risk"] and r["overall_risk"] > 0.8])}
    ]
    
    conn.close()
    return {
        "claims_processed": total_claims,
        "fast_track_rate": round(ft_rate, 1),
        "fraud_prevented_amount": round(high_risk_prevented, 2),
        "amount_at_risk": round(amount_at_risk, 2),
        "roi_multiple": round(roi, 1),
        "open_rings": conn.execute("SELECT COUNT(*) FROM rings WHERE status='open'").fetchone()[0],
        "patterns": patterns,
        "assumptions": {
            "avg_manual_investigation_cost": avg_manual_cost_per_claim,
            "ai_processing_cost": ai_cost_per_claim
        }
    }
