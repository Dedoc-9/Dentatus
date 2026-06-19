"""
salience/demo_salience.py — the full pipeline: physics → possibility geometry → compute allocation.
PYTHONHASHSEED=0.

Two regions of a world, each a state with its own field of lawful alternatives. `horizon` measures the
possibility pressure around each; `salience` allocates a compute budget by that pressure. The doorway (low
geometry, high possibility) outranks the valley (high geometry, low possibility) — a scheduling signal LOD
and distance cannot see. Allocation steers compute, never the kernel: the committed world is unchanged.
"""
import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))           # salience/
sys.path.insert(0, os.path.join(ROOT, "airlock"))                        # airlock/
import field as SAL
import adapters as A
import horizon as HZ

B = {"budget": {"max_cost": 9, "max_delta": 10**18}, "constraints": {"max_bodies": 3}}


def pressure(world, candidates):
    return HZ.neighborhood(world, 0, candidates, A)["possibility_pressure"]


def main():
    W = A.K.make_world([A.K.body(0, (0, 5, 0), (0, 0, 0), (1, 1, 1))], ((-100, -100, -100), (100, 100, 100)))
    # "valley": geometrically rich in a real game, but few/near lawful futures here
    valley = [{"transition": {"op": "impulse", "id": 0, "dv": [1, 0, 0]}, **B},
              {"transition": {"op": "impulse", "id": 0, "dv": [2, 0, 0]}, **B}]
    # "doorway": few primitives, but crossing it opens many far-reaching lawful futures
    doorway = [{"transition": {"op": "impulse", "id": 0, "dv": [1, 0, 0]}, **B},
               {"transition": {"op": "impulse", "id": 0, "dv": [40, 0, 0]}, **B},
               {"transition": {"op": "impulse", "id": 0, "dv": [0, 30, 0]}, **B},
               {"transition": {"op": "advance", "ticks": 8}, **B},
               {"transition": {"op": "spawn", "body": {"id": 1, "pos": [5, 5, 0], "vel": [0, 0, 0], "half": [1, 1, 1]}}, **B}]

    pressures = {"valley": pressure(W, valley), "doorway": pressure(W, doorway)}
    alloc = SAL.allocate(SAL.density(pressures), budget=1000, floor=50)
    print("possibility pressure (from horizon):", {k: v // (1 << 32) for k, v in pressures.items()}, "(units)")
    print("compute budget (1000, floor 50) by possibility:", alloc)
    print("=> the doorway gets %d%% of compute; the valley %d%% — possibility, not geometry, drove the budget."
          % (alloc["doorway"] * 100 // 1000, alloc["valley"] * 100 // 1000))
    print("   concentration:", SAL.concentration(alloc), "permille")
    print("\nThe committed world is byte-identical no matter how compute is allocated.")
    print("possibility → allocation (compute), NEVER possibility → physics. A possibility-aware runtime.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[salience] set PYTHONHASHSEED=0.\n\n")
        raise SystemExit(2)
    main()
