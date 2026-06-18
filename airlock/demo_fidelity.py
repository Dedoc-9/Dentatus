"""
airlock/demo_fidelity.py — multi-fidelity integrity on ONE world. PYTHONHASHSEED=0.

Severity is a POLICY (world, txn) -> tier, so different regions of the same world are audited at different
depth: near-camera/player-zone strict, far-field cheap. Fidelity (where you look) is independent of integrity
(how hard you check). Not everything deserves Einstein-level scrutiny every frame.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import membrane as M
import adapters as A

S = 1 << 32


def main():
    R = 20 * S
    W = A.K.make_world([A.K.body(0, (0, 0, 0), (0, 0, 0), (1, 1, 1)),       # near origin  → strict
                        A.K.body(1, (500, 0, 0), (0, 0, 0), (1, 1, 1))],    # far field    → game
                       ((-10000, -10000, -10000), (10000, 10000, 10000)))

    def policy(world, txn):
        b = next((x for x in world["bodies"] if x["id"] == txn.get("id")), None)
        if b is None:
            return "game"
        return "strict" if sum(c * c for c in b["pos"]) <= R * R else "game"

    cons = {"max_bodies": 8, "c_limit": 5 * S}
    boom = lambda bid: {"transition": {"op": "impulse", "id": bid, "dv": [99, 0, 0]},
                        "budget": {"max_cost": 5, "max_delta": 10**22}, "constraints": cons}

    print("One world, two zones, one membrane, a region severity policy (near=strict, far=game):\n")
    for bid, where in [(0, "near origin"), (1, "far field")]:
        r = M.propose(W, boom(bid), A, severity=policy)
        print("  superluminal impulse on body %d (%-11s) -> severity=%-6s %s"
              % (bid, where, r["telemetry"]["severity"], r["gate"]))
    print("\n  => the SAME deterministic world is audited at different depth by region.")
    print("     fidelity (where you look) is independent of integrity (how hard you check).")
    print("     Multi-fidelity = a richer severity policy; no new kernel, no new product surface.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[airlock] set PYTHONHASHSEED=0.\n\n")
        raise SystemExit(2)
    main()
