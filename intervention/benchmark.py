"""
intervention/benchmark.py — the Causal Intervention Benchmark.

Three worlds where OBSERVATION (ghost/persistence) gives the SAME signal — A and C move together — but
INTERVENTION separates them. Each is a deterministic integer dynamics; the query holds A (and C) constant in a
shadow copy and watches what survives:

    world        structure      do(A) → C ?   do(C) → A ?   verdict
    true         A → C          yes           no            CONFIRMED  (directed evidence A→C)
    confounder   A ← X → C      no            no            REJECTED   (C rides X, not A — persistence cannot see this)
    feedback     A ⇄ C          yes           yes           CYCLE      (warning, never a stronger edge)

The confounder is the headline: persistence proposed (A,C) because they co-occur, and ONLY intervention can
reject it. The committed history is never touched (all probes run on discarded shadow copies). Deterministic.
"""
from protocol import make
from query import query

MOD = 1_000_003


def true_world():
    """A is exogenous; C is a direct function of A (A → C)."""
    init = {"A": 5, "C": 0, "drive": 7}

    def dyn(s):
        return {"A": (s["A"] + s["drive"]) % MOD, "C": (3 * s["A"]) % MOD, "drive": s["drive"]}
    return init, dyn


def confounder_world():
    """Hidden X drives BOTH A and C (A ← X → C). A and C correlate, but neither causes the other."""
    init = {"X": 2, "A": 0, "C": 0, "drive": 5}

    def dyn(s):
        return {"X": (s["X"] + s["drive"]) % MOD, "A": (2 * s["X"]) % MOD,
                "C": (4 * s["X"]) % MOD, "drive": s["drive"]}
    return init, dyn


def feedback_world():
    """A and C drive each other (A → C → A): a cycle."""
    init = {"A": 3, "C": 1, "drive": 7}

    def dyn(s):
        return {"A": (s["C"] + s["drive"]) % MOD, "C": (2 * s["A"]) % MOD, "drive": s["drive"]}
    return init, dyn


WORLDS = {"true": true_world, "confounder": confounder_world, "feedback": feedback_world}


def run():
    out = {}
    for name, build in WORLDS.items():
        init, dyn = build()
        out[name] = query(make("A", "C"), dyn, init)
    return out


def verdict(rows=None):
    rows = rows or run()
    v = {k: r.verdict for k, r in rows.items()}
    ok = (v["true"] == "CONFIRMED" and v["confounder"] == "REJECTED" and v["feedback"] == "CYCLE")
    return ("intervention-separates-cause-confounder-cycle" if ok else "inconclusive"), v


if __name__ == "__main__":
    rows = run()
    for name in ("true", "confounder", "feedback"):
        r = rows[name]
        print("%-11s verdict=%-11s fwd=%-7d bwd=%-7d  (%s)"
              % (name, r.verdict, r.effect_fwd, r.effect_bwd, r.reason))
    label, v = verdict(rows)
    print("\nVERDICT:", label)
    print("confounder REJECTED is the case persistence alone could not resolve.")
    print("LAW: causal_information -> experiment ALLOWED (airlock, shadow-only) ; -> truth FORBIDDEN")
