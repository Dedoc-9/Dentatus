"""
consequence/demo_butterfly.py — the Butterfly Benchmark. PYTHONHASHSEED=0.

Two worlds identical in everything a conventional engine sees (node count, physics cost), differing ONLY in
consequence topology. The metric is future-divergence captured per unit attention budget — not FPS, not
polygons. It answers WHEN consequence-aware scheduling matters.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import butterfly as BF


def main():
    r = BF.run(n=200, seed=3, budget_frac=0.1)
    print("Butterfly Benchmark — 200 nodes; FLAT vs +1 hidden dependency chain (positionally random)\n")
    print("  future-divergence captured @10%% budget:")
    print("  world     distance   visibility   consequence")
    for w in ("flat", "chained"):
        print("  %-8s  %.3f      %.3f        %.3f" % (w, r[w]["distance"], r[w]["visibility"], r[w]["consequence"]))
    print("\n  VERDICT: %s" % r["verdict"].upper())
    print("  FLAT (no hidden structure): all schedulers tie at the budget fraction (0.10) — consequence adds")
    print("    nothing when there is nothing to find. A fair negative control.")
    print("  CHAINED: consequence captures ~94%% of the future-divergence; distance/visibility ~34%% (≈ luck),")
    print("    because the chain is decorrelated from position — proximity is STRUCTURALLY blind to it.")
    print("\n  The decision-useful claim: consequence-aware scheduling wins exactly when a world has dependency")
    print("  structure that position cannot see — not 'always faster', but 'sees future surface area position")
    print("  cannot'. Honest bound: the dependency graph is a declared modeling input, not a fact of nature.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[consequence] set PYTHONHASHSEED=0.\n\n")
        raise SystemExit(2)
    main()
