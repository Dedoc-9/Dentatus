"""
causal_runtime/demo_dini_novelty.py — dini as a NOVELTY PRODUCER for the epistemic axis, on a real Aether app.

Two claims, proven:

  (1) dini is ONE producer feeding the producer-agnostic novelty seam. dini_distance is a FLOAT (a captured
      observable, never bit-identical), so it crosses into the integer attention field through a deterministic
      Q16 canon boundary: novelty_q16 = clamp(round(dini_distance / D_REF · SCALE), 0, SCALE). The float never
      enters any hash; only its quantised shadow weights attention.

  (2) THE CARDINAL INVARIANT STILL HOLDS with dini + ghost attached: the AetherPulse committed-hash trajectory
      is byte-identical with and without the observers. dini tells the runtime WHERE IGNORANCE IS EXPENSIVE,
      never what is true. (`novelty/ghost → attention ALLOWED ; → mutation FORBIDDEN`.)

Run under PYTHONHASHSEED=0.
"""
import _wb
from runtime import AttentionField
from field import SCALE
import novelty as N

K = _wb.aetherpulse_kernel()
CG = _wb.consequence_graph()
DINI = _wb.dini_compass()
FP = K._fp(1)
D_REF = 6.0                                               # Poincaré-distance scale for the Q16 boundary


def _make_world():
    bodies = [
        K.body(1, (40, 70, 40), (6, 0, 4), (4, 4, 4)),
        K.body(2, (48, 66, 44), (-4, 1, 0), (4, 4, 4)),
        K.body(3, (44, 60, 41), (2, 0, -3), (4, 4, 4)),
        K.body(4, (90, 90, 90), (0, 0, 0), (4, 4, 4)),    # far loner: consequence ~0, a ghost candidate
        K.body(5, (46, 56, 42), (5, 2, 2), (4, 4, 4)),
    ]
    return K.make_world(bodies, ((0, 0, 0), (100, 100, 100)), gravity=10, dt_ms=8)


def _consequence(world):
    g = CG.Graph()
    bs = sorted(world["bodies"], key=lambda b: b["id"])
    for b in bs:
        g.add_node(b["id"])
    r2 = 22 * 22
    for a in bs:
        for c in bs:
            if a["id"] == c["id"]:
                continue
            d2 = sum(((a["pos"][k] - c["pos"][k]) // FP) ** 2 for k in range(3))
            if d2 < r2:
                g.add_edge(a["id"], c["id"], max(1, CG.SCALE * (r2 - d2) // r2))
    return {b["id"]: CG.dependency_mass(g, b["id"]) for b in bs}


def _observed(world, prev):
    if not prev:
        return {b["id"]: 0 for b in world["bodies"]}
    pm = {b["id"]: b for b in prev["bodies"]}
    out = {}
    for b in world["bodies"]:
        p = pm.get(b["id"])
        out[b["id"]] = sum(abs(b["pos"][k] - p["pos"][k]) for k in range(3)) // FP if p else 0
    return out


def _novelty_q16(dini_distance):
    """The CANON BOUNDARY: float dini_distance -> integer Q16 novelty. The float is captured-only; this shadow
    is all that touches attention. Deterministic given the float."""
    q = int(round(dini_distance / D_REF * SCALE))
    return max(0, min(SCALE, q))


def run(ticks=24):
    # (1) plain
    _, hashes_plain = K.run(_make_world(), ticks)

    # (2) observed: dini novelty (global) + ghost (per-body), never written back
    af = AttentionField(budgets={"validation": 12, "streaming": 100, "ai_tick": 100,
                                 "network": 100, "fidelity": 100})
    compass = DINI.HyperbolicMap()
    w = _make_world()
    compass.set_root({"h": K.state_hash(w), "tick": 0})
    hashes_obs = [K.state_hash(w)]
    prev = None
    novelty_trace, ghost_hits = [], set()
    prev_state = {"h": K.state_hash(w), "tick": 0}
    for t in range(ticks):
        cons = _consequence(w)
        obs = _observed(w, prev)
        ghost = N.ghost_field(obs, cons)                  # per-body surprise
        cur_state = {"h": K.state_hash(w), "tick": t + 1}
        dobs = compass.observe(prev_state, cur_state)     # dini novelty of the trajectory (FLOAT)
        u = _novelty_q16(dobs["dini_distance"])           # -> Q16 canon boundary
        novelty_trace.append(u)
        # global novelty gain feeds the uncertainty axis uniformly; ghost is per-body
        unc = {bid: u for bid in cons}
        af.observe(cons, uncertainty=unc, ghost=ghost, now=t)
        for bid, gv in ghost.items():
            if gv > 0:
                ghost_hits.add(bid)
        prev, prev_state = w, cur_state
        w = K.step(w)                                     # UNTOUCHED world advances
        hashes_obs.append(K.state_hash(w))

    return {"ticks": ticks,
            "identical_hashes": hashes_plain == hashes_obs,
            "novelty_grows": novelty_trace[-1] > novelty_trace[0],
            "novelty_head": novelty_trace[0], "novelty_tail": novelty_trace[-1],
            "ghost_flagged_bodies": sorted(ghost_hits)}


if __name__ == "__main__":
    r = run()
    print("AetherPulse + dini novelty + ghost — invariant & producer check\n")
    print("  cardinal invariant (hashes identical with dini+ghost attached):", r["identical_hashes"])
    print("  dini novelty signal Q16: head=%d -> tail=%d  (grows=%s)"
          % (r["novelty_head"], r["novelty_tail"], r["novelty_grows"]))
    print("  ghost flagged bodies (surprise > predicted):", r["ghost_flagged_bodies"])
    print("\n  => dini said WHERE IGNORANCE IS EXPENSIVE; the committed reality never changed.")
    print("     LAW:", AttentionField.law())
