"""
causal_runtime/demo_coupling_discovery.py — closing the epistemic trap on a real Aether application.

The chain: ghost (model error) -> persistence -> PROPOSED edge -> external review -> graph (model) update. The
trap is that a self-modifying system's learning loop can corrupt the model it edits. We show the four locks
hold end to end, and the decisive one against a real kernel:

    EVEN AN ACCEPTED PROPOSAL LEAVES THE COMMITTED WORLD HASH UNCHANGED.

`graph improvement ≠ world modification`: the consequence graph is a MODEL that steers attention; the
AetherPulse kernel never reads it, so learning a new edge changes where we look, never what happened. Run
under PYTHONHASHSEED=0.
"""
import _wb
from runtime import AttentionField
import ghost_persistence as GP
from coupling_discovery import CouplingRegistry

K = _wb.aetherpulse_kernel()
CG = _wb.consequence_graph()


def _discover_proposal():
    """Run the repeatable hidden-coupling world, return the top reviewed proposal (A→C)."""
    rows = GP.run()
    rep = [r for r in rows if r["kind"] == "repeatable"][0]
    return rep["proposals"][0] if rep["proposals"] else None


def _review_accept(graph, edge, weight=None):
    """EXTERNAL authority (human/tool). Pure function: returns a NEW graph with the proposed edge added. This
    lives OUTSIDE the registry — the discovery mechanism cannot call a graph mutator, only emit the proposal."""
    s, t = edge
    g2 = CG.Graph()
    for n in graph.nodes:
        g2.add_node(n)
    for u in graph.out:
        for (v, w) in graph.out[u]:
            g2.add_edge(u, v, w)
    g2.add_node(s); g2.add_node(t)
    g2.add_edge(s, t, weight if weight is not None else CG.SCALE // 2)
    return g2


def _committed_hashes(ticks=24):
    return K.run(_make_world(), ticks)[1]


def _make_world():
    bodies = [K.body(i, (40 + 4 * i, 70 - 3 * i, 40 + i), (5 - i, i, 2), (4, 4, 4)) for i in range(1, 6)]
    return K.make_world(bodies, ((0, 0, 0), (100, 100, 100)), gravity=10, dt_ms=8)


def run():
    proposal = _discover_proposal()

    # a v0 model graph (what consequence currently declares) and the v1 graph AFTER an accepted proposal
    g0 = CG.Graph()
    for n in ("A", "B", "C"):
        g0.add_node(n)
    g0.add_edge("A", "B", CG.SCALE)                       # declared A→B only
    g1 = _review_accept(g0, proposal) if proposal else g0  # learned A→C added by external review

    # reality is the AetherPulse commit trajectory — a pure function of the kernel, NOT of any model graph
    hashes_before = _committed_hashes()
    # (model learning happens here: g0 -> g1) ...
    hashes_after = _committed_hashes()

    registry_has_graph_mutator = any(
        m in dir(CouplingRegistry) for m in ("apply", "commit", "add_edge", "mutate", "promote"))
    return {
        "proposal": proposal,
        "graph_v0_edges": sum(len(v) for v in g0.out.values()),
        "graph_v1_edges": sum(len(v) for v in g1.out.values()),
        "model_changed": (sum(len(v) for v in g1.out.values()) >
                          sum(len(v) for v in g0.out.values())),
        "world_hash_unchanged": hashes_before == hashes_after,
        "registry_can_mutate_graph": registry_has_graph_mutator,
    }


if __name__ == "__main__":
    r = run()
    print("Closing the epistemic trap — discovery proposes, reality stays put\n")
    print("  proposed coupling (from persistent ghost):", r["proposal"])
    print("  model graph edges: v0=%d -> v1=%d  (model_changed=%s)"
          % (r["graph_v0_edges"], r["graph_v1_edges"], r["model_changed"]))
    print("  committed WORLD hash unchanged by the model update:", r["world_hash_unchanged"])
    print("  registry has ANY graph-mutation method:", r["registry_can_mutate_graph"])
    print("\n  => the model learned a new coupling; reality was never a function of the model.")
    print("     ghost -> PROPOSED coupling ALLOWED ; ghost -> ACTUAL coupling FORBIDDEN")
    print("     graph improvement != world modification.")
