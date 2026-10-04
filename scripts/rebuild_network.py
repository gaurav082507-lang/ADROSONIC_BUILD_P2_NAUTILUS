"""
Network Graph Rebuild Utility (§14.3, Prompt 10).
Rebuilds the fraud network and detects rings across all claims.
"""
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.network import detect_fraud_rings

def rebuild():
    t0 = time.time()
    print("Rebuilding fraud network and detecting rings...")
    rings = detect_fraud_rings(rebuild=True)
    dt = time.time() - t0
    print(f"Rebuild completed in {dt:.2f}s: detected {len(rings)} ring(s).")
    for r in rings:
        print(f" - Ring {r['ring_id']}: score={r['ring_score']} band={r['band']} claims={r['claims_count']} claimants={r['claimants_count']}")

if __name__ == "__main__":
    rebuild()
