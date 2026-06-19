"""
causal_runtime/discovery.py — the Blind Discovery Benchmark (can the runtime find what nothing declared?).

The hidden-coupling reconstruction bound said: consequence is blind to an UNDECLARED coupling. distance is
blind to anything LOW-VISIBILITY. The claim under test: the GHOST (observed − predicted) catches an anomaly
that is invisible to BOTH structural priors — because the world moved a node the model rated zero.

Setup: N nodes, each with a consequence score and a visibility. One HIDDEN node H: consequence 0 (no declared
dependency), low visibility — but at frame `t_anom` it undergoes an unusual transition (a large observed
delta) sustained for `anom_dur` frames. Each frame, a policy inspects a budget B of nodes; H is DISCOVERED the
first frame ≥ t_anom that it lands in the inspected set. Three policies at equal budget:

    distance        : inspect top-B by visibility         (today's engines)
    consequence     : inspect top-B by consequence        (structural prior)
    consequence+ghost: inspect top-B by A = surface + G⁺  (structure + surprise)

Metric: discovered? and latency (frames from t_anom). NEGATIVE CONTROL `declared`: H has normal consequence and
visibility -> all three find it instantly, ghost buys nothing. Expected on `hidden`: distance misses,
consequence misses, ghost discovers. Deterministic given seed. Stdlib only.
"""
import random

from field import SCALE
import novelty as N


def _world(n, seed, hidden):
    rng = random.Random(seed)
    consequence, visibility = {}, {}
    for i in range(n):
        c = rng.randint(50, 1000)
        consequence[i] = c
        visibility[i] = c + rng.randint(-40, 40)
    H = "H"
    if hidden:
        consequence[H] = 0                                # no declared dependency -> structurally invisible
        visibility[H] = 1                                 # nearly unseen
    else:                                                 # negative control: H is a TOP-RANKED declared node
        consequence[H] = 5000                             # clearly above the budget cut by both priors
        visibility[H] = 5000
    return consequence, visibility, H


def _topk(score, k):
    return set(sorted(score, key=lambda x: (-score[x], str(x)))[:k])


def _observed(frame, nodes, H, t_anom, anom_dur, rng):
    """Per-frame observed deltas: small baseline noise everywhere; H spikes for the anomaly window."""
    obs = {x: rng.randint(0, 20) for x in nodes}
    if t_anom <= frame < t_anom + anom_dur:
        obs[H] = 5000                                     # the unusual transition
    return obs


def discover(world_kind, n=120, seed=11, budget_frac=0.08, frames=60, t_anom=20, anom_dur=8):
    consequence, visibility, H = _world(n, seed, hidden=(world_kind == "hidden"))
    nodes = sorted(consequence, key=str)
    budget = max(1, int(len(nodes) * budget_frac))
    rng = random.Random(seed ^ 0x5DEECE66)

    static_dist = _topk(visibility, budget)               # distance & consequence sets are time-invariant
    static_cons = _topk(consequence, budget)
    found = {"distance": None, "consequence": None, "ghost": None}

    for f in range(frames):
        obs = _observed(f, nodes, H, t_anom, anom_dur, rng)
        ghost = N.ghost_field(obs, consequence)           # observed vs predicted(=consequence)
        attn = N.attention_field(consequence, ghost=ghost)
        sets = {"distance": static_dist, "consequence": static_cons, "ghost": _topk(attn, budget)}
        for pol, inspected in sets.items():
            if found[pol] is None and f >= t_anom and H in inspected:
                found[pol] = f - t_anom                    # latency in frames

    return {"world": world_kind, "n": len(nodes), "budget": budget, "t_anom": t_anom,
            "latency": found}


def run():
    return [discover("hidden"), discover("declared")]


def verdict(rows=None):
    rows = rows or run()
    by = {r["world"]: r for r in rows}
    h = by["hidden"]["latency"]
    d = by["declared"]["latency"]
    ghost_finds = h["ghost"] is not None
    priors_miss = (h["distance"] is None) and (h["consequence"] is None)
    control_all_find = all(v is not None for v in d.values())
    ok = ghost_finds and priors_miss and control_all_find
    return ("ghost-discovers-the-undeclared-anomaly" if ok else "inconclusive"), by


if __name__ == "__main__":
    rows = run()
    for r in rows:
        lat = r["latency"]
        fmt = lambda v: ("miss" if v is None else "t+%d" % v)
        print("%-9s budget=%d  distance=%-5s consequence=%-5s ghost=%-5s" % (
            r["world"], r["budget"], fmt(lat["distance"]), fmt(lat["consequence"]), fmt(lat["ghost"])))
    v, _ = verdict(rows)
    print("\nVERDICT:", v)
    print("hidden  = no declared edge + low visibility: only the ghost (observed-predicted) catches it")
    print("declared= negative control: all three find it, surprise buys nothing")
    print("LAW: ghost -> attention ALLOWED ; ghost -> truth FORBIDDEN")
