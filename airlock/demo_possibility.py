"""
airlock/demo_possibility.py — the lawful possibility space, and "Hello, World" as a boundary crossing.
PYTHONHASHSEED=0.

"Arbitrary" in mathematics is not "anything" — it is any member of a lawful set, free within a declared
structure. Here the structure is the airlock; the lawful set is the ADMISSIBLE set. Making something concrete
is a projection through constraints: a possibility crosses the boundary and becomes an actual state.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import membrane as M
import adapters as A
import possibility as PS


def main():
    W = A.K.make_world([A.K.body(0, (0, 5, 0), (0, 0, 0), (1, 1, 1))], ((-10, -10, -10), (10, 10, 10)))
    B = {"budget": {"max_cost": 5, "max_delta": 10**18}, "constraints": {"max_bodies": 2}}
    candidates = [
        {"transition": {"op": "impulse", "id": 0, "dv": [1, 0, 0]}, **B},
        {"transition": {"op": "impulse", "id": 0, "dv": [0, 1, 0]}, **B},
        {"transition": {"op": "advance", "ticks": 3}, **B},
        {"transition": {"op": "impulse", "id": 0, "dv": [0.5, 0, 0]}, **B},     # float → CANON
        {"transition": {"op": "spawn", "body": {"id": 1, "pos": [3, 5, 0], "vel": [0, 0, 0], "half": [1, 1, 1]}}, **B},
        {"transition": {"op": "teleport"}, **B},                               # SCHEMA
    ]
    g = PS.admissible_set(W, candidates, A)
    print("possible  = %d candidate transitions" % g["candidates"])
    print("admissible = %s   (lawful freedom: %d permille of the proposed space)" % (g["admissible"], g["freedom_permille"]))
    print("inadmissible = %s   (filtered at the boundary, by gate)" % g["inadmissible"])

    chosen = g["admissible"][0]
    print("\n'Let x be arbitrary' = pick any member of the admissible set; here we realize index %d." % chosen)
    print("admissible-but-UNREALIZED (every bit as lawful, simply not chosen): %s" % PS.unrealized_admissible(g, chosen))

    # the boundary crossing — a possibility becomes an actual state
    r = M.propose(W, candidates[chosen], A)
    print("\nHello, World:  a possibility crossed the boundary and became an actual state.")
    print("  committed post_hash = %s" % r["shard"]["post_hash"][:16])
    print("\n('arbitrary' = freedom constrained by an unseen boundary. In math: axioms. In physics: laws.")
    print(" In this engine: the airlock. The realized world is a projection of the possible through constraints.)")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[airlock] set PYTHONHASHSEED=0.\n\n")
        raise SystemExit(2)
    main()
