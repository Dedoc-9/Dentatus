"""
airlock/demo_horizon.py — the geometry of the unrealized field; a state's possibility pressure. PYTHONHASHSEED=0.

Reality is a trajectory through a field of unrealized admissible alternatives. This measures the SHAPE of that
field around a realized state — the felt weight of what could have happened but did not.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adapters as A
import horizon as HZ

B = {"budget": {"max_cost": 9, "max_delta": 10**18}, "constraints": {"max_bodies": 3}}
S = 1 << 32


def show(label, world, candidates):
    g = HZ.neighborhood(world, 0, candidates, A)
    print("%-14s alternatives=%d  reach=%.1f  mean=%.1f  dispersion=%.1f  possibility_pressure=%.1f"
          % (label, g["alternatives"], g["reach"] / S, g["mean_distance"] / S, g["dispersion"] / S, g["possibility_pressure"] / S))


def main():
    W = A.K.make_world([A.K.body(0, (0, 5, 0), (0, 0, 0), (1, 1, 1))], ((-100, -100, -100), (100, 100, 100)))
    print("The same realized choice (a small nudge), surrounded by different fields of lawful alternatives:\n")
    show("alive state", W, [{"transition": {"op": "impulse", "id": 0, "dv": [1, 0, 0]}, **B},
                            {"transition": {"op": "impulse", "id": 0, "dv": [40, 0, 0]}, **B},
                            {"transition": {"op": "impulse", "id": 0, "dv": [0, 30, 0]}, **B},
                            {"transition": {"op": "advance", "ticks": 8}, **B},
                            {"transition": {"op": "spawn", "body": {"id": 1, "pos": [5, 5, 0], "vel": [0, 0, 0], "half": [1, 1, 1]}}, **B}])
    show("tight state", W, [{"transition": {"op": "impulse", "id": 0, "dv": [1, 0, 0]}, **B},
                            {"transition": {"op": "impulse", "id": 0, "dv": [2, 0, 0]}, **B},
                            {"transition": {"op": "impulse", "id": 0, "dv": [1, 1, 0]}, **B}])
    print("\nSame realized history; very different surrounding possibility. A player feels the second number, not")
    print("the first: worlds feel ALIVE when the engine knows what could have happened, not just what did.")
    print("Pure shadow telemetry — reality is never touched. A modeling lens, not a claim about nature.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[airlock] set PYTHONHASHSEED=0.\n\n")
        raise SystemExit(2)
    main()
