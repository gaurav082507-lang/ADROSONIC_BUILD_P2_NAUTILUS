from typing import List, Dict, Any, Tuple, Set, Optional

# Per-source caps: maximum contribution any one source can make to the fused score.
# "forensics" cap (0.30) applies to DOC-CNN-01 alone; lifted to 1.0 when
# the CNN box overlaps a rule-based flag (DOC-LOGIC-*, DOC-FONT-*, DOC-OVERLAY-01)
# — see compute_fusion_with_contributions's corroborated_sources argument.
CAPS = {
    "metadata": 0.4,
    "aadhaar_qr": 0.85,
    "liveness": 0.75,
    "voice": 0.55,
    "llm_story": 0.25,
    "forensics": 0.30,   # DOC-CNN-01 source cap; lifted by corroboration
    "network": 0.35,     # Principle P1: network evidence can never make a claim HIGH alone
}

def compute_fusion(evidence_list: List[Dict[str, Any]]) -> float:
    """
    Computes noisy-OR fusion over kind='risk' evidence with participation
    thresholds and per-source caps (§15.4).
    """
    risk, _ = compute_fusion_with_contributions(evidence_list)
    return risk

def compute_fusion_with_contributions(
    evidence_list: List[Dict[str, Any]],
    corroborated_sources: Optional[Set[str]] = None,
) -> Tuple[float, Dict[str, float]]:
    """
    Computes noisy-OR risk and per-evidence normalized contributions (§15.4).
    Contribution_i = w_i * p_i * prod_{j!=i} (1 - w_j * p_j)
    Normalized so sum(contributions) == fused_risk.

    corroborated_sources: source strings whose cap should be lifted to 1.0 because
      a higher-confidence detector's bbox overlaps theirs (CNN corroboration, P0-5).
    """
    if corroborated_sources is None:
        corroborated_sources = set()

    # 1. Filter participating risk items
    participating = []
    sources = {}

    for ev in evidence_list:
        ev_d = ev.model_dump() if hasattr(ev, "model_dump") else (ev if isinstance(ev, dict) else dict(ev))
        if ev_d.get("kind") != "risk":
            continue

        w = float(ev_d.get("effective_weight", 0.0))
        p = float(ev_d.get("calibrated_score", 0.0))
        source = ev_d.get("source", "unknown")
        ev_id = ev_d.get("id", "unknown")

        # Guard against many weak signals: p >= 0.2 AND w*p >= 0.02
        if p >= 0.2 and (w * p) >= 0.02:
            term = w * p
            participating.append({"id": ev_id, "source": source, "term": term})
            if source not in sources:
                sources[source] = []
            sources[source].append(term)

    if not participating:
        return 0.0, {}

    # 2. Noisy-OR with per-source caps
    # Source risk = 1 - prod(1 - t_i), capped at CAPS[source]
    # Cap is lifted (set to 1.0) for corroborated sources.
    risk_total = 1.0
    source_risks = {}

    for source, terms in sources.items():
        s_risk = 1.0
        for t in terms:
            s_risk *= (1.0 - t)
        s_risk = 1.0 - s_risk

        if source in corroborated_sources:
            cap = 1.0  # lifted: CNN box overlaps rule-based flag
        else:
            cap = CAPS.get(source, 1.0)
        s_risk = min(s_risk, cap)
        source_risks[source] = s_risk
        risk_total *= (1.0 - s_risk)

    final_risk = round(1.0 - risk_total, 4)

    # 3. Marginal contributions calculation
    # Raw marginal contribution: t_i * prod_{j!=i} (1 - t_j)
    contributions = {}
    raw_contrib_sum = 0.0

    # Scale term by source cap ratio if source was capped
    for item in participating:
        source = item["source"]
        uncapped_source_risk = 1.0
        for t in sources[source]:
            uncapped_source_risk *= (1.0 - t)
        uncapped_source_risk = 1.0 - uncapped_source_risk

        if source in corroborated_sources:
            cap = 1.0
        else:
            cap = CAPS.get(source, 1.0)
        scale = (cap / uncapped_source_risk) if uncapped_source_risk > cap > 0 else 1.0
        effective_term = min(0.999, item["term"] * scale)
        item["effective_term"] = effective_term

    for i, item in enumerate(participating):
        t_i = item["effective_term"]
        prod_others = 1.0
        for j, other in enumerate(participating):
            if i != j:
                prod_others *= (1.0 - other["effective_term"])
        raw_contrib = t_i * prod_others
        contributions[item["id"]] = raw_contrib
        raw_contrib_sum += raw_contrib

    # Normalize contributions to sum to final_risk
    normalized_contributions = {}
    if raw_contrib_sum > 0:
        for ev_id, c in contributions.items():
            normalized_contributions[ev_id] = round((c / raw_contrib_sum) * final_risk, 4)
    else:
        for ev_id in contributions:
            normalized_contributions[ev_id] = 0.0

    return final_risk, normalized_contributions
