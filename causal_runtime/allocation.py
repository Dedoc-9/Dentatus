"""
causal_runtime/allocation.py — the FORMAL test of an attention field: a scoring function judged by decisions.

The root principle ("the field allocates attention, not truth") has a precise mathematical reading. The field
is a scoring function `F`; the only rigorous question is **does using F improve decisions under a fixed budget?**
Three claims hide inside, and they are not equally decidable:

  1. ALLOCATION claim (testable). Given budget B, allocating by F captures more TRUE importance M than allocating
     by a baseline:   max Σ aᵢ Mᵢ  s.t.  Σ aᵢ cᵢ ≤ B.  Test: greedy-by-F vs greedy-by-baseline, scored on M.
  2. PREDICTIVE claim (testable). F ranks items by their true future importance:  Spearman(F, M) > baselines.
  3. ONTOLOGY claim (NOT decidable). "F captures what truly matters." Undecidable, because M is not a
     mathematical primitive — player score, win-probability, entropy, economic value, narrative weight are all
     different choices of M. The math can show `F → M predicts well`; it can never show `M` is the right notion
     of importance.

This module makes (1) and (2) runnable and makes (3) STRUCTURAL: **M is an explicit, independent parameter** —
never the allocator's own score — so every verdict is "better under *this* M," never "F is true." And the test
is built to be **falsifiable**: a world where F is a bad estimate of M must show F LOSING to a baseline. A test
that cannot fail the field is circular. Deterministic integer math. Stdlib only.
"""
import random


def allocate(items, budget, score_key, cost_key="cost"):
    """Greedy knapsack by score/cost ratio — the allocation decision aᵢ. Returns the chosen id-set.
    Deterministic (ties broken by id)."""
    ranked = sorted(items, key=lambda o: (-(o[score_key] * 1000) // max(1, o[cost_key]), str(o["id"])))
    chosen, spent = set(), 0
    for o in ranked:
        if spent + o[cost_key] <= budget:
            chosen.add(o["id"]); spent += o[cost_key]
    return chosen


def captured(items, chosen, m_key="M"):
    """Σ aᵢ Mᵢ — the TRUE importance captured by an allocation, scored on the independent objective M."""
    return sum(o[m_key] for o in items if o["id"] in chosen)


def _ranks(vals):
    order = sorted(vals, key=lambda k: (vals[k], str(k)))
    return {k: i for i, k in enumerate(order)}


def spearman_q(a, b):
    """Spearman rank correlation × 1000 (integer, deterministic) over common keys. +1000 = perfect, -1000 = anti."""
    keys = sorted(set(a) & set(b), key=str)
    n = len(keys)
    if n < 2:
        return 0
    ra, rb = _ranks({k: a[k] for k in keys}), _ranks({k: b[k] for k in keys})
    d2 = sum((ra[k] - rb[k]) ** 2 for k in keys)
    return 1000 - (6 * d2 * 1000) // (n * (n * n - 1))


def evaluate(items, budget, estimate="future_surface", baselines=("distance", "magnitude"), m_key="M"):
    """Run claim 1 (allocation utility) + claim 2 (predictive correlation) for the estimate F vs baselines,
    against the independent objective M. `oracle` allocates by M itself (upper bound); `random` is the floor."""
    rng = random.Random(0)
    for o in items:
        o.setdefault("random", rng.randint(0, 1_000_000))
    policies = [estimate, *baselines, "random", m_key]            # m_key as the oracle
    cap = {p: captured(items, allocate(items, budget, p), m_key) for p in policies}
    by_id = lambda k: {o["id"]: o[k] for o in items}
    corr = {p: spearman_q(by_id(p), by_id(m_key)) for p in (estimate, *baselines, "random")}
    return {"captured": cap, "spearman_to_M": corr, "estimate": estimate, "oracle": m_key}


# ---- worlds: F is an ESTIMATE of M; M is the independent objective -----------------------------------------

def _world(kind, n=60, seed=1):
    rng = random.Random(seed)
    items = []
    for i in range(n):
        M = rng.randint(1, 1000)                                  # the true importance (the chosen objective)
        cost = rng.randint(1, 10)
        if kind == "aligned":                                     # F ≈ distance ≈ M (negative control)
            fs = M + rng.randint(-50, 50); dist = M + rng.randint(-50, 50)
        elif kind == "future_wins":                              # F tracks M; distance/magnitude do not
            fs = M + rng.randint(-50, 50); dist = rng.randint(1, 1000)
        elif kind == "future_loses":                            # F is a BAD estimate; distance tracks M (falsifiability)
            fs = rng.randint(1, 1000); dist = M + rng.randint(-50, 50)
        else:
            raise ValueError(kind)
        items.append({"id": "o%d" % i, "M": M, "cost": cost,
                      "future_surface": max(1, fs), "distance": max(1, dist),
                      "magnitude": rng.randint(1, 1000)})
    return items


WORLDS = ("aligned", "future_wins", "future_loses")


def run(budget_frac=0.3):
    out = {}
    for w in WORLDS:
        items = _world(w)
        budget = int(sum(o["cost"] for o in items) * budget_frac)
        out[w] = evaluate(items, budget)
    return out


def verdict(rows=None, eps=0.03):
    rows = rows or run()
    def rel(w, p):
        c = rows[w]["captured"]; return c[p] / max(1, c["M"])     # captured as fraction of the oracle
    aligned_ties = abs(rel("aligned", "future_surface") - rel("aligned", "distance")) <= eps
    future_wins = rel("future_wins", "future_surface") > rel("future_wins", "distance") + eps
    future_loses = rel("future_loses", "future_surface") < rel("future_loses", "distance") - eps  # MUST fail here
    ok = aligned_ties and future_wins and future_loses
    return ("allocation-test-is-comparative-and-falsifiable" if ok else "inconclusive"), rows


if __name__ == "__main__":
    rows = run()
    print("Formal allocation test — captured TRUE importance M as %% of the oracle (M-greedy), at equal budget:\n")
    for w in WORLDS:
        c = rows[w]["captured"]; o = max(1, c["M"])
        print("  %-13s future_surface=%3d%%  distance=%3d%%  magnitude=%3d%%  random=%3d%%   |  Spearman(F,M)=%+d"
              % (w, 100 * c["future_surface"] // o, 100 * c["distance"] // o, 100 * c["magnitude"] // o,
                 100 * c["random"] // o, rows[w]["spearman_to_M"]["future_surface"]))
    label, _ = verdict(rows)
    print("\nVERDICT:", label)
    print("  aligned      = negative control (F and distance are equally good estimates of M -> tie)")
    print("  future_wins  = F is a better estimate of M than distance/magnitude -> captures more true M")
    print("  future_loses = F is a BAD estimate of M -> it LOSES to distance (the test CAN fail the field)")
    print("\nClaim 1 (allocation) & Claim 2 (prediction) are testable above. Claim 3 (ontology) is NOT: M is the")
    print("chosen objective, an INPUT — swap M and the verdict can flip. The math shows F ranks M well; it never")
    print("shows M is 'what truly matters'. The field allocates attention; it does not allocate truth.")
