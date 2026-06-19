"""
causal_runtime/lod.py — the LOD Falsification Bench: does the future-surface field reach the IMAGE?

Everything upstream allocates COMPUTE, validation, network, AI. Rasterization is the last consumer, and it asks
a different question — *which pixels can safely receive less effort?* — so consequence alone cannot drive it.
The new bound:

    consequence ≠ visibility

A mountain dominates half the screen with zero future surface; a quest switch controls the world in 3 pixels.
So the render-priority quantity is a PRODUCT, not a field already built:

    render_priority(node) = future_surface(node) × perceptual_sensitivity(node)

where perceptual_sensitivity ≈ screen_coverage (error you can actually SEE). This reproduces both cases by
construction: the switch (huge future_surface × ~0 coverage) gets ~0 render budget; the collapsing bridge
(huge future_surface × real coverage) gets a lot.

This is a FALSIFICATION BENCH, not a renderer. It allocates a fixed TRIANGLE budget across objects by three
policies — distance LOD, screen-space LOD, and future-surface LOD — and measures FUTURE-RELEVANT VISUAL ERROR
at equal budget. If future-surface preserves significantly more future-relevant fidelity per triangle than
distance/screen-space, the field has crossed from runtime allocation into rasterization. Until it passes, the
rasterization benefit is a hypothesis. Deterministic integer math. Stdlib only.
"""
import random

from field import _hamilton

Obj = None  # objects are plain dicts: {id, distance, coverage, future_surface, needed}


def render_priority(o):
    """future_surface × perceptual_sensitivity (screen_coverage). The corrected quantity: a node only earns
    render detail if its future surface AND its on-screen footprint are both non-trivial."""
    return o["future_surface"] * o["coverage"]


def _priorities(objs, policy):
    if policy == "distance":
        return {o["id"]: max(1, 1_000_000 // (o["distance"] + 1)) for o in objs}   # nearer -> higher
    if policy == "screen":
        return {o["id"]: o["coverage"] for o in objs}                              # bigger on screen -> higher
    if policy == "future":
        return {o["id"]: render_priority(o) for o in objs}                         # future_surface × coverage
    raise ValueError(policy)


def allocate(objs, budget, policy):
    """Apportion a fixed triangle budget across objects by the policy's priority (Hamilton, integer-exact)."""
    return _hamilton(_priorities(objs, policy), budget)


def future_relevant_visual_error(objs, alloc):
    """Σ future_surface · visible_error, where visible_error = coverage · under-allocation. Error that is both
    ON SCREEN (coverage) and FUTURE-RELEVANT (future_surface) and STARVED (under-allocation) counts most; a
    future-relevant object with ~0 coverage contributes ~0 (its detail wouldn't be seen — the honest part)."""
    total = 0
    for o in objs:
        got = alloc.get(o["id"], 0)
        under = max(0, o["needed"] - got) * 1000 // o["needed"]                    # ‰ under-allocated
        total += o["future_surface"] * o["coverage"] * under // 1000
    return total


# ---- worlds ----------------------------------------------------------------

def flat_world(n=40, seed=1):
    """Negative control: future surface correlates with coverage and nearness. All three policies should agree."""
    rng = random.Random(seed)
    objs = []
    for i in range(n):
        d = rng.randint(1, 100)
        cov = max(2, 120 - d)                                   # near -> big on screen
        objs.append({"id": "o%d" % i, "distance": d, "coverage": cov,
                     "future_surface": cov, "needed": cov})     # future_surface == coverage (correlated)
    return objs


def hidden_importance_world(n=30, seed=2):
    """A far, moderately-sized structure with huge future surface (a collapsing bridge), buried in nearby
    high-coverage clutter with ZERO future surface (rocks/grass/fence), plus a tiny-coverage high-future switch
    (the control that should NOT get render budget)."""
    rng = random.Random(seed)
    objs = []
    for i in range(n):                                          # near clutter: big on screen, no future
        objs.append({"id": "clutter%d" % i, "distance": rng.randint(1, 8),
                     "coverage": 100, "future_surface": 0, "needed": 100})
    objs.append({"id": "bridge", "distance": 90, "coverage": 40,
                 "future_surface": 10000, "needed": 40})        # far, visible, future-critical
    objs.append({"id": "switch", "distance": 95, "coverage": 2,
                 "future_surface": 10000, "needed": 2})         # far, ~invisible, future-critical (control)
    return objs


WORLDS = {"flat": flat_world, "hidden": hidden_importance_world}
POLICIES = ("distance", "screen", "future")


def reconstruct(world_kind, budget_frac=0.10, seed=None):
    objs = WORLDS[world_kind]() if seed is None else WORLDS[world_kind](seed=seed)
    budget = max(1, int(sum(o["needed"] for o in objs) * budget_frac))
    out = {}
    allocs = {}
    for p in POLICIES:
        a = allocate(objs, budget, p)
        allocs[p] = a
        out[p] = future_relevant_visual_error(objs, a)
    return {"world": world_kind, "budget": budget, "error": out, "objs": objs, "allocs": allocs}


def run():
    return {w: reconstruct(w) for w in WORLDS}


def verdict(rows=None, tie_eps_frac=0.10):
    rows = rows or run()
    flat = rows["flat"]["error"]
    hid = rows["hidden"]["error"]
    base = max(1, min(flat.values()))
    flat_ties = (max(flat.values()) - min(flat.values())) <= tie_eps_frac * base
    future_wins = hid["future"] < hid["screen"] and hid["future"] < hid["distance"]
    ok = flat_ties and future_wins
    return ("future-surface-LOD-preserves-future-relevant-fidelity" if ok else "inconclusive"), rows


if __name__ == "__main__":
    rows = run()
    for w in ("flat", "hidden"):
        e = rows[w]["error"]
        print("%-7s budget=%d  future-relevant visual error:  distance=%d  screen=%d  future=%d"
              % (w, rows[w]["budget"], e["distance"], e["screen"], e["future"]))
    # the two corrective examples, from the hidden world's future-policy allocation
    a = rows["hidden"]["allocs"]["future"]
    need = {o["id"]: o["needed"] for o in rows["hidden"]["objs"]}
    eff = lambda k: min(a.get(k, 0), need[k])
    print("\n  Example A  switch (future_surface huge, coverage 2):  covered %d/%d triangles  (≈unchanged — 3 pixels, detail unseen)" % (eff("switch"), need["switch"]))
    print("  Example B  bridge (future_surface huge, coverage 40): covered %d/%d triangles  (funded — pixels DO depend on it)" % (eff("bridge"), need["bridge"]))
    label, _ = verdict(rows)
    print("\nVERDICT:", label)
    print("BOUND: consequence ≠ visibility ; render_priority = future_surface × perceptual_sensitivity")
    print("HONEST SCOPE: a LOD-allocation falsification bench, not a renderer — it does not draw pixels.")
