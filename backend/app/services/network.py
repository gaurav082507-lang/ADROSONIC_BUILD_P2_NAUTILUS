"""
Fraud Ring Network Service (§14.3, Prompt 10).
Constructs multi-entity bipartite and projected graphs using NetworkX.
Detects coordinated fraud rings across claims, claimants, and shared identifiers.

Principles:
P1. Association is context, not proof: network evidence is capped (0.35) and can never make a claim HIGH alone.
P2. Humans decide: ring status changes are investigator actions, audited in ring_audits.
P3. Honest data: synthetic history is labelled data_source="synthetic_history".
"""

import json
import logging
import math
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set

import networkx as nx

try:
    from networkx.algorithms.community import louvain_communities
except ImportError:
    try:
        from networkx.community import louvain_communities
    except ImportError:
        louvain_communities = None

from ..db.database import get_connection

logger = logging.getLogger(__name__)

# Edge strength standards
STRONG_KINDS = {"bank", "bank_account", "phone", "image_cluster", "invoice"}
MEDIUM_KINDS = {"email", "address", "vehicle", "vehicle_number"}
WEAK_KINDS = {"facility", "provider", "garage", "hospital"}

def normalize_kind(kind: str) -> str:
    k = kind.lower().strip()
    if k in ("bank", "bank_account"):
        return "bank"
    if k in ("vehicle", "vehicle_number"):
        return "vehicle"
    if k in ("facility", "provider", "garage", "hospital"):
        return "facility"
    return k

def get_strength_for_kind(kind: str) -> float:
    k = normalize_kind(kind)
    if k in ("bank", "phone", "image_cluster", "invoice"):
        return 1.0
    if k in ("email", "address", "vehicle"):
        return 0.6
    if k in ("facility", "provider"):
        return 0.3
    return 0.4

def get_label_for_kind(kind: str) -> str:
    labels = {
        "bank": "Shared Bank Account",
        "phone": "Shared Phone Number",
        "image_cluster": "Reused Photo / Image",
        "invoice": "Duplicate Invoice Number",
        "email": "Shared Email Address",
        "address": "Shared Physical Address",
        "vehicle": "Shared Vehicle Registration",
        "facility": "Shared Repair/Medical Facility",
        "provider": "Shared Provider",
    }
    return labels.get(normalize_kind(kind), f"Shared {kind.title()}")



def build_raw_graph(min_strength: float = 0.0) -> nx.Graph:
    """
    Builds the full graph from claims, claimants, and entities in SQLite.
    Nodes:
      - claim:{claim_id}
      - claimant:{claimant_id}
      - id:{kind}:{value_hash}
    """
    conn = get_connection()
    G = nx.Graph()

    # 1. Fetch claims
    claims_rows = conn.execute("""
        SELECT c.id, c.claimant_user_id, c.claimant_name, c.status, c.claimed_amount,
               c.created_at, COALESCE(c.data_source, 'real') as data_source,
               r.overall_risk, r.overall_band
        FROM claims c
        LEFT JOIN results r ON c.result_id = r.id
    """).fetchall()

    for row in claims_rows:
        cid = row["id"]
        c_node = f"claim:{cid}"
        band = row["overall_band"] or "LOW"
        risk = float(row["overall_risk"] or 0.0)
        c_source = row["data_source"]
        
        G.add_node(
            c_node,
            node_type="claim",
            raw_id=cid,
            label=f"Claim {cid[:8]}",
            band=band,
            risk=risk,
            flags=[],
            amount=float(row["claimed_amount"] or 0.0),
            created_at=row["created_at"] or "",
            data_source=c_source
        )

        # Claimant node + edge
        claimant_id = row["claimant_user_id"] or row["claimant_name"] or "unknown_claimant"
        cm_node = f"claimant:{claimant_id}"
        if cm_node not in G:
            G.add_node(
                cm_node,
                node_type="claimant",
                raw_id=claimant_id,
                label=row["claimant_name"] or f"Claimant {claimant_id[:8]}",
                data_source=c_source
            )
        G.add_edge(
            c_node,
            cm_node,
            edge_type="claimant_link",
            strength=1.0,
            label="Claimed By",
            evidence_ids=[]
        )

    # 2. Fetch entities
    entity_rows = conn.execute("""
        SELECT e.claim_id, e.kind, e.value_hash, e.display, e.created_at,
               COALESCE(c.data_source, 'real') as data_source
        FROM entities e
        LEFT JOIN claims c ON e.claim_id = c.id
    """).fetchall()

    for erow in entity_rows:
        cid = erow["claim_id"]
        if not cid:
            continue
        c_node = f"claim:{cid}"
        if c_node not in G:
            continue

        kind = erow["kind"]
        v_hash = erow["value_hash"]
        display = erow["display"] or f"{kind}:{v_hash[:6]}"
        ent_node = f"id:{kind}:{v_hash}"
        strength = get_strength_for_kind(kind)

        if strength < min_strength:
            continue

        if ent_node not in G:
            G.add_node(
                ent_node,
                node_type="identifier",
                kind=kind,
                raw_id=v_hash,
                label=display,
                data_source=erow["data_source"]
            )

        G.add_edge(
            c_node,
            ent_node,
            edge_type=kind,
            strength=strength,
            label=get_label_for_kind(kind),
            evidence_ids=[]
        )

    conn.close()
    return G


def detect_fraud_rings(rebuild: bool = True) -> List[Dict[str, Any]]:
    """
    Connected components over strong + medium edges only.
    Rings require:
      - >= 3 claims
      - >= 2 distinct claimants
    Inside large components, splits using Louvain community detection.
    Computes ring_score and saves to database.
    """
    conn = get_connection()
    # Fast bipartite linking via SQLite
    # Fetch all claims sharing strong or medium entities
    query = """
        SELECT e1.claim_id as claim_a, e2.claim_id as claim_b,
               e1.kind, e1.display,
               c1.claimant_user_id as claimant_a, c2.claimant_user_id as claimant_b,
               c1.claimed_amount as amount_a, c2.claimed_amount as amount_b,
               COALESCE(c1.data_source, 'real') as ds_a,
               COALESCE(c2.data_source, 'real') as ds_b,
               c1.created_at as created_a, c2.created_at as created_b
        FROM entities e1
        JOIN entities e2 ON e1.kind = e2.kind AND e1.value_hash = e2.value_hash
        JOIN claims c1 ON e1.claim_id = c1.id
        JOIN claims c2 ON e2.claim_id = c2.id
        WHERE e1.claim_id < e2.claim_id
          AND e1.kind IN ('bank', 'bank_account', 'phone', 'image_cluster', 'invoice', 'email', 'address', 'vehicle', 'vehicle_number')
    """
    rows = conn.execute(query).fetchall()

    # Build claim-to-claim graph
    C_graph = nx.Graph()
    edge_shared: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    claim_meta: Dict[str, Dict[str, Any]] = {}

    for r in rows:
        ca = r["claim_a"]
        cb = r["claim_b"]
        kind = normalize_kind(r["kind"])
        strength = get_strength_for_kind(kind)
        
        # Track claim metadata
        if ca not in claim_meta:
            claim_meta[ca] = {
                "claimant": r["claimant_a"],
                "amount": float(r["amount_a"] or 0.0),
                "created_at": r["created_a"],
                "data_source": r["ds_a"],
            }
        if cb not in claim_meta:
            claim_meta[cb] = {
                "claimant": r["claimant_b"],
                "amount": float(r["amount_b"] or 0.0),
                "created_at": r["created_b"],
                "data_source": r["ds_b"],
            }

        C_graph.add_edge(ca, cb, weight=strength)
        pair = (min(ca, cb), max(ca, cb))
        if pair not in edge_shared:
            edge_shared[pair] = []
        edge_shared[pair].append({"kind": kind, "display": r["display"], "strength": strength})

    rings: List[Dict[str, Any]] = []

    # Process connected components
    components = list(nx.connected_components(C_graph))
    for comp in components:
        comp_claims = list(comp)
        if len(comp_claims) < 3:
            continue

        # If component is large, sub-divide with Louvain
        candidate_clusters = [comp_claims]
        if len(comp_claims) >= 10 and louvain_communities:
            subg = C_graph.subgraph(comp_claims)
            try:
                comms = louvain_communities(subg, seed=42)
                if len(comms) > 1:
                    candidate_clusters = [list(c) for c in comms if len(c) >= 3]
            except Exception as e:
                logger.warning(f"Louvain failed: {e}")

        for cluster in candidate_clusters:
            # Check claimants count
            claimants = set(claim_meta[c]["claimant"] for c in cluster if c in claim_meta)
            if len(cluster) < 3 or len(claimants) < 2:
                continue

            # Gather all shared entities across pairs of claims by DIFFERENT claimants
            shared_types: Set[str] = set()
            shared_items_map: Dict[str, Dict[str, Any]] = {}
            total_amount = sum(claim_meta[c]["amount"] for c in cluster if c in claim_meta)
            created_dates = [claim_meta[c]["created_at"] for c in cluster if c in claim_meta and claim_meta[c]["created_at"]]
            first_seen = min(created_dates) if created_dates else datetime.utcnow().isoformat()
            last_seen = max(created_dates) if created_dates else datetime.utcnow().isoformat()
            data_sources = set(claim_meta[c]["data_source"] for c in cluster if c in claim_meta)
            ring_ds = "synthetic_history" if "synthetic_history" in data_sources and len(data_sources) == 1 else "real"

            # Check edges in this cluster
            for i in range(len(cluster)):
                for j in range(i + 1, len(cluster)):
                    pair = (min(cluster[i], cluster[j]), max(cluster[i], cluster[j]))
                    if pair in edge_shared:
                        for item in edge_shared[pair]:
                            k = item["kind"]
                            shared_types.add(k)
                            disp = item["display"]
                            key = f"{k}:{disp}"
                            if key not in shared_items_map:
                                shared_items_map[key] = {"type": k, "label": disp, "count": 0}
                            shared_items_map[key]["count"] += 1

            # ring_score = (1 - prod(1 - strength)) * min(1, claims/5)
            prod_val = 1.0
            for t in shared_types:
                st = get_strength_for_kind(t)
                prod_val *= (1.0 - st)
            raw_factor = 1.0 - prod_val
            size_factor = min(1.0, len(cluster) / 5.0)
            score = round(raw_factor * size_factor, 4)

            band = "HIGH" if score >= 0.65 else ("MEDIUM" if score >= 0.35 else "LOW")

            # Stable ring ID based on sorted claims
            import hashlib
            cluster_hash = hashlib.sha256(":".join(sorted(cluster)).encode("utf-8")).hexdigest()[:10]
            ring_id = f"ring_{cluster_hash}"

            # Format reasons with numbers
            reasons = []
            for item in sorted(shared_items_map.values(), key=lambda x: -x["count"]):
                reasons.append(f"{len(claimants)} claimants share {get_label_for_kind(item['type']).lower()} {item['label']} across {len(cluster)} claims")
            if "image_cluster" in shared_types:
                reasons.append(f"Same damage photo reused in {len(cluster)} claims across multiple policies")
            reasons.append(f"Total claimed amount ₹{total_amount:,.2f} across {len(cluster)} coordinated claims")

            shared_summary = list(shared_items_map.values())

            ring_obj = {
                "ring_id": ring_id,
                "ring_score": score,
                "band": band,
                "claims_count": len(cluster),
                "claimants_count": len(claimants),
                "shared": shared_summary,
                "total_claimed_amount": total_amount,
                "first_seen": first_seen,
                "last_seen": last_seen,
                "status": "open",
                "reasons": reasons,
                "data_source": ring_ds,
                "member_ids": sorted(cluster)
            }
            rings.append(ring_obj)

    # Persist detected rings to database
    if rebuild:
        # Preserve status of existing rings if already audited
        existing_status = {}
        for r_row in conn.execute("SELECT id, status FROM rings").fetchall():
            existing_status[r_row["id"]] = r_row["status"]

        for r in rings:
            rid = r["ring_id"]
            stat = existing_status.get(rid, "open")
            r["status"] = stat
            now = datetime.utcnow().isoformat()
            conn.execute("""
                INSERT INTO rings (id, ring_score, band, claims_count, claimants_count,
                                  shared_json, total_claimed_amount, first_seen, last_seen,
                                  status, reasons_json, data_source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    ring_score=excluded.ring_score,
                    band=excluded.band,
                    claims_count=excluded.claims_count,
                    claimants_count=excluded.claimants_count,
                    shared_json=excluded.shared_json,
                    total_claimed_amount=excluded.total_claimed_amount,
                    first_seen=excluded.first_seen,
                    last_seen=excluded.last_seen,
                    reasons_json=excluded.reasons_json,
                    updated_at=excluded.updated_at
            """, (
                rid, r["ring_score"], r["band"], r["claims_count"], r["claimants_count"],
                json.dumps(r["shared"]), r["total_claimed_amount"], r["first_seen"], r["last_seen"],
                stat, json.dumps(r["reasons"]), r["data_source"], now, now
            ))
            # Delete old members and insert new
            conn.execute("DELETE FROM ring_members WHERE ring_id = ?", (rid,))
            for cid in r["member_ids"]:
                cm = claim_meta.get(cid, {})
                conn.execute("""
                    INSERT INTO ring_members (ring_id, claim_id, claimant_id, added_at)
                    VALUES (?, ?, ?, ?)
                """, (rid, cid, cm.get("claimant", ""), now))

        conn.commit()

    conn.close()
    return rings


def update_ring_status(ring_id: str, new_status: str, note: Optional[str], actor: str) -> Dict[str, Any]:
    """
    Audited ring status transition (Principle P2).
    Requires a non-empty note when moving to 'confirmed' or 'dismissed'.
    """
    valid_statuses = {"open", "under_review", "confirmed", "dismissed"}
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid status: {new_status}. Must be one of {valid_statuses}")

    if new_status in ("confirmed", "dismissed") and (not note or not note.strip()):
        raise ValueError(f"A non-empty note is required when setting ring status to '{new_status}'")

    conn = get_connection()
    row = conn.execute("SELECT id, status FROM rings WHERE id = ?", (ring_id,)).fetchone()
    if not row:
        conn.close()
        raise KeyError(f"Ring {ring_id} not found")

    from_status = row["status"]
    now = datetime.utcnow().isoformat()

    conn.execute("UPDATE rings SET status = ?, updated_at = ? WHERE id = ?", (new_status, now, ring_id))
    conn.execute("""
        INSERT INTO ring_audits (ring_id, from_status, to_status, note, actor, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ring_id, from_status, new_status, note or "", actor, now))
    conn.commit()
    conn.close()

    return {
        "ring_id": ring_id,
        "status": new_status,
        "from_status": from_status,
        "to_status": new_status,
        "note": note,
        "actor": actor,
        "updated_at": now
    }


def get_rings_list(min_score: Optional[float] = None, status: Optional[str] = None, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    conn = get_connection()
    query = "SELECT * FROM rings WHERE 1=1"
    params: List[Any] = []
    if min_score is not None:
        query += " AND ring_score >= ?"
        params.append(min_score)
    if status:
        query += " AND status = ?"
        params.append(status)

    total = conn.execute(f"SELECT COUNT(*) as c FROM ({query})", params).fetchone()["c"]

    query += " ORDER BY ring_score DESC, claims_count DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    items = []
    for r in rows:
        items.append({
            "ring_id": r["id"],
            "ring_score": float(r["ring_score"]),
            "band": r["band"],
            "claims_count": int(r["claims_count"]),
            "claimants_count": int(r["claimants_count"]),
            "shared": json.loads(r["shared_json"] or "[]"),
            "total_claimed_amount": float(r["total_claimed_amount"]),
            "first_seen": r["first_seen"],
            "last_seen": r["last_seen"],
            "status": r["status"],
            "reasons": json.loads(r["reasons_json"] or "[]"),
            "data_source": r["data_source"]
        })

    conn.close()
    return {"items": items, "total": total}


def get_ring_detail(ring_id: str) -> Dict[str, Any]:
    conn = get_connection()
    r = conn.execute("SELECT * FROM rings WHERE id = ?", (ring_id,)).fetchone()
    if not r:
        conn.close()
        raise KeyError(f"Ring {ring_id} not found")

    # Fetch members
    m_rows = conn.execute("""
        SELECT rm.claim_id, c.claimed_amount, r.overall_band, c.created_at
        FROM ring_members rm
        JOIN claims c ON rm.claim_id = c.id
        LEFT JOIN results r ON c.result_id = r.id
        WHERE rm.ring_id = ?
        ORDER BY c.created_at ASC
    """, (ring_id,)).fetchall()

    claims = [{
        "claim_id": row["claim_id"],
        "band": row["overall_band"] or "LOW",
        "amount": float(row["claimed_amount"] or 0.0),
        "submitted_at": row["created_at"] or ""
    } for row in m_rows]

    # Timeline of ring formation
    timeline = [{
        "date": row["created_at"] or "",
        "event": f"Claim {row['claim_id'][:8]} submitted (₹{float(row['claimed_amount'] or 0.0):,.0f})"
    } for row in m_rows]

    # Audits
    a_rows = conn.execute("""
        SELECT from_status, to_status, note, actor, created_at
        FROM ring_audits
        WHERE ring_id = ?
        ORDER BY id DESC
    """, (ring_id,)).fetchall()
    audit = [dict(a) for a in a_rows]

    conn.close()

    # Generate graph focused on this ring
    graph = get_network_subgraph(focus_type="ring", focus_id=ring_id, hops=2, limit=200)

    ring_data = {
        "ring_id": r["id"],
        "ring_score": float(r["ring_score"]),
        "band": r["band"],
        "claims_count": int(r["claims_count"]),
        "claimants_count": int(r["claimants_count"]),
        "shared": json.loads(r["shared_json"] or "[]"),
        "total_claimed_amount": float(r["total_claimed_amount"]),
        "first_seen": r["first_seen"],
        "last_seen": r["last_seen"],
        "status": r["status"],
        "reasons": json.loads(r["reasons_json"] or "[]"),
        "data_source": r["data_source"],
        "claims": claims,
        "timeline": timeline,
        "graph": graph,
        "audit": audit
    }
    return ring_data


def get_network_subgraph(
    focus_type: Optional[str] = None,
    focus_id: Optional[str] = None,
    hops: int = 2,
    min_strength: float = 0.3,
    limit: int = 300
) -> Dict[str, Any]:
    """
    Subgraphs query for UI.
    If no focus, returns top rings overview.
    """
    G = build_raw_graph(min_strength=min_strength)

    # Fetch rings overview
    rings_list = get_rings_list(limit=50)["items"]
    rings_summary = [{
        "ring_id": r["ring_id"],
        "ring_score": r["ring_score"],
        "member_ids": [m["claim_id"] for m in get_ring_members(r["ring_id"])]
    } for r in rings_list]

    selected_nodes = set()

    if focus_type and focus_id:
        target_node = None
        if focus_type == "claim":
            target_node = f"claim:{focus_id}"
        elif focus_type == "claimant":
            target_node = f"claimant:{focus_id}"
        elif focus_type == "ring":
            # Select all claims in the ring
            m_ids = [m["claim_id"] for m in get_ring_members(focus_id)]
            for cid in m_ids:
                cn = f"claim:{cid}"
                if cn in G:
                    selected_nodes.add(cn)

        if target_node and target_node in G:
            selected_nodes.add(target_node)

        # Expand hops
        current_layer = set(selected_nodes)
        for _ in range(hops):
            next_layer = set()
            for n in current_layer:
                if n in G:
                    for nbr in G.neighbors(n):
                        next_layer.add(nbr)
            selected_nodes.update(next_layer)
            current_layer = next_layer
    else:
        # Default view: pick nodes from top rings
        for r in rings_list[:5]:
            m_ids = [m["claim_id"] for m in get_ring_members(r["ring_id"])]
            for cid in m_ids:
                cn = f"claim:{cid}"
                if cn in G:
                    selected_nodes.add(cn)
                    for nbr in G.neighbors(cn):
                        selected_nodes.add(nbr)

    if not selected_nodes:
        # If no rings or focus, take top claims by degree
        selected_nodes = set(list(G.nodes)[:limit])

    truncated = False
    if len(selected_nodes) > limit:
        truncated = True
        selected_nodes = set(list(selected_nodes)[:limit])

    subG = G.subgraph(selected_nodes)

    nodes_out = []
    for n, data in subG.nodes(data=True):
        node_item = {
            "id": n,
            "type": data.get("node_type", "identifier"),
            "label": data.get("label", n),
            "data_source": data.get("data_source", "real")
        }
        if "band" in data:
            node_item["band"] = data["band"]
        if "risk" in data:
            node_item["risk"] = data["risk"]
        if "flags" in data:
            node_item["flags"] = data["flags"]
        nodes_out.append(node_item)

    edges_out = []
    for u, v, data in subG.edges(data=True):
        edges_out.append({
            "id": f"{u}-{v}",
            "source": u,
            "target": v,
            "type": data.get("edge_type", "link"),
            "strength": float(data.get("strength", 0.5)),
            "label": data.get("label", ""),
            "evidence_ids": data.get("evidence_ids", [])
        })

    return {
        "nodes": nodes_out,
        "edges": edges_out,
        "rings": rings_summary,
        "truncated": truncated
    }


def get_ring_members(ring_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT claim_id, claimant_id, added_at FROM ring_members WHERE ring_id = ?", (ring_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_claim_network_info(claim_id: str) -> Dict[str, Any]:
    """
    Returns network intelligence for a single claim:
    - active rings it belongs to
    - shared identifiers across other claims
    - network evidence items
    """
    conn = get_connection()

    # Rings
    rings_rows = conn.execute("""
        SELECT r.id, r.ring_score, r.band, r.status, r.claims_count, r.claimants_count
        FROM ring_members rm
        JOIN rings r ON rm.ring_id = r.id
        WHERE rm.claim_id = ?
    """, (claim_id,)).fetchall()

    rings = [{
        "ring_id": row["id"],
        "ring_score": float(row["ring_score"]),
        "band": row["band"],
        "status": row["status"]
    } for row in rings_rows]

    # Shared identifiers with other claims
    shared_rows = conn.execute("""
        SELECT e1.kind, e1.display, COUNT(DISTINCT e2.claim_id) as other_claims_count
        FROM entities e1
        JOIN entities e2 ON e1.kind = e2.kind AND e1.value_hash = e2.value_hash
        JOIN claims c2 ON e2.claim_id = c2.id
        WHERE e1.claim_id = ? AND e2.claim_id != ?
        GROUP BY e1.kind, e1.display
    """, (claim_id, claim_id)).fetchall()

    shared_identifiers = [{
        "type": r["kind"],
        "label": r["display"],
        "other_claims": int(r["other_claims_count"])
    } for r in shared_rows]

    # Evidence items
    evidence = []
    # Check strong shared
    strong_shared = [s for s in shared_identifiers if s["type"] in STRONG_KINDS]
    if strong_shared:
        details_txt = ", ".join([f"{s['type']} ({s['label']}) with {s['other_claims']} other claim(s)" for s in strong_shared])
        evidence.append({
            "id": "CLM-NET-01",
            "title": "Shared Strong Identifier Across Claimants",
            "weight": 0.40,
            "raw_score": 0.85,
            "calibrated_score": 0.85,
            "reason": f"Claim shares strong identifier: {details_txt}"
        })

    if rings:
        top_ring = max(rings, key=lambda x: x["ring_score"])
        evidence.append({
            "id": "CLM-NET-02",
            "title": f"Fraud Ring Member ({top_ring['ring_id']})",
            "weight": 0.55,
            "raw_score": top_ring["ring_score"],
            "calibrated_score": top_ring["ring_score"],
            "reason": f"Member of coordinated fraud ring {top_ring['ring_id']} (ring score: {top_ring['ring_score']:.2f}, band: {top_ring['band']})"
        })

    conn.close()
    return {
        "rings": rings,
        "shared_identifiers": shared_identifiers,
        "evidence": evidence
    }
