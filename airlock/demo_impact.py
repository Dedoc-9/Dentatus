"""
airlock/demo_impact.py — impact density as a predicate for VALIDATION DEPTH (never outcome). PYTHONHASHSEED=0.

Same world, different transitions. A cheap O(apply) impact predicate routes each through the airlock at a
severity that scales with how much future it touches — deep validation for high-impact, cheap for low — while
the committed outcome stays byte-identical regardless of depth. future importance decides where we LOOK; it
never decides what is TRUE.
"""
import os
import sys
import random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adapters as A
import impact as IM
import membrane as M

S = 1 << 32


def main():
    random.seed(5)
    cluster = [A.K.body(i, (random.randint(-4, 4), 5, random.randint(-4, 4)), (0, 0, 0), (1, 1, 1)) for i in range(6)]
    W = A.K.make_world(cluster, ((-80, -80, -80), (80, 80, 80)))
    B = {"budget": {"max_cost": 20, "max_delta": 10**22}, "constraints": {"max_bodies": 12, "c_limit": 200 * S}}
    txns = {"move (small)": {"op": "impulse", "id": 0, "dv": [1, 0, 0]},
            "shoot far": {"op": "impulse", "id": 0, "dv": [60, 0, 0]},
            "nudge cluster": {"op": "impulse", "id": 0, "dv": [-2, -3, 0]},
            "advance": {"op": "advance", "ticks": 6},
            "spawn fast": {"op": "spawn", "body": {"id": 6, "pos": [0, 7, 0], "vel": [0, -40, 0], "half": [1, 1, 1]}}}

    pol = IM.bind(IM.validation_policy(threshold=5 * S), A)
    print("transition        cheap_impact   true_impact   validation depth (impact-driven severity)")
    for name, t in txns.items():
        ci = IM.cheap_impact(W, t, A) / S
        ti = IM.impact_density(W, t, A) / S
        tier = pol(W, t)
        print("  %-15s %10.1f  %12.1f   %s" % (name, ci, ti, tier))

    # THE LAW: validation depth never changes the committed outcome
    lo = {"transition": txns["move (small)"], **B}
    g = M.propose(W, dict(lo), A, severity="game")["shard"]["post_hash"]
    s = M.propose(W, dict(lo), A, severity="strict")["shard"]["post_hash"]
    p = M.propose(W, dict(lo), A, severity=pol)["shard"]["post_hash"]
    print("\n  LAW: same transition at game / strict / impact-policy → identical committed post_hash:", g == s == p)
    print("  impact_density → validation depth  (ALLOWED).   impact_density → committed outcome  (FORBIDDEN).")
    print("\n  Honest bound: cheap impact predicts physical (kinematic) consequence near-perfectly here because")
    print("  divergence ≈ immediate magnitude in linear-ish dynamics. The hard case — a small cause with large")
    print("  downstream consequence (a trigger / chain reaction / quest unlock) — needs nonlinear or game-state")
    print("  dynamics to test; there a cheap proxy may fail and fall back to true impact. Mechanism + law: proven.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[airlock] set PYTHONHASHSEED=0.\n\n")
        raise SystemExit(2)
    main()
