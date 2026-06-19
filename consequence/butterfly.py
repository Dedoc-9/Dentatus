"""
consequence/butterfly.py — the Butterfly Benchmark: when does consequence-aware scheduling matter?

Two worlds, identical in everything a conventional engine sees — same node count, same "physics cost" — but
different CONSEQUENCE TOPOLOGY:

    FLAT     N nodes, uniform dependency (no structure to find)
    CHAINED  N nodes + ONE hidden dependency chain/hub at POSITIONALLY-RANDOM nodes

Three schedulers rank nodes for an attention budget: `distance` and `visibility` (position-based, the
industry baselines) and `consequence` (dependency-mass, reads the graph). The metric is **future-divergence
captured** = the share of total consequence the top-budget nodes hold (a uniform perturbation hits every node,
so this isolates `consequence ≠ magnitude`).

Honest, decision-useful verdict: consequence-aware scheduling ADDS VALUE only when consequence topology is
DECORRELATED from position (CHAINED) — there, position-based schedulers are *structurally blind* to the
hidden chain. On a FLAT world it ties the baselines at the budget fraction (a fair negative control). It does
NOT prove the graph is "true" — the dependency graph is a declared modeling input. Deterministic. Stdlib only.
"""
import random
import graph as G

S = G.SCALE


def flat_world(n, seed):
    """N nodes, UNIFORM dependency — every node equally (in)consequential. The negative control."""
    rng = random.Random(seed)
    g = G.Graph()
    for i in range(n):
        g.add_edge(i, ("sink", i), int(0.5 * S))     # one private dependent, identical weight for all
    pos = {i: (rng.random(), rng.random()) for i in range(n)}
    return g, pos, set()


def chained_world(n, seed, chain_len=8, fanout=6):
    """FLAT plus one hidden dependency chain + hub at positionally-random nodes."""
    g, pos, _ = flat_world(n, seed)
    rng = random.Random(seed + 1)
    chain = rng.sample(range(n), chain_len)
    for a, b in zip(chain, chain[1:]):
        for _ in range(3):
            g.add_edge(a, b, int(0.9 * S))
    for d in rng.sample(range(n), fanout):
        g.add_edge(chain[0], d, int(0.85 * S))       # the head is a hub
    return g, pos, set(chain)


def schedulers(g, pos, n, seed):
    rng = random.Random(seed + 2)
    dist = {i: 1.0 / (1 + abs(pos[i][0] - 0.5) + abs(pos[i][1] - 0.5)) for i in range(n)}
    vis = {i: rng.random() * dist[i] for i in range(n)}
    cons = {i: G.dependency_mass(g, i) for i in range(n)}
    return {"distance": dist, "visibility": vis, "consequence": cons}


def true_consequence(g, n):
    """Ground-truth future divergence under a uniform perturbation (same Δ everywhere)."""
    return {i: G.consequence(g, i, 1 * S) for i in range(n)}


def capture(rank_scores, true_cons, budget_frac=0.1):
    n = len(true_cons)
    k = max(1, int(n * budget_frac))
    top = sorted(range(n), key=lambda i: rank_scores[i], reverse=True)[:k]
    tot = sum(true_cons.values())
    return (sum(true_cons[i] for i in top) / tot) if tot else budget_frac   # uniform ⇒ exactly budget_frac


def run(n=200, seed=3, budget_frac=0.1):
    """Run both worlds; return {world: {scheduler: capture}} + verdict."""
    out = {}
    for name, build in (("flat", flat_world), ("chained", chained_world)):
        g, pos, _ = build(n, seed)
        t = true_consequence(g, n)
        sch = schedulers(g, pos, n, seed)
        out[name] = {s: capture(sch[s], t, budget_frac) for s in sch}
    flat_spread = max(out["flat"].values()) - min(out["flat"].values())
    cw = out["chained"]
    verdict = ("consequence-wins-on-structure"
               if (cw["consequence"] > 1.5 * cw["distance"] and cw["consequence"] > 1.5 * cw["visibility"]
                   and flat_spread < 0.05)        # and ties (within 5%) on the flat negative control
               else "inconclusive")
    out["verdict"] = verdict
    out["budget_frac"] = budget_frac
    return out
