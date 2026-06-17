"""
ration/demo_ration.py — hardware-invariant resource budgeting on the frozen ledger.

Run:  PYTHONHASHSEED=0 python3 demo_ration.py

  A. WITHIN BUDGET   — an agent loop accumulates logical steps under the ceiling; the transition commits,
                       physical cost captured as an observable.
  B. QUOTA BREACH    — a runaway loop pushes the integer step total past the precommitted ceiling; the
                       commit is refused fail-closed and rolls back.
  C. HARDWARE-INVARIANT — the SAME logical run on a "fast" vs a "slow" machine (different captured CPU ms,
                       identical step counts) resolves the identical gate outcome and content hash.
  D. REPLAY          — the Replay Court reproduces the sealed runs bit-for-bit (CPU ms read from the
                       record, never recomputed).

Honest bound: the gate is integer logical steps, not wall-clock; physical cost is an observable, never a
gate. It does not stop an OS OOM if the ceiling is too loose. Integrity != truth.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meter as M
import core
from court import verify_chain, print_verdict
from signing import HmacSigner

POLICY = {"ceiling": 1000, "per_category": {"tokens": 800}, "weights": {"tokens": 1, "iterations": 1, "mutations": 5, "nodes": 1}}


def run_logic(inputs):
    """Deterministic: total logical steps from the integer counts; CPU ms is read from capture (observable)."""
    return {"total_steps": M.step_total(inputs["counts"], POLICY.get("weights")),
            "counts": inputs["counts"], "cpu_ms_observable": inputs["_cap"]["cpu_ms"]}


def budget_invariant(inputs, outputs):
    """Fail-closed: refuse to commit a transition that breaches the precommitted logical budget."""
    return M.within_budget(inputs["counts"], POLICY)


def _sealed(counts, cpu_ms):
    return {"counts": counts, "_cap": {"cpu_ms": cpu_ms}}


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("[ration] run with PYTHONHASHSEED=0\n"); raise SystemExit(2)

    rec = core.Recorder(HmacSigner(b"ration"), core.ruleset_hash(run_logic, budget_invariant))
    ledger = []

    print("A) WITHIN BUDGET (ceiling=%d, tokens<=800):" % POLICY["ceiling"])
    m = M.StepMeter()
    for _ in range(300):
        m.add("iterations").add("tokens", 2)   # 300 iters + 600 tokens = 900 logical steps
    sealed = _sealed(m.snapshot(), cpu_ms=41.7)
    r = rec.record("RUN-OK", sealed, run_logic(sealed), budget_invariant)
    ledger.append(r)
    print("   total_steps=%d  cpu_ms(obs)=%.1f  -> SEALED +%s"
          % (r["frame"]["outputs"]["total_steps"], r["frame"]["outputs"]["cpu_ms_observable"], r["committed_hash"][:10]))

    print("\nB) QUOTA BREACH (runaway loop):")
    m2 = M.StepMeter()
    for _ in range(900):
        m2.add("tokens", 2)                     # 1800 tokens -> exceeds tokens cap AND total ceiling
    bad = _sealed(m2.snapshot(), cpu_ms=120.0)
    try:
        rec.record("RUN-RUNAWAY", bad, run_logic(bad), budget_invariant)
        print("   committed (should NOT happen)")
    except core.InvariantViolation as e:
        print("   QuotaBreached -> refused fail-closed: total=%d, tokens=%d" % (M.step_total(bad["counts"]), bad["counts"]["tokens"]))

    print("\nC) HARDWARE-INVARIANT (same logical run, different physical cost):")
    fast = _sealed(m.snapshot(), cpu_ms=12.3)    # "fast machine"
    slow = _sealed(m.snapshot(), cpu_ms=410.9)   # "slow machine"
    of, osl = run_logic(fast), run_logic(slow)
    print("   fast cpu_ms=%.1f total_steps=%d   slow cpu_ms=%.1f total_steps=%d"
          % (of["cpu_ms_observable"], of["total_steps"], osl["cpu_ms_observable"], osl["total_steps"]))
    print("   gate outcome identical: %s   (the budget keys off integer steps, not the clock)"
          % (M.within_budget(fast["counts"], POLICY) == M.within_budget(slow["counts"], POLICY)))

    print("\nD) REPLAY COURT verifies the sealed runs (cpu_ms read from the record, not recomputed):")
    print_verdict(verify_chain(ledger, b"ration", run_logic, budget_invariant), len(ledger))
