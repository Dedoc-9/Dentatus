"""
consequence/propagation.py — walk the dependency graph from a changed set to its downstream affected region.

Operator: changed-set -> reached-flow map. Given the nodes a transition actually changed (from extractor),
propagate magnitude downstream along dependency edges (u->v weighted), accumulating per-node reached flow with
per-hop decay so cycles converge. The CAUSAL FRONTIER of a transition is then:

    frontier = changed ∪ {v : reached[v] > threshold}

i.e. exactly the region whose future the change can still bend. Everything else is provably-irrelevant to THIS
transition and can be frozen (allocation decision only; never a truth decision). Mirrors graph.taint but is
keyed for the runtime loop: it returns the reached map AND the frontier set in one pass. Deterministic integer
math, sorted iteration. Stdlib only.
"""
from graph import SCALE


def reached(graph, magnitudes, depth=6, decay=(9, 10)):
    """Downstream accumulated flow from the changed sources `magnitudes` = {node: magnitude}.
    Returns {node: reached_flow} over nodes with strictly-positive inflow (sources not included unless they
    are also downstream of another source). Exact integer; bounded by `depth`; per-hop decay dn/dd<1."""
    dn, dd = decay
    acc = {}
    # per-LAYER merge by node: aggregate inflow before propagating. By linearity the accumulated totals match
    # the path-sum walk, but work is bounded by depth*|V|*deg instead of exploding multiplicatively on dense
    # graphs. (graph.dependency_mass/taint keep the path-sum form; only this runtime walk is merged.)
    frontier = {n: int(m) for n, m in magnitudes.items()}
    for _ in range(depth):
        nxt = {}
        for u in sorted(frontier.keys(), key=str):
            flow = frontier[u]
            for v, w in graph._edges(u):
                contrib = (flow * w // SCALE) * dn // dd
                if contrib <= 0:
                    continue
                acc[v] = acc.get(v, 0) + contrib
                nxt[v] = nxt.get(v, 0) + contrib
        if not nxt:
            break
        frontier = nxt
    return acc


def frontier(graph, changed, magnitudes, depth=6, decay=(9, 10), threshold=0):
    """The causal frontier = changed sources ∪ downstream nodes whose reached flow exceeds `threshold`.
    This is the set the runtime should actually simulate/validate this step; the complement is frozen.
    Returns a sorted-by-str frozenset. Deterministic."""
    r = reached(graph, {n: magnitudes.get(n, 0) for n in changed}, depth, decay)
    region = set(changed)
    for v, f in r.items():
        if f > threshold:
            region.add(v)
    return frozenset(region)


def region_size(graph, changed, magnitudes, depth=6, decay=(9, 10), threshold=0):
    """|frontier| — the count of nodes a transition can still affect. Used as reachable_dependents in the
    fingerprint and as the compute-cost numerator in the reconstruction test."""
    return len(frontier(graph, changed, magnitudes, depth, decay, threshold))
