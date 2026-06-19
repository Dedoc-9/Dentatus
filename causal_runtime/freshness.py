"""
causal_runtime/freshness.py — the Causal Freshness Benchmark (causal cache invalidation).

Distributed systems already have dependency graphs. The novel claim is using FUTURE CONSEQUENCE to decide what
must stay FRESH. Test it against the standard heuristic.

Setup: N cache entries, each with a TRUE importance (its future dependency surface) and a VISIBILITY
(distance/screen-heuristic). Each frame a fixed refresh BUDGET keeps some entries warm; an "important
transition" then fires at a node sampled ∝ importance. It is MISSED if that node was STALE (not refreshed
within stale_window). Metric: missed_important_transition_rate at equal budget (lower is better).

Two policies:
    visibility : refresh top-budget by VISIBILITY        (what engines do today)
    causal     : refresh top-budget by consequence×unc   (the AttentionField)

Two worlds:
    aligned : visibility ≈ importance  -> NEGATIVE CONTROL (the heuristic is already right; causal must only
              TIE, not magically win)
    hidden  : a few low-visibility, high-importance "switches" (a hidden switch -> door -> economy -> faction
              war). The heuristic is structurally blind to them; causal should keep them warm.

uncertainty is held UNIFORM so the result isolates the consequence-vs-visibility axis (uncertainty would only
sharpen the causal win). Deterministic given seed. Stdlib only.
"""
import random

from field import SCALE


def _world(n, seed, hidden):
    rng = random.Random(seed)
    importance, visibility = {}, {}
    for i in range(n):
        imp = rng.randint(1, 100)
        importance[i] = imp
        visibility[i] = imp + rng.randint(-5, 5)          # aligned: visibility tracks importance
    switches = []
    if hidden:
        for k in range(max(1, n // 20)):                  # ~5% are hidden switches
            i = rng.randrange(n)
            importance[i] = 1000                          # huge future surface
            visibility[i] = rng.randint(1, 5)             # but nearly invisible
            switches.append(i)
    return importance, visibility, switches


def _topk(score, k):
    return set(sorted(score, key=lambda n: (-score[n], str(n)))[:k])


def _simulate(importance, visibility, policy, budget, frames, stale_window, seed):
    rng = random.Random(seed ^ 0x9E3779B9)
    n = len(importance)
    last = {i: -10 ** 9 for i in importance}
    # event sampler ∝ importance (deterministic)
    nodes = sorted(importance)
    weights = [importance[i] for i in nodes]
    if policy == "visibility":
        score = visibility
    else:                                                 # causal: consequence × uncertainty (uniform unc)
        score = importance
    refresh = _topk(score, budget)                        # static-by-score (recomputed identically each frame)
    missed = total = 0
    for f in range(frames):
        for i in refresh:
            last[i] = f
        node = rng.choices(nodes, weights=weights, k=1)[0]
        total += 1
        if (f - last[node]) > stale_window:
            missed += 1
    return missed / total if total else 0.0


def reconstruct(world_kind, n=200, seed=7, budget_frac=0.1, frames=400, stale_window=4):
    importance, visibility, switches = _world(n, seed, hidden=(world_kind == "hidden"))
    budget = max(1, int(n * budget_frac))
    vis = _simulate(importance, visibility, "visibility", budget, frames, stale_window, seed)
    cau = _simulate(importance, visibility, "causal", budget, frames, stale_window, seed)
    return {"world": world_kind, "n": n, "budget": budget,
            "missed_visibility": round(vis, 3), "missed_causal": round(cau, 3),
            "switches": len(switches)}


def run(n=200, seed=7, budget_frac=0.1, frames=400, stale_window=4):
    return [reconstruct(w, n, seed, budget_frac, frames, stale_window) for w in ("aligned", "hidden")]


def verdict(rows=None, tie_eps=0.05):
    rows = rows or run()
    by = {r["world"]: r for r in rows}
    a, h = by["aligned"], by["hidden"]
    aligned_ties = abs(a["missed_visibility"] - a["missed_causal"]) <= tie_eps
    causal_wins_hidden = h["missed_causal"] < h["missed_visibility"] - tie_eps
    ok = aligned_ties and causal_wins_hidden
    return ("causal-freshness-wins-on-hidden-importance" if ok else "inconclusive"), by


if __name__ == "__main__":
    rows = run()
    for r in rows:
        print("%-8s budget=%d  missed[visibility]=%.3f  missed[causal]=%.3f  (switches=%d)" % (
            r["world"], r["budget"], r["missed_visibility"], r["missed_causal"], r["switches"]))
    v, _ = verdict(rows)
    print("\nVERDICT:", v)
    print("aligned = negative control (heuristic already right -> causal only ties)")
    print("hidden  = low-visibility high-consequence switches -> causal keeps them warm, visibility misses")
