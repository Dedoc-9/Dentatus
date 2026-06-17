"""
syracuse/demo_syracuse.py — the Collatz/Syracuse map as integrity != truth, made runnable.

  A. VERIFY A TRAJECTORY  — exact integer orbit of a seed; content-addressed; stopping time + peak.
  B. INTEGRITY != TRUTH   — verify thousands of seeds (empirical reach) while REFUSING the conjecture.
  C. RATION TIE           — a long-orbit seed exceeds an integer step budget; refused, hardware-invariant.
  D. LOCKSTEP TIE         — the same orbit as a content-addressed TruthTrack of ticks; replayable.

Run:  PYTHONHASHSEED=0 python3 demo_syracuse.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orbit as S
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ration"))
import meter as R


def main():
    print("A) VERIFY A TRAJECTORY (compressed Syracuse map, pure integer):")
    for n in (3, 27, 97):
        g = S.gates(n); ob = S.observables(S.orbit(n))
        print("   n=%-4d reached_one=%s  stopping_time=%-3d  peak=%-6d  H=%s"
              % (n, g["reached_one"], g["stopping_time"], ob["peak"], g["orbit_hash"][:12]))
    print("   orbit(3) =", S.orbit(3), "  (the orbit, not the hash, is what an auditor replays)\n")

    print("B) INTEGRITY != TRUTH — verify many seeds, refuse the conjecture:")
    w = S.ConjectureWitness()
    for n in range(1, 10000):
        w.record(S.gates(n, max_steps=2000))
    r = w.report()
    print("   verified_count=%d  max_verified_n=%d  max_stopping_time=%d"
          % (r["verified_count"], r["max_verified_n"], r["max_stopping_time"]))
    print("   conjecture_proven=%s  <-- structural refusal: more seeds raise integrity, never truth\n" % r["conjecture_proven"])

    print("C) RATION TIE — hardware-invariant integer step budget (ceiling=80 logical steps):")
    POLICY = {"ceiling": 80, "per_category": {}, "weights": {"iterations": 1}}
    for n in (27, 703):
        ok = R.within_budget(S.ration_counts(n), POLICY)
        g = S.gates(n)
        print("   n=%-4d stopping_time=%-4d within_budget=%s%s"
              % (n, g["stopping_time"], ok, "" if ok else "   -> refused (QuotaBreached-style), identical on any machine"))
    print()

    print("D) LOCKSTEP TIE — each Collatz step is a content-addressed tick:")
    t = S.as_truth_track(27)
    print("   n=27 -> %d ticks -> final n=%d  (tick hashes unique=%s)"
          % (t.tick, t.states[-1]["n"], len(set(t.hashes)) == len(t.hashes)))
    peer = S.as_truth_track(27)
    print("   re-run converges to identical final tick hash: %s" % (peer.hashes[-1] == t.hashes[-1]))
    print("\n   Truth is the tick/orbit hash you can replay; the conjecture is the ghost the workbench will not sign.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[syracuse] set PYTHONHASHSEED=0 (orbit hashes must match across processes).\n\n")
        raise SystemExit(2)
    main()
