"""
airlock/demo_admissibility.py — the geometry of what almost happened. PYTHONHASHSEED=0.

A session of mixed proposals through the membrane; then the admissibility geometry — proposal pressure and
the shape of the filter (which gates reality used to reject candidate transitions). Pure telemetry.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import membrane as M
import adapters as A
import admissibility as AD


def main():
    W = A.K.make_world([A.K.body(0, (0, 5, 0), (0, 0, 0), (1, 1, 1))], ((-10, -10, -10), (10, 10, 10)))
    L = M.Ledger()
    props = [{"op": "impulse", "id": 0, "dv": [1, 0, 0]},
             {"op": "impulse", "id": 0, "dv": [0.5, 0, 0]},        # CANON (float)
             {"op": "teleport"},                                   # SCHEMA
             {"op": "advance", "ticks": 100},                      # BUDGET
             {"op": "advance", "ticks": 2},                        # COMMIT
             {"op": "spawn", "body": {"id": 9, "pos": [3, 5, 0], "vel": [0, 0, 0], "half": [1, 1, 1]}},  # CONSTRAINT
             {"op": "impulse", "id": 99, "dv": [1, 0, 0]}]         # APPLY
    for t in props:
        M.propose(W, {"transition": t, "budget": {"max_cost": 10, "max_delta": 10**18},
                      "constraints": {"max_bodies": 1}}, A, ledger=L)
    g = AD.geometry(L)
    print("Session: %d proposals -> %d realized, %d unrealized\n" % (g["proposed"], g["realized"], g["unrealized"]))
    print("  admissibility    = %d permille  (how much proposed history became real)" % g["admissibility_permille"])
    print("  proposal pressure = %d permille  (how strongly the filter shaped history)" % g["proposal_pressure_permille"])
    print("  shape of the filter (where reality rejected candidates):")
    for gate, n in sorted(g["gate_histogram"].items()):
        print("     %-11s %d" % (gate, n))
    print("  dominant filter gate:", g["dominant_gate"])
    print("\nMost systems record only what happened. This one measures what ALMOST happened — the geometry of")
    print("admissibility a session moved through. Pure telemetry; a modeling lens, not a claim about nature.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[airlock] set PYTHONHASHSEED=0.\n\n")
        raise SystemExit(2)
    main()
