"""
consequence/reconstruct.py — the Causal Reconstruction Test (the falsification beyond the Butterfly Benchmark).

Butterfly proved position-blindness on STATIC structure. This proves the operational claim and finds its bound:

    "Can the runtime delete most computation while preserving the future-relevant outcomes?"

Two simulations of the same integer cellular world (node value = pure function of its in-neighbours, mod P,
so a node changes ONLY while its inputs change -> a settled region stops costing compute):

    FULL    : update every node every step                          -> ground truth full_final
    CAUSAL  : each step recompute the causal frontier (extractor ->  -> reconstruction caus_final
              propagation), update ONLY that frontier, freeze rest

Metrics (both in [0,1]):
    compute_saved        = 1 - Σ_t|frontier_t| / (N·|V|)            node-updates skipped
    divergence_preserved = 1 - L1(caus_final, full_final) / L1(full_final, init)

THREE worlds, including a deliberate adversary:
    flat     (negative control): dense uniform coupling -> the wave never localises -> ~0 savings (honest:
             on an unstructured world causal scheduling buys nothing)
    chained  (the win): thin dependency chains -> the wave is a moving front -> high savings, high preservation
    trigger  (the adversary): a DORMANT node that fires only when an upstream key crosses a threshold (small
             cause -> large consequence). A frontier built from observed Δstate can MISS or LATE-catch it.
             Built so the test CAN fail here; we report whatever it does, we do not spin it.

Law under test: consequence -> allocation (which nodes to simulate) is ALLOWED; consequence -> truth is
FORBIDDEN (the FULL sim is the only authority; CAUSAL is an approximation whose error we MEASURE, never hide).
Deterministic integer math, stdlib only.
"""
import random

from graph import Graph, SCALE
from extractor import extract
from propagation import frontier as causal_frontier

MOD = 1_000_003


def _in_adj(g):
    ia = {n: [] for n in g.nodes}
    for u in sorted(g.nodes, key=str):
        for v, w in g._edges(u):
            ia.setdefault(v, []).append((u, w))
    return ia


def _step(g, ia, state, update_set, bias, triggers):
    """One deterministic update of ONLY update_set; sources and frozen nodes hold. Trigger nodes fire when
    their key crosses threshold."""
    new = dict(state)
    for v in sorted(update_set, key=str):
        # trigger fires on its key crossing threshold REGARDLESS of declared in-edges -> a trigger whose key
        # is not a declared edge is a HIDDEN coupling (visible to the dynamics, invisible to the frontier).
        if v in triggers:
            key, thresh, fire = triggers[v]
            if state.get(key, 0) > thresh:
                new[v] = fire
                continue
        ins = ia.get(v, [])
        if not ins:
            continue                                   # source: holds unless externally perturbed
        acc = bias.get(v, 0)
        for u, w in ins:
            acc += (state[u] * w) >> 16
        new[v] = acc % MOD
    return new


def run_full(world, steps):
    g, init, bias, triggers = world["graph"], world["init"], world["bias"], world["triggers"]
    ia = _in_adj(g)
    allnodes = set(g.nodes)
    state = dict(init)
    for _ in range(steps):
        state = _step(g, ia, state, allnodes, bias, triggers)
    return state


def run_causal(world, steps, depth=6, decay=(9, 10), threshold=0):
    g, init, bias, triggers = world["graph"], world["init"], world["bias"], world["triggers"]
    ia = _in_adj(g)
    state = dict(init)
    changed = frozenset(world["seed_nodes"])
    mags = {n: SCALE for n in changed}
    total_updates = 0
    for _ in range(steps):
        F = causal_frontier(g, changed, mags, depth, decay, threshold)
        total_updates += len(F)
        new = _step(g, ia, state, F, bias, triggers)
        changed, mags = extract(state, new)            # PURE observe -> next frontier
        state = new
    return state, total_updates


def _l1(a, b, keys):
    return sum(abs(a.get(k, 0) - b.get(k, 0)) for k in keys)


def reconstruct(world, steps=24, depth=6, decay=(9, 10), threshold=0):
    keys = sorted(world["graph"].nodes, key=str)
    init = world["init"]
    full = run_full(world, steps)
    caus, updates = run_causal(world, steps, depth, decay, threshold)
    n = len(keys)
    compute_saved = 1.0 - updates / float(steps * n) if n else 0.0
    motion = _l1(full, init, keys)
    err = _l1(caus, full, keys)
    preserved = 1.0 - (err / motion) if motion > 0 else 1.0
    preserved = max(0.0, min(1.0, preserved))
    return {
        "world": world["name"], "nodes": n, "steps": steps,
        "compute_saved": round(compute_saved, 3),
        "divergence_preserved": round(preserved, 3),
        "full_motion": motion, "recon_err": err,
    }


# ----- worlds ---------------------------------------------------------------

def flat_world(n=120, seed=1):
    rng = random.Random(seed)
    g = Graph()
    nodes = ["n%d" % i for i in range(n)]
    for x in nodes:
        g.add_node(x)
    src = nodes[0]
    for v in nodes[1:]:                                  # dense: each node fed by many random others
        for _ in range(6):
            u = nodes[rng.randrange(n)]
            if u != v:
                g.add_edge(u, v, SCALE // 2)
    init = {x: (rng.randrange(MOD)) for x in nodes}
    init[src] = 777777                                   # perturb source
    bias = {x: rng.randrange(97) for x in nodes}
    return {"name": "flat", "graph": g, "init": init, "bias": bias,
            "triggers": {}, "seed_nodes": [src]}


def chained_world(n=120, seed=2, chains=6, length=10):
    rng = random.Random(seed)
    g = Graph()
    nodes = ["n%d" % i for i in range(n)]
    for x in nodes:
        g.add_node(x)
    src = nodes[0]
    used = 1
    for _ in range(chains):                              # thin disjoint chains hung off the source
        prev = src
        for _ in range(length):
            if used >= n:
                break
            cur = nodes[used]; used += 1
            g.add_edge(prev, cur, SCALE)
            prev = cur
    init = {x: (rng.randrange(MOD)) for x in nodes}
    init[src] = 777777
    bias = {x: 0 for x in nodes}
    return {"name": "chained", "graph": g, "init": init, "bias": bias,
            "triggers": {}, "seed_nodes": [src]}


def trigger_world(n=120, seed=3, length=10):
    """A dormant cascade: src -> key (a long thin chain), and a DORMANT node D that fires a large cascade only
    when `key` crosses a threshold. Small cause (key crossing) -> large consequence (D's subtree). The causal
    frontier reaches key via the chain, but D activates late and its subtree may be pruned -> adversary."""
    rng = random.Random(seed)
    g = Graph()
    nodes = ["n%d" % i for i in range(n)]
    for x in nodes:
        g.add_node(x)
    src = nodes[0]
    # chain src -> ... -> key
    prev = src; used = 1
    for _ in range(length):
        cur = nodes[used]; used += 1
        g.add_edge(prev, cur, SCALE)
        prev = cur
    key = prev
    D = nodes[used]; used += 1
    g.add_edge(key, D, SCALE)                            # D depends on key (so a key change can reach D)
    # D's dormant subtree (large consequence once it fires)
    sub_prev = D
    for _ in range(length):
        if used >= n:
            break
        cur = nodes[used]; used += 1
        g.add_edge(sub_prev, cur, SCALE)
        sub_prev = cur
    init = {x: rng.randrange(1000) for x in nodes}
    init[src] = 777777
    bias = {x: 0 for x in nodes}
    triggers = {D: (key, 500, 999999)}                  # if state[key] > 500 -> D := 999999 (cascade ignites)
    return {"name": "trigger", "graph": g, "init": init, "bias": bias,
            "triggers": triggers, "seed_nodes": [src]}


def hidden_trigger_world(n=120, seed=4, length=10):
    """IDENTICAL to trigger_world EXCEPT the key->D coupling is NOT declared as a graph edge — it exists only
    in the dynamics (the trigger). This is the honest bound: the causal frontier can only follow DECLARED
    dependencies, so it never reaches D, D stays frozen, and the dormant cascade is missed. The reconstruction
    is exact iff the dependency graph contains every real coupling (cf. Butterfly: integrity != graph-truth)."""
    rng = random.Random(seed)
    g = Graph()
    nodes = ["n%d" % i for i in range(n)]
    for x in nodes:
        g.add_node(x)
    src = nodes[0]
    prev = src; used = 1
    for _ in range(length):
        cur = nodes[used]; used += 1
        g.add_edge(prev, cur, SCALE)
        prev = cur
    key = prev
    D = nodes[used]; used += 1
    # NOTE: no g.add_edge(key, D) -> the coupling is UNDECLARED (hidden)
    sub_prev = D
    for _ in range(length):
        if used >= n:
            break
        cur = nodes[used]; used += 1
        g.add_edge(sub_prev, cur, SCALE)
        sub_prev = cur
    init = {x: rng.randrange(1000) for x in nodes}
    init[src] = 777777
    bias = {x: 0 for x in nodes}
    triggers = {D: (key, 500, 999999)}
    return {"name": "hidden", "graph": g, "init": init, "bias": bias,
            "triggers": triggers, "seed_nodes": [src]}


def run(steps=24):
    worlds = [flat_world(), chained_world(), trigger_world(), hidden_trigger_world()]
    rows = [reconstruct(w, steps=steps) for w in worlds]
    return rows


def verdict(rows=None, save_floor=0.5, preserve_floor=0.9):
    """Classify the reconstruction outcome. Deterministic, no spin.
        flat    -> savings ~0  : on an unstructured world causal scheduling buys nothing (negative control)
        chained -> save & keep : structure lets the runtime delete most compute and lose nothing
        trigger -> save & keep : a DECLARED dormant cascade is caught by per-step re-extraction
        hidden  -> save NOT keep: an UNDECLARED coupling is invisible -> reconstruction collapses (the BOUND)
    Returns {world: tag} and an overall string. The bound is the headline, not a footnote."""
    rows = rows or run()
    by = {r["world"]: r for r in rows}
    tag = {}
    for r in rows:
        s, p = r["compute_saved"], r["divergence_preserved"]
        if s < 0.10:
            tag[r["world"]] = "no-free-lunch"
        elif p >= preserve_floor:
            tag[r["world"]] = "save-and-preserve"
        else:
            tag[r["world"]] = "BOUND:undeclared-coupling-missed"
    ok = (tag.get("flat") == "no-free-lunch"
          and tag.get("chained") == "save-and-preserve"
          and tag.get("trigger") == "save-and-preserve"
          and tag.get("hidden", "").startswith("BOUND"))
    overall = ("reconstruction-valid-with-declared-bound" if ok else "anomaly")
    return tag, overall


if __name__ == "__main__":
    rows = run()
    for r in rows:
        print("%-8s nodes=%3d  compute_saved=%.3f  divergence_preserved=%.3f  (motion=%d err=%d)" % (
            r["world"], r["nodes"], r["compute_saved"], r["divergence_preserved"],
            r["full_motion"], r["recon_err"]))
    tag, overall = verdict(rows)
    print()
    for w in ("flat", "chained", "trigger", "hidden"):
        print("  %-8s -> %s" % (w, tag[w]))
    print("\nVERDICT:", overall)
    print("LAW: consequence -> allocation ALLOWED (which nodes to simulate); consequence -> truth FORBIDDEN")
    print("BOUND: exact reconstruction iff the dependency graph declares every real coupling (integrity != graph-truth)")
