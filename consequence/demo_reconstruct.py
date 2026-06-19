"""
consequence/demo_reconstruct.py — make the consequence field operationally native, then try to break it.

Pipeline shown: POST STATE -> extractor(Δ) -> propagation(frontier) -> fingerprint(token) -> cache(budget).
Then the Causal Reconstruction Test: simulate only the causal frontier vs the full world, measure
compute_saved and divergence_preserved across flat / chained / declared-trigger / hidden-trigger worlds.

The headline is the BOUND, not the win: causal reconstruction is exact iff the dependency graph declares every
real coupling. Run under PYTHONHASHSEED=0.
"""
import graph as G
import extractor as EX
import propagation as PR
import fingerprint as FP
import cache as CA
import reconstruct as RC


def _native_pipeline_demo():
    print("== operational pipeline: POST STATE -> extract -> propagate -> fingerprint -> cache ==")
    g = G.Graph()
    for u, v in [("door_17", "quest_3"), ("quest_3", "faction_A"), ("faction_A", "ending_2")]:
        g.add_edge(u, v, G.SCALE)
    g.add_edge("wall_88", "dust_9", G.SCALE // 3)            # a wall: shallow downstream
    pre = {"door_17": 0, "wall_88": 0, "quest_3": 0, "faction_A": 0, "ending_2": 0, "dust_9": 0}
    post = dict(pre, door_17=1, wall_88=1)                   # same physical delta (1) at door and wall
    changed, mags = EX.extract(pre, post)
    print("  changed:", sorted(changed), " magnitudes:", {k: mags[k] for k in sorted(mags)})
    cache = CA.ConsequenceCache(capacity=16)
    for n in sorted(changed):
        rd = PR.region_size(g, frozenset([n]), {n: G.SCALE})   # structural reachability (unit probe)
        tok = FP.fingerprint(g, n, mags[n], reachable_dependents=rd, now=0, ttl=240)
        cache.put(tok)
        print("  fingerprint %-8s impact=%d reachable=%d score=%d h=%s"
              % (n, tok.impact, tok.reachable_dependents, tok.score, tok.h[:10]))
    print("  budget=1 frontier (where to spend):", cache.frontier(1),
          "  <- same magnitude, door wins on consequence (butterfly)\n")


def _reconstruction_demo():
    print("== Causal Reconstruction Test (can the runtime delete compute and keep the future?) ==")
    rows = RC.run()
    for r in rows:
        print("  %-8s compute_saved=%.3f  divergence_preserved=%.3f" % (
            r["world"], r["compute_saved"], r["divergence_preserved"]))
    tag, overall = RC.verdict(rows)
    print()
    for w in ("flat", "chained", "trigger", "hidden"):
        print("  %-8s -> %s" % (w, tag[w]))
    print("\n  VERDICT:", overall)
    print("  LAW   : consequence -> allocation ALLOWED ; consequence -> truth FORBIDDEN")
    print("  BOUND : exact iff the graph declares every real coupling (integrity != graph-truth)")


if __name__ == "__main__":
    _native_pipeline_demo()
    _reconstruction_demo()
