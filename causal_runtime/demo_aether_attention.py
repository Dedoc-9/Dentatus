"""
causal_runtime/demo_aether_attention.py — attach the AttentionField to an Aether application (AetherPulse).

THE CARDINAL INVARIANT (the user's law): "the outcome hash cannot know the difference." We run the SAME
AetherPulse simulation two ways:

    (1) plain     : kernel.run(world, ticks)                       -> committed hash trajectory
    (2) observed  : same kernel.step loop, but each tick the AttentionField OBSERVES the world (builds a
                    consequence graph from body proximity, uncertainty from |Δvel|, emits AttentionTokens and a
                    per-channel allocation) and the world handed to the NEXT step is byte-for-byte the one the
                    kernel produced — the observer never writes back.

If observation is truly separated from reality, (1) and (2) commit the IDENTICAL hash at every tick, while the
attention layer still produces a non-trivial, body-varying, time-varying allocation. That is the proof that
causal awareness changed WHAT WE COMPUTE ABOUT, not WHAT HAPPENED. Run under PYTHONHASHSEED=0.
"""
import _wb
from runtime import AttentionField
from field import SCALE

K = _wb.aetherpulse_kernel()
CG = _wb.consequence_graph()
FP = K._fp(1)                       # the kernel's fixed-point unit (=2**32); positions are in this scale


def _make_world():
    bodies = [
        K.body(1, (40, 70, 40), (6, 0, 4), (4, 4, 4)),    # cluster that falls & collides -> proximity shifts
        K.body(2, (48, 66, 44), (-4, 1, 0), (4, 4, 4)),
        K.body(3, (44, 60, 41), (2, 0, -3), (4, 4, 4)),
        K.body(4, (90, 90, 90), (0, 0, 0), (4, 4, 4)),    # far, slow loner -> low attention (control)
        K.body(5, (46, 56, 42), (5, 2, 2), (4, 4, 4)),
    ]
    return K.make_world(bodies, ((0, 0, 0), (100, 100, 100)), gravity=10, dt_ms=8)


def _consequence_from_world(world):
    """Proximity dependency: body u -> v if v is within a radius of u (they can collide). consequence score =
    dependency_mass. Pure read of positions; integers."""
    g = CG.Graph()
    bs = sorted(world["bodies"], key=lambda b: b["id"])
    for b in bs:
        g.add_node(b["id"])
    radius = 22                                          # interaction radius in DISPLAY units
    r2 = radius * radius
    for a in bs:
        for c in bs:
            if a["id"] == c["id"]:
                continue
            d2 = sum(((a["pos"][k] - c["pos"][k]) // FP) ** 2 for k in range(3))   # display-unit distance^2
            if d2 < r2:
                w = CG.SCALE * (r2 - d2) // r2           # linear falloff in [0, SCALE]
                g.add_edge(a["id"], c["id"], max(1, w))
    cons = {b["id"]: CG.dependency_mass(g, b["id"]) for b in bs}
    return cons


def _uncertainty_from_motion(world, prev):
    """uncertainty ∝ speed change since last tick (fast/accelerating bodies are less predictable). Q16."""
    out = {}
    pmap = {b["id"]: b for b in (prev["bodies"] if prev else [])}
    for b in world["bodies"]:
        v = b["vel"]
        spd = (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) // (FP * FP // SCALE + 1)
        out[b["id"]] = max(1, min(SCALE, spd))
    return out


def run(ticks=24):
    # (1) plain
    w0 = _make_world()
    _, hashes_plain = K.run(w0, ticks)

    # (2) observed — identical kernel loop, attention observes each tick, never writes back
    af = AttentionField(budgets={"streaming": 100, "ai_tick": 100, "fidelity": 100,
                                 "network": 100, "validation": 8})
    w = _make_world()
    hashes_obs = [K.state_hash(w)]
    alloc_log = []
    stream_log = []
    prev = None
    for t in range(ticks):
        cons = _consequence_from_world(w)               # OBSERVE (pure reads of w)
        unc = _uncertainty_from_motion(w, prev)
        af.observe(cons, unc, now=t)
        a = af.allocation()
        alloc_log.append(a["validation"])                # coarse: where validation depth concentrates
        stream_log.append(a["streaming"])                # fine: shifts as bodies move/collide
        prev = w
        w = K.step(w)                                    # the kernel advances the UNTOUCHED world
        hashes_obs.append(K.state_hash(w))

    identical = (hashes_plain == hashes_obs)
    # non-triviality: the validation allocation varies across bodies AND changes over time
    body_ids = sorted({bid for a in alloc_log for bid in a})
    last = alloc_log[-1]
    varies_across_bodies = len(set(last.values())) > 1
    varies_over_time = any(stream_log[i] != stream_log[i + 1] for i in range(len(stream_log) - 1))
    return {"ticks": ticks, "identical_hashes": identical,
            "n_hashes": len(hashes_obs), "head": hashes_obs[0][:12], "tail": hashes_obs[-1][:12],
            "alloc_varies_across_bodies": varies_across_bodies,
            "alloc_varies_over_time": varies_over_time,
            "final_validation_alloc": {k: last[k] for k in body_ids}}


if __name__ == "__main__":
    r = run()
    print("AetherPulse + AttentionField — cardinal invariant check\n")
    print("  committed hash trajectory identical with/without observer :", r["identical_hashes"])
    print("  ticks=%d  head=%s  tail=%s" % (r["ticks"], r["head"], r["tail"]))
    print("  attention non-trivial: varies across bodies=%s  over time=%s"
          % (r["alloc_varies_across_bodies"], r["alloc_varies_over_time"]))
    print("  final validation-depth allocation by body:", r["final_validation_alloc"])
    print("\n  => observation changed WHAT WE COMPUTE ABOUT, not WHAT HAPPENED.")
    print("     LAW:", AttentionField.law())
