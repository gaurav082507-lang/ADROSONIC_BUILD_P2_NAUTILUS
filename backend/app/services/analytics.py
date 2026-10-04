"""
Analytics & Fraud Intelligence Service (§14, §15, §16, Prompt 10).
Provides summary KPIs, operational sparklines, and 7d/30d/90d longitudinal trends.
Supports filtering by claim type and date ranges. Detects localized fraud spikes.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict

from ..db.database import get_connection

logger = logging.getLogger(__name__)


def get_analytics_summary() -> Dict[str, Any]:
    """
    Computes dashboard overview metrics:
    - claims_today, fast_tracked, flagged, flagged_rate
    - top_reasons, sparkline_7d, open_rings
    """
    conn = get_connection()
    today_prefix = datetime.utcnow().strftime("%Y-%m-%d")

    # Claims today
    row_today = conn.execute(
        "SELECT COUNT(*) as c FROM claims WHERE created_at LIKE ?",
        (f"{today_prefix}%",)
    ).fetchone()
    claims_today = int(row_today["c"]) if row_today else 0

    # Fast-tracked
    row_ft = conn.execute(
        "SELECT COUNT(*) as c FROM claims WHERE fast_track = 1"
    ).fetchone()
    fast_tracked = int(row_ft["c"]) if row_ft else 0

    # Total and flagged (overall_band in ('MEDIUM', 'HIGH'))
    row_flagged = conn.execute("""
        SELECT
            COUNT(c.id) as total,
            SUM(CASE WHEN r.overall_band IN ('MEDIUM', 'HIGH') THEN 1 ELSE 0 END) as flagged
        FROM claims c
        LEFT JOIN results r ON c.result_id = r.id
    """).fetchone()

    total_claims = int(row_flagged["total"]) if row_flagged and row_flagged["total"] else 0
    flagged = int(row_flagged["flagged"]) if row_flagged and row_flagged["flagged"] else 0
    flagged_rate = round(flagged / max(1, total_claims), 3)

    # Top reasons from evidence table
    reason_rows = conn.execute("""
        SELECT evidence_id, title, COUNT(*) as cnt
        FROM evidence
        WHERE kind = 'risk'
        GROUP BY evidence_id, title
        ORDER BY cnt DESC
        LIMIT 5
    """).fetchall()

    top_reasons = [{
        "id": r["evidence_id"],
        "title": r["title"] or r["evidence_id"],
        "count": int(r["cnt"])
    } for r in reason_rows]

    # Sparkline: last 7 days of claim volume
    sparkline_7d: List[int] = []
    base_date = datetime.utcnow().date()
    for i in range(6, -1, -1):
        d_str = (base_date - timedelta(days=i)).strftime("%Y-%m-%d")
        r_d = conn.execute(
            "SELECT COUNT(*) as c FROM claims WHERE created_at LIKE ?",
            (f"{d_str}%",)
        ).fetchone()
        sparkline_7d.append(int(r_d["c"]) if r_d else 0)

    # Open rings count
    row_rings = conn.execute("SELECT COUNT(*) as c FROM rings WHERE status = 'open'").fetchone()
    open_rings = int(row_rings["c"]) if row_rings else 0

    conn.close()

    return {
        "claims_today": claims_today,
        "fast_tracked": fast_tracked,
        "flagged": flagged,
        "flagged_rate": flagged_rate,
        "top_reasons": top_reasons,
        "sparkline_7d": sparkline_7d,
        "open_rings": open_rings
    }


def get_analytics_trends(
    range_param: str = "30d",
    claim_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes time-series trend breakdowns:
    - daily: [{date, low, medium, high, flagged_rate, avg_risk}]
    - top_signals: [{id, title, count}]
    - by_type: [{type, total, flagged}]
    - by_modality: [{modality, flagged}]
    - recycled_evidence_weekly: [{week, count}]
    - rings_weekly: [{week, count}]
    - decisions_weekly: [{week, approved, rejected, requested}]
    - spike: {detected, message}
    """
    days = 30
    if range_param == "7d":
        days = 7
    elif range_param == "90d":
        days = 90

    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    conn = get_connection()

    where_clauses = ["c.created_at >= ?"]
    params: List[Any] = [cutoff]
    if claim_type:
        where_clauses.append("c.claim_type = ?")
        params.append(claim_type)

    where_sql = " AND ".join(where_clauses)

    claims_rows = conn.execute(f"""
        SELECT c.id, c.claim_type, c.created_at, r.overall_risk, r.overall_band,
               c.status as claim_status
        FROM claims c
        LEFT JOIN results r ON c.result_id = r.id
        WHERE {where_sql}
        ORDER BY c.created_at ASC
    """, params).fetchall()

    # Daily aggregation
    daily_map = defaultdict(lambda: {"low": 0, "medium": 0, "high": 0, "risks": []})
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days - 1)

    cur = start_date
    while cur <= end_date:
        d_str = cur.strftime("%Y-%m-%d")
        daily_map[d_str] = {"low": 0, "medium": 0, "high": 0, "risks": []}
        cur += timedelta(days=1)

    by_type_map = defaultdict(lambda: {"total": 0, "flagged": 0})
    decisions_weekly_map = defaultdict(lambda: {"approved": 0, "rejected": 0, "requested": 0})

    for r in claims_rows:
        dt_full = r["created_at"] or ""
        dt_str = dt_full[:10]
        band = (r["overall_band"] or "LOW").upper()
        risk = float(r["overall_risk"] or 0.0)
        ctype = r["claim_type"] or "motor"

        if dt_str in daily_map:
            if band == "HIGH":
                daily_map[dt_str]["high"] += 1
            elif band == "MEDIUM":
                daily_map[dt_str]["medium"] += 1
            else:
                daily_map[dt_str]["low"] += 1
            daily_map[dt_str]["risks"].append(risk)

        by_type_map[ctype]["total"] += 1
        if band in ("MEDIUM", "HIGH"):
            by_type_map[ctype]["flagged"] += 1

        # Decisions by week
        if dt_full:
            try:
                dt_obj = datetime.fromisoformat(dt_full.replace("Z", "+00:00"))
                week_key = dt_obj.strftime("%Y-W%U")
                status = (r["claim_status"] or "").lower()
                if status == "approved":
                    decisions_weekly_map[week_key]["approved"] += 1
                elif status in ("rejected", "denied"):
                    decisions_weekly_map[week_key]["rejected"] += 1
                elif status in ("needs_evidence", "requested"):
                    decisions_weekly_map[week_key]["requested"] += 1
            except Exception:
                pass

    daily = []
    daily_high_counts = []
    for dt_str in sorted(daily_map.keys()):
        item = daily_map[dt_str]
        tot = item["low"] + item["medium"] + item["high"]
        flg = item["medium"] + item["high"]
        frate = round(flg / max(1, tot), 3) if tot > 0 else 0.0
        avg_r = round(sum(item["risks"]) / max(1, len(item["risks"])), 3) if item["risks"] else 0.0
        daily.append({
            "date": dt_str,
            "low": item["low"],
            "medium": item["medium"],
            "high": item["high"],
            "flagged_rate": frate,
            "avg_risk": avg_r
        })
        daily_high_counts.append(item["high"])

    # by_type list
    by_type = [
        {"type": k, "total": v["total"], "flagged": v["flagged"]}
        for k, v in by_type_map.items()
    ]
    if not by_type:
        by_type = [
            {"type": "motor", "total": 0, "flagged": 0},
            {"type": "health", "total": 0, "flagged": 0},
            {"type": "property", "total": 0, "flagged": 0}
        ]

    # Modality breakdown
    modality_rows = conn.execute("""
        SELECT pipeline, COUNT(*) as c
        FROM evidence
        WHERE kind = 'risk'
        GROUP BY pipeline
    """).fetchall()
    by_modality = [{"modality": r["pipeline"], "flagged": int(r["c"])} for r in modality_rows]
    if not by_modality:
        by_modality = [
            {"modality": "image", "flagged": 0},
            {"modality": "document", "flagged": 0},
            {"modality": "identity", "flagged": 0},
            {"modality": "voice", "flagged": 0},
            {"modality": "claim", "flagged": 0}
        ]

    # Top signals in period
    signal_rows = conn.execute("""
        SELECT e.evidence_id, e.title, COUNT(*) as cnt
        FROM evidence e
        JOIN results r ON e.result_id = r.id
        WHERE e.kind = 'risk' AND r.created_at >= ?
        GROUP BY e.evidence_id, e.title
        ORDER BY cnt DESC
        LIMIT 6
    """, (cutoff,)).fetchall()
    top_signals = [{"id": s["evidence_id"], "title": s["title"] or s["evidence_id"], "count": int(s["cnt"])} for s in signal_rows]

    # Recycled evidence weekly (IMG-DUP, DOC-DUP, CLM-X-04)
    recycled_rows = conn.execute("""
        SELECT strftime('%Y-W%W', r.created_at) as wk, COUNT(*) as cnt
        FROM evidence e
        JOIN results r ON e.result_id = r.id
        WHERE e.evidence_id IN ('IMG-DUP-01', 'IMG-DUP-02', 'DOC-DUP-01', 'CLM-X-04')
          AND r.created_at >= ?
        GROUP BY wk
        ORDER BY wk ASC
    """, (cutoff,)).fetchall()
    recycled_weekly = [{"week": r["wk"] or "Current", "count": int(r["cnt"])} for r in recycled_rows]
    if not recycled_weekly:
        recycled_weekly = [{"week": datetime.utcnow().strftime("%Y-W%W"), "count": 0}]

    # Rings weekly
    ring_rows = conn.execute("""
        SELECT strftime('%Y-W%W', created_at) as wk, COUNT(*) as cnt
        FROM rings
        WHERE created_at >= ?
        GROUP BY wk
        ORDER BY wk ASC
    """, (cutoff,)).fetchall()
    rings_weekly = [{"week": r["wk"] or "Current", "count": int(r["cnt"])} for r in ring_rows]
    if not rings_weekly:
        rings_weekly = [{"week": datetime.utcnow().strftime("%Y-W%W"), "count": 0}]

    # Decisions weekly
    decisions_weekly = [
        {"week": wk, "approved": v["approved"], "rejected": v["rejected"], "requested": v["requested"]}
        for wk, v in sorted(decisions_weekly_map.items())
    ]
    if not decisions_weekly:
        decisions_weekly = [{"week": datetime.utcnow().strftime("%Y-W%W"), "approved": 0, "rejected": 0, "requested": 0}]

    # Spike Detection:
    # If recent 2-day high count >= 3 and exceeds 2.5x baseline average
    spike_detected = False
    spike_message = "Claim volume and forensic risk signals are within normal operating bounds."
    if len(daily_high_counts) >= 4:
        recent_2d = sum(daily_high_counts[-2:])
        prior = daily_high_counts[:-2]
        avg_prior = sum(prior) / max(1, len(prior))
        if recent_2d >= 3 and (recent_2d / 2.0) > (2.5 * max(avg_prior, 0.5)):
            spike_detected = True
            spike_message = "Spike detected: sudden elevation in flagged claims and reused evidence patterns across recent filings."

    conn.close()

    return {
        "daily": daily,
        "top_signals": top_signals,
        "by_type": by_type,
        "by_modality": by_modality,
        "recycled_evidence_weekly": recycled_weekly,
        "rings_weekly": rings_weekly,
        "decisions_weekly": decisions_weekly,
        "spike": {
            "detected": spike_detected,
            "message": spike_message
        }
    }
