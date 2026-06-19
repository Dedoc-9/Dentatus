"""
salience/ccr.py — Consequence Capture Ratio: does possibility-attention beat distance-attention?

The deeper claim is not "possibility-aware rendering" but **possibility-aware ATTENTION** — a scheduler that
spends compute by *future consequence density* rather than proximity. To test it without circularity,
"consequence" is an INDEPENDENT counterfactual ground truth: how much the downstream world diverges *because*
an entity acts (act vs freeze) over a horizon — never defined via possibility itself.

    consequence(region) = ‖ advance(apply(most-impactful action))  −  advance(freeze) ‖   over H ticks

Then four rankers (distance, visibility, hand-authored importance, the cheap possibility atlas) each rank
regions; CCR = the fraction of total consequence captured by the top attention budget. The same atlas signal
serves every subsystem (AI, simulation, streaming, rendering) — one signal, many schedulers.

Pure-metric functions here are kernel-free (take score/consequence arrays). `consequence()` needs an adapter.
This is OBSERVABILITY: it measures where attention should go; it never gates physics. Stdlib only.
"""
import math


def consequence(world, candidates, adapter, horizon=12):
    """Independent counterfactual ground truth: downstream divergence from acting vs freezing, over `horizon`
    ticks. `apply`/`advance` are pure (no commit). Returns an exact-integer-derived float magnitude."""
    def advance(w):
        for _ in range(horizon):
            w = adapter.K.step(w) if hasattr(adapter, "K") else w
        return w
    base = advance(world)
    best, bd = None, -1
    for c in candidates:
        try:
            w2 = adapter.apply(world, c["transition"])
        except adapter.ApplyError:
            continue
        d = adapter.delta_norm(world, w2)
        if d > bd:
            bd, best = d, c
    if best is None:
        return 0.0
    acted = advance(adapter.apply(world, best["transition"]))
    return adapter.delta_norm(base, acted)


def spearman(a, b):
    if len(a) < 2:
        return 0.0
    ra = sorted(range(len(a)), key=lambda k: a[k]); rb = sorted(range(len(b)), key=lambda k: b[k])
    da = [0] * len(a); db = [0] * len(b)
    for i, k in enumerate(ra): da[k] = i
    for i, k in enumerate(rb): db[k] = i
    n = len(a); m = (n - 1) / 2
    cov = sum((da[i] - m) * (db[i] - m) for i in range(n))
    sa = math.sqrt(sum((x - m) ** 2 for x in da)); sb = math.sqrt(sum((x - m) ** 2 for x in db))
    return cov / (sa * sb) if sa > 0 and sb > 0 else 0.0


def ccr(scores, consequences, budget_frac=0.2):
    """Fraction of total consequence captured by the top `budget_frac` regions ranked by `scores`."""
    n = len(consequences)
    k = max(1, int(n * budget_frac))
    top = sorted(range(n), key=lambda i: scores[i], reverse=True)[:k]
    total = sum(consequences) or 1.0
    return sum(consequences[i] for i in top) / total


def compare(signals, consequences, budget_frac=0.2):
    """signals = {name: [score per region]}. Returns per-ranker CCR + Spearman, and an honest verdict:
    possibility 'wins-attention' iff it beats the AUTOMATIC proximity baselines (distance, visibility) AND at
    least matches hand-authored importance (≥ 90%). Matching importance automatically/at-scale IS the win."""
    rep = {name: {"ccr": ccr(s, consequences, budget_frac), "spearman": spearman(s, consequences)}
           for name, s in signals.items()}
    p = rep.get("possibility", {}).get("ccr", 0.0)
    d = rep.get("distance", {}).get("ccr", 1e9)
    v = rep.get("visibility", {}).get("ccr", 1e9)
    imp = rep.get("importance", {}).get("ccr", 0.0)
    beats_proximity = p > d and p > v
    matches_importance = p >= 0.9 * imp if imp > 0 else True
    rep["verdict"] = ("possibility-wins-attention" if (beats_proximity and matches_importance)
                      else "beats-proximity-not-importance" if beats_proximity
                      else "inconclusive")
    return rep
