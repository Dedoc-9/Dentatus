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

FAIRNESS LAW (so a future-aware renderer never becomes a gameplay oracle):
    future_surface → fidelity allocation   ALLOWED   (smoother animation, sharper shading, more triangles)
    future_surface → hidden information     FORBIDDEN  (perceptual_sensitivity is gated by LEGAL visibility, so
                                                       an occluded enemy scores 0 no matter its future_surface)

This is a FALSIFICATION BENCH, not a renderer. It allocates a fixed TRIANGLE budget across objects by three
policies — distance LOD, screen-space LOD, and future-surface LOD — and measures FUTURE-RELEVANT VISUAL ERROR
at equal budget. If future-surface preserves significantly more future-relevant fidelity per triangle than
distance/screen-space, the field has crossed from runtime allocation into rasterization. Until it passes, the
rasterization benefit is a hypothesis. Deterministic integer math. Stdlib only.
"""
import random

from field import _hamilton

Obj = None  # objects are plain dicts: {id, distance, coverage, future_surface, needed}


def _visible_coverage(o):
    """Perceptual sensitivity = on-screen footprint that is LEGALLY VISIBLE. An occluded object (behind a wall,
    outside line-of-sight) has zero visible coverage no matter how future-critical it is — the fairness gate:
    `future_surface → hidden information` is structurally impossible because the field multiplies by it."""
    return 0 if o.get("occluded") else o["coverage"]


def render_priority(o):
    """future_surface × perceptual_sensitivity (LEGALLY-VISIBLE screen_coverage). A node earns render detail
    only if its future surface AND its legally-visible footprint are both non-trivial. An occluded node scores
    0 regardless of future_surface — the renderer may raise FIDELITY, never reveal INFORMATION."""
    return o["future_surface"] * _visible_coverage(o)


def _priorities(objs, policy):
    # every policy occlusion-culls (an unseen object gets no triangles) — fidelity allocation never reveals info
    vis = {o["id"]: (0 if o.get("occluded") else 1) for o in objs}
    if policy == "distance":
        return {o["id"]: vis[o["id"]] * max(1, 1_000_000 // (o["distance"] + 1)) for o in objs}
    if policy == "screen":
        return {o["id"]: _visible_coverage(o) for o in objs}
    if policy == "future":
        return {o["id"]: render_priority(o) for o in objs}
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


def occlusion_world(n=20, seed=3):
    """The anti-wallhack scenario: a visible bridge (future-critical, drawn) and an OCCLUDED sniper behind a
    wall (future_surface even larger, but legally unseen). A correct allocator funds the bridge and gives the
    sniper exactly ZERO — future relevance must not become hidden information."""
    rng = random.Random(seed)
    objs = [{"id": "clutter%d" % i, "distance": rng.randint(1, 8), "coverage": 100,
             "future_surface": 0, "needed": 100} for i in range(n)]
    objs.append({"id": "bridge", "distance": 60, "coverage": 40,
                 "future_surface": 10000, "needed": 40, "occluded": False})
    objs.append({"id": "sniper", "distance": 70, "coverage": 30,
                 "future_surface": 50000, "needed": 30, "occluded": True})
    return objs


def fairness_invariant(objs, alloc):
    """THE FAIRNESS LAW as a test: no object the player cannot legally see may receive render budget — no matter
    its future_surface. Returns (ok, violations). `future_surface → hidden information` FORBIDDEN."""
    violations = [o["id"] for o in objs if o.get("occluded") and alloc.get(o["id"], 0) > 0]
    return (len(violations) == 0, violations)


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
    ow = occlusion_world(); b2 = int(sum(o["needed"] for o in ow) * 0.10)
    fa = allocate(ow, b2, "future"); ok, _viol = fairness_invariant(ow, fa)
    print("FAIRNESS  occluded sniper (future_surface 50000, behind a wall): render budget = %d  (fairness_ok=%s)" % (fa.get("sniper", 0), ok))
    print("          visible bridge (future-critical, in line of sight):      render budget = %d  (funded)" % fa.get("bridge", 0))
    print("BOUND: consequence ≠ visibility ; render_priority = future_surface × perceptual_sensitivity")
    print("HONEST SCOPE: a LOD-allocation falsification bench, not a renderer — it does not draw pixels.")
