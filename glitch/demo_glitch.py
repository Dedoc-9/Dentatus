"""
glitch/demo_glitch.py — find a latent bug by deterministic state-space exploration, then seal + replay it.

Run:  PYTHONHASHSEED=0 python3 demo_glitch.py

The system under test has a realistic LATENT bug: discounts STACK ADDITIVELY (a classic mistake), so two
60%-off events sum to 120% and yield a NEGATIVE price. No single input reveals it; it needs a specific
sequence. `glitch` explores the space, dedups states by content hash, finds the minimal trigger, seals it
into a signed ledger, and the Replay Court reproduces it bit-for-bit.

Honest scope: bounded model-check. Finding nothing at depth k is not a proof of absence. No quantum, no
parallelism, no bytecode injection — just deterministic search over the frozen core's public API.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import explorer as G
import core
from court import verify_chain, print_verdict
from signing import HmacSigner

# --- system under test: a price with an additive-discount-stacking bug (integers only, replay-safe) ---
INITIAL = {"cents": 1000, "total_pct": 0, "finalized": False, "final_cents": 0}
DISCOUNT_60 = {"op": "discount", "pct": 60}
DISCOUNT_25 = {"op": "discount", "pct": 25}
PURCHASE = {"op": "purchase"}
EVENTS = [DISCOUNT_60, DISCOUNT_25, PURCHASE]


def step(state, event):
    """Pure transition (does not mutate `state`)."""
    s = dict(state)
    if event["op"] == "discount" and not s["finalized"]:
        s["total_pct"] = s["total_pct"] + event["pct"]        # BUG: additive stacking, can exceed 100
    elif event["op"] == "purchase" and not s["finalized"]:
        s["final_cents"] = s["cents"] * (100 - s["total_pct"]) // 100
        s["finalized"] = True
    return s


def invariant(state):
    """A finalized price may never be negative."""
    return (not state["finalized"]) or state["final_cents"] >= 0


def fixed_step(state, event):
    """The patched transition: total discount is clamped to <= 100%."""
    s = dict(state)
    if event["op"] == "discount" and not s["finalized"]:
        s["total_pct"] = min(100, s["total_pct"] + event["pct"])
    elif event["op"] == "purchase" and not s["finalized"]:
        s["final_cents"] = s["cents"] * (100 - s["total_pct"]) // 100
        s["finalized"] = True
    return s


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("[glitch] run with PYTHONHASHSEED=0\n"); raise SystemExit(2)

    print("A) EXPLORE the buggy system (BFS, content-hash dedup, depth<=4):")
    res = G.explore(INITIAL, EVENTS, step, invariant, max_depth=4)
    print("   %r" % res)
    print("   counterexample path: %s" % [e["op"] + (str(e.get("pct", "")) if "pct" in e else "") for e in res.path])

    print("\nB) SHRINK to a minimal counterexample:")
    minimal = G.shrink(INITIAL, res.path, step, invariant)
    final = G.replay_path(INITIAL, minimal, step)
    print("   minimal: %s  ->  final_cents=%d (negative => bug)"
          % ([e["op"] + (str(e.get("pct", "")) if "pct" in e else "") for e in minimal], final["final_cents"]))

    print("\nC) SEAL the counterexample into a signed ledger; the breaking step is refused fail-closed:")
    ledger, refused, logic, gate = G.seal_counterexample(INITIAL, minimal, step, invariant, HmacSigner(b"glitch"))
    print("   sealed %d valid prefix step(s); refused event: %s" % (len(ledger), refused))

    print("\nD) REPLAY COURT reproduces the sealed prefix bit-for-bit:")
    print_verdict(verify_chain(ledger, b"glitch", logic, gate), len(ledger))

    print("\nE) Re-run EXPLORE against the FIXED system (bounded model-check):")
    res2 = G.explore(INITIAL, EVENTS, fixed_step, invariant, max_depth=4)
    print("   %r" % res2)
    print("   -> no counterexample within depth 4 (NOT a proof of total absence — integrity != truth).")

    print("\n   NOTE: dedup made the search cost ~distinct states (%d), not total paths. Deterministic," % res.distinct_states)
    print("   single-threaded, public-API only. No 'quantum', no magic parallelism, no bytecode injection.")
