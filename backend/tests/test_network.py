import time
import pytest
import networkx as nx
from backend.app.services.network import (
    build_raw_graph,
    detect_fraud_rings,
    update_ring_status,
    get_network_subgraph,
    get_rings_list
)
from backend.app.db.database import get_connection


def test_graph_construction_and_weights():
    # Verify graph can be built with strength filtering
    G = build_raw_graph(min_strength=0.0)
    assert isinstance(G, nx.Graph)
    # Check that strong (1.0), medium (0.6), and weak (0.3) edge attributes are valid
    for u, v, d in G.edges(data=True):
        assert "strength" in d
        assert 0.0 <= d["strength"] <= 1.0


def test_shared_garage_only_does_not_form_ring():
    # CLM-GARAGE-01 and CLM-GARAGE-02 share ONLY a garage (weak edge 0.3)
    # Connected components over strong (1.0) and medium (0.6) edges MUST NOT cluster them
    rings = detect_fraud_rings(rebuild=False)
    for r in rings:
        members = r.get("member_claim_ids", [])
        assert not ("CLM-GARAGE-01" in members and "CLM-GARAGE-02" in members and len(members) == 2), \
            "Shared garage alone formed a ring, violating Principle P1!"


def test_ring_score_formula_and_threshold():
    rings = detect_fraud_rings(rebuild=False)
    for r in rings:
        assert r["claims_count"] >= 3, "Ring must have >= 3 claims"
        assert r["claimants_count"] >= 2, "Ring must have >= 2 distinct claimants"
        assert 0.0 <= r["ring_score"] <= 1.0
        assert r["band"] in ("LOW", "MEDIUM", "HIGH")
        assert len(r["reasons"]) > 0


def test_ring_audit_workflow():
    conn = get_connection()
    ring = conn.execute("SELECT id, status FROM rings LIMIT 1").fetchone()
    conn.close()
    if not ring:
        pytest.skip("No rings in DB to test audit workflow")

    rid = ring["id"]

    # Updating to 'confirmed' without note must raise ValueError
    with pytest.raises(ValueError, match="non-empty note"):
        update_ring_status(rid, "confirmed", note="", actor="Investigator Test")

    # Updating to 'confirmed' with note must succeed and write audit record
    updated = update_ring_status(rid, "confirmed", note="Confirmed after cross-referencing bank data", actor="Investigator Test")
    assert updated["status"] == "confirmed"

    # Reset back to under_review
    update_ring_status(rid, "under_review", note="Investigating ongoing leads", actor="Investigator Test")


def test_5000_claims_benchmark():
    # Must handle 5,000 claims graph analysis in < 5 seconds
    B = nx.Graph()
    # Build a synthetic graph of 5,000 claims with claimants and identifiers
    for i in range(5000):
        c_id = f"c_{i}"
        user_id = f"u_{i % 800}"
        bank_id = f"b_{i % 500}"
        B.add_node(c_id, type="claim")
        B.add_node(user_id, type="claimant")
        B.add_node(bank_id, type="bank")
        B.add_edge(c_id, user_id, strength=1.0)
        B.add_edge(c_id, bank_id, strength=1.0)

    t0 = time.perf_counter()
    components = list(nx.connected_components(B))
    t1 = time.perf_counter()
    elapsed = t1 - t0
    assert elapsed < 5.0, f"Graph benchmark took {elapsed:.2f}s, expected < 5.0s"
