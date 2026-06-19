"""
toolkit.allocation — the two proven primitives (allocation + measurement).

Logic is identical to causal_runtime/allocation.py. Kept here so the toolkit is self-contained.

  allocate()  — a deterministic greedy knapsack by score/cost ratio (ties broken by id).
  captured()  — the score-INDEPENDENT objective sum: the only honest way to grade an allocation.
"""
from __future__ import annotations


def allocate(items, budget, score_key, cost_key="cost"):
    """Greedy knapsack by score/cost. Returns (chosen id-set, spent). Deterministic; ties break by id."""
    ranked = sorted(items, key=lambda o: (-(o[score_key] * 1000) // max(1, o[cost_key]), str(o["id"])))
    chosen, spent = set(), 0
    for o in ranked:
        if spent + o[cost_key] <= budget:
            chosen.add(o["id"]); spent += o[cost_key]
    return chosen, spent


def captured(items, chosen, objective):
    """Sum, over the chosen set, of the INDEPENDENT objective — never the allocator's own score.

    This is what prevents the classic mistake: "my model picked well because my model says so."
    The allocation is always graded against a quantity the scorer never saw.
    """
    return sum(o[objective] for o in items if o["id"] in chosen)
