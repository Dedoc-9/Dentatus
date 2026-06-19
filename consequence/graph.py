"""
consequence/graph.py — the State-Graph Taint Map: the shared field all subsystems consume.

A general-purpose deterministic primitive for **consequence-aware** runtimes. The world is a dependency
graph — node = an entity / state element, directed edge u→v with a weight = how strongly v depends on u.
A node's **future sensitivity** is its downstream weighted reachability (how much future hinges on it). The
**consequence** of perturbing a node is then NOT its magnitude but:

    consequence(node, Δ) = Δ · dependency_mass(node)              # the new law: consequence ≠ magnitude
                         ≈ physical_delta · state_dependency · future_branching

so a *tiny* delta at a high-dependency hub outweighs a *huge* delta at a leaf (the butterfly). One field, many
consumers — the same per-node consequence answers every subsystem's "what matters next?":

    rendering → where to spend pixels      AI → where to think        network → what to replicate
    physics   → where to validate (depth)  streaming → what's resident

This is OBSERVABILITY: it weights attention/verification/resources, it never changes committed state
(`consequence → allocation/validation depth`, never `consequence → truth`). Deterministic integer math
(weights as Q16 fractions, integer decay per hop, sorted edge iteration). Stdlib only.
"""
SCALE_BITS = 16
SCALE = 1 << SCALE_BITS                       # weights/flows are Q16


class Graph:
    def __init__(self):
        self.nodes = set()
        self.out = {}                          # node -> list[(target, weight_q16)]

    def add_node(self, n):
        self.nodes.add(n)
        self.out.setdefault(n, [])
        return self

    def add_edge(self, u, v, weight):
        """Directed dependency u→v with weight ∈ [0, SCALE] (how strongly v depends on u)."""
        self.add_node(u); self.add_node(v)
        self.out[u].append((v, int(weight)))
        return self

    def _edges(self, u):
        return sorted(self.out.get(u, []), key=lambda e: (str(e[0]), e[1]))  # deterministic, any node type


def dependency_mass(graph, node, depth=6, decay=(9, 10)):
    """Downstream weighted reachable mass from `node` — its future sensitivity. Bounded BFS with per-hop
    decay (so cycles converge and the walk terminates). Exact integer."""
    dn, dd = decay
    total = 0
    frontier = [(node, SCALE)]                 # start with a unit flow
    for _ in range(depth):
        nxt = []
        for u, flow in frontier:
            for v, w in graph._edges(u):
                contrib = (flow * w // SCALE) * dn // dd
                if contrib <= 0:
                    continue
                total += contrib
                nxt.append((v, contrib))
        if not nxt:
            break
        frontier = nxt
    return total


def consequence(graph, node, magnitude, depth=6, decay=(9, 10)):
    """The butterfly-aware consequence of a perturbation of size `magnitude` at `node`:
    magnitude scaled by how much future depends on the node. consequence ≠ magnitude."""
    return magnitude * dependency_mass(graph, node, depth, decay) // SCALE


def field(graph, magnitudes, depth=6, decay=(9, 10)):
    """The shared CONSEQUENCE FIELD: {node: consequence} given per-node injected magnitudes. This single
    map is what compute (salience), validation depth (impact), network priority, and AI attention all read."""
    return {n: consequence(graph, n, magnitudes.get(n, 0), depth, decay) for n in sorted(graph.nodes, key=str)}


def taint(graph, source_magnitudes, depth=6, decay=(9, 10)):
    """Propagate perturbation magnitudes from sources downstream, accumulating per-node taint — the spread of
    influence through the dependency graph. {node: accumulated_taint}. Deterministic."""
    dn, dd = decay
    acc = {n: 0 for n in graph.nodes}
    frontier = [(n, int(m)) for n, m in sorted(source_magnitudes.items(), key=lambda kv: str(kv[0]))]
    for _ in range(depth):
        nxt = []
        for u, flow in frontier:
            for v, w in graph._edges(u):
                contrib = (flow * w // SCALE) * dn // dd
                if contrib <= 0:
                    continue
                acc[v] = acc.get(v, 0) + contrib
                nxt.append((v, contrib))
        if not nxt:
            break
        frontier = nxt
    return acc
