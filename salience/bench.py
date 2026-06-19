"""
salience/bench.py — the Distance vs Cheap vs True falsification (pure metrics, kernel-free).

The sharp question (from the debate): not "does possibility beat distance" (trivially yes), but —
    can a CHEAP O(local) predictor approximate possibility well enough to outperform distance,
    after overhead, when amortized through a Possibility Atlas?

These are pure functions over per-region maps {region: value}: `true` (expensive ground truth), `cheap`
(predictor estimate), `distance` (the industry baseline). The demo feeds real airlock/horizon values in.

Key correction surfaced by the prototype: naive ROA = impactful/cost OVER-REWARDS the cheapest signal
(distance is cheapest, so it scores high ROA despite low quality). The honest frame is the ATLAS: per-frame
all signals are O(1) lookups (equal cost), so the differentiators are (a) QUALITY — does the atlas put
compute on real possibility — and (b) FRESHNESS — can the atlas be refreshed cheaply enough to stay current.
"""
import math


def _norm(vals):
    s = sum(vals)
    return [v / s for v in vals] if s > 0 else [0.0] * len(vals)


def spearman(a, b):
    if len(a) < 2:
        return 0.0
    ra = sorted(range(len(a)), key=lambda k: a[k]); rb = sorted(range(len(b)), key=lambda k: b[k])
    da = [0] * len(a); db = [0] * len(b)
    for i, k in enumerate(ra): da[k] = i
    for i, k in enumerate(rb): db[k] = i
    n = len(a); mean = (n - 1) / 2
    cov = sum((da[i] - mean) * (db[i] - mean) for i in range(n))
    sa = math.sqrt(sum((x - mean) ** 2 for x in da)); sb = math.sqrt(sum((x - mean) ** 2 for x in db))
    return cov / (sa * sb) if sa > 0 and sb > 0 else 0.0


def top_k_overlap(estimate, truth, k):
    """Fraction of the TRUE top-k regions the estimate also ranks in its top-k. This is what matters: land
    compute on the actually-high-possibility regions; overall correlation matters less than top-k ranking."""
    idx = list(range(len(truth)))
    te = set(sorted(idx, key=lambda i: truth[i], reverse=True)[:k])
    ee = set(sorted(idx, key=lambda i: estimate[i], reverse=True)[:k])
    return len(te & ee) / k if k else 0.0


def impactful_captured(allocation, truth):
    """QUALITY: dot(normalized allocation, normalized true possibility) — how much real possibility the
    compute landed on. Max when the allocation matches the true field."""
    a = _norm([max(x, 0.0) for x in allocation]); t = _norm([max(x, 0.0) for x in truth])
    return sum(a[i] * t[i] for i in range(len(t)))


def frames_to_refresh_all(per_region_cost_us, n_regions, maintenance_budget_us):
    """FRESHNESS: with a fixed per-frame maintenance budget, how many frames to refresh the whole atlas.
    1 ⇒ always fresh; large ⇒ stale. Cheap signal ⇒ ~1; expensive (true) ⇒ many."""
    if maintenance_budget_us <= 0:
        return float("inf")
    return max(1, math.ceil(per_region_cost_us * n_regions / maintenance_budget_us))


def evaluate(true, cheap, distance, costs, n_regions, maintenance_budget_us, top_frac=0.2):
    """Full falsification report + verdict. costs = {distance, cheap, true} per-region µs."""
    k = max(1, int(n_regions * top_frac))
    q_true = impactful_captured(true, true)
    q_cheap = impactful_captured(cheap, true)
    q_dist = impactful_captured(distance, true)
    fresh = {sig: frames_to_refresh_all(costs[sig], n_regions, maintenance_budget_us)
             for sig in ("distance", "cheap", "true")}
    rep = {
        "accuracy_spearman": spearman(cheap, true),
        "accuracy_topk": top_k_overlap(cheap, true, k),
        "quality": {"true": q_true, "cheap": q_cheap, "distance": q_dist},
        "quality_cheap_vs_true_pct": (100 * q_cheap / q_true) if q_true else 0,
        "quality_cheap_vs_distance_x": (q_cheap / q_dist) if q_dist else float("inf"),
        "cost_us": costs,
        "cost_cheap_vs_true_pct": (100 * costs["cheap"] / costs["true"]) if costs["true"] else 0,
        "frames_to_refresh_all": fresh,
    }
    # Verdict: cheap is the practical winner iff it keeps most of true's quality, beats distance's quality,
    # costs a small fraction of true, AND (atlas) stays fresh where true cannot.
    rep["verdict"] = ("cheap-wins"
                      if (q_cheap >= 0.8 * q_true and q_cheap > q_dist
                          and costs["cheap"] <= 0.1 * costs["true"]
                          and fresh["cheap"] <= fresh["true"])
                      else "inconclusive")
    return rep
