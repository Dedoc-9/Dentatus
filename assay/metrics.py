"""
assay/metrics.py — DETERMINISTIC, recomputable quality metrics (the 'correct' and 'fair' tiers).

These are pure functions of recorded evidence, so the assay court can re-run them bit-for-bit and catch a
fudged number. They do NOT certify truth:
  * correctness is only as good as the oracle/label supplied as ground truth;
  * a fairness metric is a population property, requires sensitive labels, and different fairness
    definitions provably conflict — this records ONE chosen metric, it does not declare a system 'fair'.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "llm_toolkit"))
import agent_core as core


def correctness_vs_oracle(evidence):
    """evidence = {"decision": {...}, "ground_truth": {...}, "key": "<field>"}.
    Compares one decision field against a supplied ground-truth label. Recomputable."""
    key = evidence["key"]
    got = evidence["decision"].get(key)
    exp = evidence["ground_truth"].get(key)
    return {"correct": bool(got == exp), "got": got, "expected": exp}


def group_approval_parity(evidence):
    """evidence = {"cohort": [{"group": g, "<decision_key>": bool}, ...],
                   "decision_key": "approved", "tolerance": 0.10}.
    Approval rate per group + max pairwise disparity vs a tolerance. Recomputable. (Demographic-parity
    style; deliberately ONE metric — equalized-odds etc. can disagree.)"""
    dk = evidence["decision_key"]
    counts = {}
    for d in evidence["cohort"]:
        g = d["group"]
        c = counts.setdefault(g, [0, 0])
        c[1] += 1
        if d.get(dk):
            c[0] += 1
    rates = {g: round(c[0] / c[1], 6) for g, c in sorted(counts.items()) if c[1] > 0}
    disparity = round(max(rates.values()) - min(rates.values()), 6) if rates else 0.0
    return {"rates": rates, "max_disparity": disparity,
            "within_tolerance": bool(disparity <= evidence["tolerance"])}


# name -> function. The court binds a metric by source_hash(fn), so swapping the logic is detectable.
METRICS = {
    "correctness_vs_oracle": correctness_vs_oracle,
    "group_approval_parity": group_approval_parity,
}


def metric_verdict(dimension, value):
    """Derive a pass/fail from a metric value. Pure + recomputable, so a tampered verdict is caught."""
    if dimension == "correct":
        return "pass" if value.get("correct") else "fail"
    if dimension == "fair":
        return "pass" if value.get("within_tolerance") else "fail"
    return "n/a"
