"""
NGGV/demo_manifold.py — topology-gated commits on the frozen Chronicle ledger.

Run:  PYTHONHASHSEED=0 python3 demo_manifold.py

  A. RECORD     — benign topology edits (add a redundant edge) commit to the ledger; world_H = topology.
  B. GATE       — an edit that would BISECT the critical subsystem is refused fail-closed by the EXACT
                  connectivity gate; the captured lambda2 -> 0 corroborates it in the record.
  C. REPLAY     — the Replay Court re-verifies the committed chain bit-for-bit, with NO numpy on the
                  replay path (lambda2 is captured, the gate is exact integer arithmetic).
  D. TAMPER     — editing a committed topology is caught (world_H no longer matches).

Honest scope: lambda2 is a captured *observable/margin*, never a gate and never inside world_H (float
eigensolvers are not bit-reproducible). The diamond-hard gate is exact graph topology. Integrity != truth:
this proves the recorded topology is connected and untampered, not that the system is "safe."
"""
import os, sys, copy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import manifold_core as M
# the frozen workbench (manifold_core already put Reality_Engine/chronicle on the path)
import core as C
from core import Recorder, ruleset_hash, InvariantViolation
from court import verify_chain, print_verdict
from signing import HmacSigner   # drop-in: Ed25519Signer or chronicle.hardware_signing.HardwareSigner

SECRET = b"nggv_manifold_authority_demo"

# the critical compute subsystem: a connected graph of 6 components/nodes
N = 6
BASE_EDGES = [(0, 1), (1, 2), (2, 0), (2, 3), (3, 4), (4, 5), (5, 3)]   # two triangles joined by bridge (2,3)


def manifold_transition(inputs):
    """Deterministic: world_H + exact connectivity from the integer graph; lambda2 is READ from capture."""
    n = inputs["n"]; edges = [tuple(e) for e in inputs["edges"]]
    return {
        "world_H": M.world_hash(n, edges),
        "connected": M.is_connected(n, edges),
        "components": 1 if M.is_connected(n, edges) else 2,
        "bridges": [list(b) for b in M.bridges(n, edges)],
        "lambda2": inputs["_cap"]["lambda2"],          # captured observable, replayed (never recomputed)
    }


def topology_gate(inputs, outputs):
    """DIAMOND-HARD, EXACT: refuse any state that fragments the manifold (loses connectivity)."""
    return outputs["connected"] is True


def seal(n, edges):
    """Live-time: capture the spectral margin into the inputs so replay is deterministic."""
    return {"n": n, "edges": [list(e) for e in M.normalize_graph(n, edges)[1]],
            "_cap": {"lambda2": M.fiedler_value(n, edges)}}


if __name__ == "__main__":
    C.__dict__.get("require_deterministic_hashing", lambda *a: None)  # chronicle core has no guard; demos do
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("[nggv] run with PYTHONHASHSEED=0\n"); raise SystemExit(2)

    ruleset = ruleset_hash(manifold_transition, topology_gate)
    rec = Recorder(HmacSigner(SECRET), ruleset)
    ledger = []

    print("A) RECORD benign topology edits (commit if the manifold stays connected):")
    edits = [
        ("T-001", BASE_EDGES),                                   # base, connected
        ("T-002", BASE_EDGES + [(0, 3)]),                        # add a redundant cross-edge (still connected)
    ]
    for tid, edges in edits:
        sealed = seal(N, edges)
        out = manifold_transition(sealed)
        ledger.append(rec.record(tid, sealed, out, topology_gate))
        print("   %s  connected=%s  lambda2=%.4f  world_H=%s" %
              (tid, out["connected"], out["lambda2"], ledger[-1]["frame"]["outputs"]["world_H"][:12]))

    print("\nB) GATE: propose removing the bridge (2,3) -> would bisect into two triangles:")
    bisecting = [e for e in BASE_EDGES if tuple(sorted(e)) != (2, 3)]
    sealed = seal(N, bisecting)
    out = manifold_transition(sealed)
    print("   exact gate sees connected=%s; captured lambda2=%.4f (collapsed)" % (out["connected"], out["lambda2"]))
    try:
        rec.record("T-BISECT", sealed, out, topology_gate)
        print("   committed (should NOT happen)")
    except InvariantViolation as e:
        print("   refused fail-closed: %s" % e)
    print("   ledger length unchanged: %d" % len(ledger))

    print("\nC) REPLAY COURT verifies the committed chain (no numpy on the replay path):")
    print_verdict(verify_chain(ledger, SECRET, manifold_transition, topology_gate), len(ledger))

    print("\nD) TAMPER: edit a committed topology (add an edge to T-001's recorded inputs):")
    bad = copy.deepcopy(ledger)
    bad[0]["frame"]["inputs"]["edges"].append([0, 5])
    print_verdict(verify_chain(bad, SECRET, manifold_transition, topology_gate), len(bad))

    print("\n   NOTE: lambda2 is a captured margin, not the gate; world_H is the integer topology.")
    print("   Integrity != truth — connected+untampered, not 'safe'.")
