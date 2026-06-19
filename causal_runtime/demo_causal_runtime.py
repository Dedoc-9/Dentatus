"""
causal_runtime/demo_causal_runtime.py — causal allocation of computation (not causal simulation).

Shows the substrate end to end: three observation-domain fields -> one future-surface -> a per-channel compute
allocation, then the Causal Freshness Benchmark. The Aether-application invariant lives in
demo_aether_attention.py. Run under PYTHONHASHSEED=0.
"""
import field as F
import runtime as R
import freshness as FR

S = F.SCALE


def _allocation_demo():
    print("== causal allocation of computation (one future-surface, five channels) ==")
    # a tiny hidden switch (high consequence, high uncertainty) vs a big visible wall (high consequence, low unc)
    cons = {"switch": 400, "wall": 400, "npc": 120, "rock": 8}
    unc = {"switch": S, "wall": S // 5, "npc": S // 2, "rock": S}
    pos = {"switch": S, "wall": S, "npc": S, "rock": S}      # possibility uniform here
    af = R.AttentionField(budgets={"streaming": 100, "ai_tick": 60, "fidelity": 80,
                                   "network": 40, "validation": 12})
    toks = af.observe(cons, unc, pos)
    print("  future-surface & token:")
    for n in ("switch", "wall", "npc", "rock"):
        t = toks[n]
        print("    %-7s surface=%-6d depth=%d refresh=%3d budget=%d" % (
            n, t.surface, t.validation_depth, t.freshness, t.recommended_budget))
    al = af.allocation()
    print("  validation-depth budget (12) ->", {k: al["validation"][k] for k in ("switch", "wall", "npc", "rock")})
    print("  note: switch == wall in raw consequence; switch wins compute on UNCERTAINTY (the dual axis)\n")


def _freshness_demo():
    print("== Causal Freshness Benchmark (consequence×uncertainty vs distance/visibility) ==")
    rows = FR.run()
    for r in rows:
        print("  %-8s missed[visibility]=%.3f  missed[causal]=%.3f  (switches=%d)" % (
            r["world"], r["missed_visibility"], r["missed_causal"], r["switches"]))
    v, _ = FR.verdict(rows)
    print("  VERDICT:", v)
    print("  aligned = negative control (heuristic already right); hidden = low-visibility high-consequence\n")


if __name__ == "__main__":
    _allocation_demo()
    _freshness_demo()
    print("LAW:", R.AttentionField.law())
    print("Aether-application invariant: see demo_aether_attention.py (committed hash identical with/without observer)")
