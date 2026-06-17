"""
ration/meter.py — deterministic resource clamps (complexity-bound accounting).

THE IDEA: divorce resource limits from wall-clock time and physical bytes — both of which are
non-deterministic (a path fails on a slow box, passes on a fast one, breaking hardware-invariance). Instead
gate on EXACT INTEGER LOGICAL STEPS: loop iterations, tokens processed, state mutations, graph nodes
traversed. A pinned budget ceiling is enforced fail-closed on the frozen recorder, so an audit on a
10-year-old laptop resolves the exact same budget-exhaustion point as an enterprise array.

THE SPLIT (the workbench's exact-gate / captured-observable pattern):
  * GATE      — integer logical-step counts vs a precommitted ceiling. Exact, deterministic, replay-safe.
  * OBSERVABLE— physical cost (CPU ms, memory delta, billing) captured at the boundary, never gated, never
                in the commit hash (it is non-deterministic across machines).

HONEST BOUND: this stops a loop from running away *logically* and makes budget enforcement bit-identical
across machines. It does NOT prevent the host OS from OOM-killing you if the ceiling is set too loose, and
it does not measure real wall-clock cost (that's the observable). Integrity != truth.

Stdlib only; imports the frozen chronicle core read-only (Sibling Law).
"""
import os
import sys

_WB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
import core
from core import Recorder, ruleset_hash, InvariantViolation

CATEGORIES = ("iterations", "tokens", "mutations", "nodes")


class StepMeter:
    """An integer accumulator of logical steps by category. Pure; deterministic across hardware."""

    def __init__(self):
        self.counts = {c: 0 for c in CATEGORIES}

    def add(self, category, n=1):
        if category not in self.counts:
            self.counts[category] = 0
        self.counts[category] += int(n)
        return self

    def snapshot(self):
        return {c: int(self.counts.get(c, 0)) for c in sorted(self.counts)}


def step_total(counts, weights=None):
    """Weighted integer sum of logical steps. weights default to 1 each — all-integer, exact."""
    weights = weights or {}
    return sum(int(counts.get(c, 0)) * int(weights.get(c, 1)) for c in sorted(counts))


def within_budget(counts, policy):
    """policy = {"ceiling": int, "per_category": {cat: int}, "weights": {cat: int}}. Pure boolean gate."""
    if step_total(counts, policy.get("weights")) > int(policy["ceiling"]):
        return False
    for cat, lim in policy.get("per_category", {}).items():
        if int(counts.get(cat, 0)) > int(lim):
            return False
    return True
