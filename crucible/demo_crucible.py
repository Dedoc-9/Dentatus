"""
crucible/demo_crucible.py — the Crucible: reverse-generate hard seeds and hammer the stack with them.

  A. THE FOREST        — grow the reverse-Syracuse tree; every seed's stopping time is its reverse depth,
                         cross-checked against an independent forward replay.
  B. RATION BOUNDARY   — a hard seed just within a step budget is admitted; a deeper one is refused.
  C. TESSERA STRESS    — mint + verify a proof shard over a high-altitude climber; the rolling hash holds.
  D. MANIFEST          — a reproducible, content-addressed difficulty map of the hardest seeds.
  E. GENERATOR GATE    — if the generator cannot produce verifiable hard seeds, the crucible itself fails.

Run:  PYTHONHASHSEED=0 python3 demo_crucible.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forest as C
import oracle as O


def main():
    print("A) THE FOREST (reverse-Syracuse, no RNG — controlled chaos):")
    forest = C.generate(max_depth=25, value_ceiling=10 ** 6)
    allok = all(C.verify_seed(s)[0] for s in forest)
    hard = C.select(forest, within_budget=25, by="altitude")
    print("   %d seeds, all cross-checked against forward replay: %s" % (len(forest), allok))
    print("   hardest by altitude: n=%d  stopping_time=%d  peak=%d  altitude=%dx (climbs above its seed)\n"
          % (hard["n"], hard["stopping_time"], hard["peak"], hard["altitude"]))

    print("B) RATION BOUNDARY ATTACK (budget K=30 logical steps):")
    r = O.inject_ration(30)
    print("   inside K: n=%-6d S=%-2d  admitted=%s" % (r["inside"]["n"], r["inside"]["stopping_time"], r["inside"]["admitted"]))
    print("   over   K: n=%-6d S=%-2d  admitted=%s   <- refused, identical on any machine\n"
          % (r["over"]["n"], r["over"]["stopping_time"], r["over"]["admitted"]))

    print("C) TESSERA STRESS (mint a proof shard over a high-altitude climber, replay it):")
    t = O.inject_tessera(hard["n"])
    print("   seed=%d -> %d steps -> path_hash=%s -> verified=%s (%s)\n"
          % (t["seed"], t["steps"], t["path_hash"][:16], t["verified"], t["detail"]))

    print("D) MANIFEST (content-addressed difficulty map):")
    m = O.build_manifest(max_depth=25, value_ceiling=10 ** 6, top=5)
    for s in m["seeds"]:
        print("   n=%-7d S=%-2d altitude=%-3dx forward_verified=%s" % (s["n"], s["stopping_time"], s["altitude"], s["verified_forward"]))
    print("   manifest_hash=%s   reproducible=%s\n"
          % (m["manifest_hash"][:16], O.build_manifest(25, 10 ** 6, top=5)["manifest_hash"] == m["manifest_hash"]))

    print("E) GENERATOR GATE — the crucible must be able to forge a verifiable hard seed, or the build fails:")
    sj = C.seed_just_under(20, value_ceiling=10 ** 6)
    ok = sj is not None and C.verify_seed(sj)[0] and sj["altitude"] > 1
    print("   forged n=%d (altitude %dx), verifies forward + is non-trivial: %s" % (sj["n"], sj["altitude"], ok))
    print("\n   It maps the difficulty landscape; it does not solve Collatz. integrity != truth.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[crucible] set PYTHONHASHSEED=0 (the manifest + shard hashes must match across machines).\n\n")
        raise SystemExit(2)
    main()
