"""
airlock/demo_airlock.py — the LLM→AetherPulse membrane end-to-end (transitions-only). PYTHONHASHSEED=0.

Shows the "governed creative workspace": an EXTERNAL planner decomposes a goal into candidate transitions
(intent lives outside the membrane); the membrane admits only bounded, canonical, reproducible ones; every
attempt — commit or reject — leaves auditable evidence; reality changes only through the kernel.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adapters as A
import membrane as M

K = A.K


def plan_goal_to_transitions(goal):
    """OUTSIDE the membrane: an (untrusted) planner turns a goal into candidate transitions. The kernel
    never sees the goal — only the decomposed, bounded proposals (intent != authority)."""
    return [
        {"op": "spawn", "body": {"id": 1, "pos": [3, 8, 0], "vel": [0, 0, 0], "half": [1, 1, 1]}},
        {"op": "impulse", "id": 0, "dv": [2, 0, 0]},
        {"op": "impulse", "id": 0, "dv": [0.5, 0, 0]},          # float — will fail CANON
        {"op": "spawn", "body": {"id": 2, "pos": [0, 0, 0], "vel": [0, 0, 0], "half": [1, 1, 1]}},  # max_bodies
        {"op": "advance", "ticks": 5},
    ]


def main():
    W = K.make_world([K.body(0, (0, 5, 0), (0, 0, 0), (1, 1, 1))], ((-10, -10, -10), (10, 10, 10)))
    L = M.Ledger()
    budget = {"max_cost": 16, "max_delta": 10**15}
    constraints = {"max_bodies": 2, "in_bounds": True}

    print("GOAL (untrusted, outside the membrane): 'add a falling box and shove the first one'")
    print("planner decomposes -> candidate transitions; the kernel only ever sees bounded proposals.\n")
    print("  %-42s -> %s" % ("transition", "verdict"))
    for txn in plan_goal_to_transitions("make it lively"):
        p = {"transition": txn, "budget": budget, "constraints": constraints,
             "claims": {"expect_tick": W.get("tick", 0)}, "provenance": {"who": "llm-planner"}}
        r = M.propose(W, p, A, ledger=L)
        if r["ok"]:
            W = r["world"]
            tag = "COMMIT  post=%s R_p=%s" % (r["shard"]["post_hash"][:10], r["telemetry"]["R_p"])
        else:
            tag = "REJECT(%s) %s" % (r["gate"], r["reason"][:32])
        print("  %-42s -> %s" % (str(txn)[:42], tag))

    print("\nLedger: %d commits, %d rejections (every attempt is auditable evidence)." % (len(L.commits), len(L.rejections)))
    print("Final committed world hash:", A.state_hash(W)[:16])
    print("\nLaws held:  intent != authority (claims/provenance never committed state)")
    print("            telemetry != control (R_p measured, never gated)")
    print("Reality changed only through canon -> budget -> shadow -> validate -> commit. integrity != truth.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[airlock] set PYTHONHASHSEED=0.\n\n")
        raise SystemExit(2)
    main()
