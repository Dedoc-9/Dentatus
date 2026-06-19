"""
consequence/demo_consequence.py — the State-Graph Taint Map: one field, many consumers. PYTHONHASHSEED=0.

A dependency graph (node=state, edge=dependency, downstream mass=future sensitivity) yields a single
CONSEQUENCE FIELD. The butterfly law `consequence ≠ magnitude` falls out, and rendering / AI / network /
validation all read the SAME field to answer "what matters next?".
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "salience"))
import graph as G
import field as SAL

S = G.SCALE


def main():
    g = G.Graph()
    for dep in ("quest", "economy", "ai_squad", "victory", "inventory"):
        g.add_edge("artifact", dep, int(0.9 * S)); g.add_edge(dep, "match_outcome", int(0.7 * S))
    g.add_edge("scenery", "dust", int(0.2 * S))

    print("consequence ≠ magnitude (the butterfly):")
    print("  dependency_mass: artifact(hub)=%d  scenery(leaf)=%d  (%.0fx)" % (
        G.dependency_mass(g, "artifact"), G.dependency_mass(g, "scenery"),
        G.dependency_mass(g, "artifact") / G.dependency_mass(g, "scenery")))
    print("  SAME Δ (a bullet): consequence @artifact=%d vs @scenery=%d  → %.0fx by WHERE it lands" % (
        G.consequence(g, "artifact", 1 * S), G.consequence(g, "scenery", 1 * S),
        G.consequence(g, "artifact", 1 * S) / G.consequence(g, "scenery", 1 * S)))
    print("  butterfly: Δ=1 at hub (%d) > Δ=10 at leaf (%d) — tiny cause, larger effect\n" % (
        G.consequence(g, "artifact", 1 * S), G.consequence(g, "scenery", 10 * S)))

    # ONE field, MANY consumers — every subsystem asks the SAME question of the SAME field
    mags = {"artifact": 1 * S, "scenery": 8 * S, "quest": 2 * S, "economy": 1 * S, "ai_squad": 1 * S}
    cf = G.field(g, mags)
    thr = sorted(cf.values())[len(cf) // 2]                 # median consequence
    print("one CONSEQUENCE FIELD, four consumers:")
    print("  compute   (salience):", {k: v for k, v in SAL.allocate({n: max(c, 0) for n, c in cf.items()}, 1000, 20).items() if v > 25})
    print("  validation(impact)  :", {n: ("strict" if c > thr else "game") for n, c in cf.items() if n in ("artifact", "scenery")})
    print("  network   (priority):", [n for n, _ in sorted(cf.items(), key=lambda kv: -kv[1])[:3]], "replicated first")
    print("  AI        (attention):", [n for n, _ in sorted(cf.items(), key=lambda kv: -kv[1])[:2]], "get deep thinking")
    print("\n  consequence → allocation · validation depth · network priority · AI attention   (ALLOWED)")
    print("  consequence → committed truth                                                   (FORBIDDEN)")
    print("  Honest bound: a deterministic weighting field over a DECLARED dependency graph — it decides where")
    print("  effort goes, never what is true. A general substrate (games, robotics, distributed DBs, agents,")
    print("  adaptive scientific meshes); the dependency graph itself is the modeling input, not a fact of nature.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[consequence] set PYTHONHASHSEED=0.\n\n")
        raise SystemExit(2)
    main()
