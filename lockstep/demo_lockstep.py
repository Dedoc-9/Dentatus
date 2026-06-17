"""
lockstep/demo_lockstep.py — decoupled truth-rate vs frame-rate, and revert-to-last-valid-hash rollback.

  A. TRUTH TICKS        — a 120 Hz integer simulation; every tick content-addressed (no float in the hash).
  B. RENDER OBSERVABLES — 240 fps drawn over it: 2 frames/tick, integer-exact interpolation, never gated.
  C. ROLLBACK           — a client mispredicts a remote input; reverts to the last valid hashed state and
                          re-simulates; an independent peer converges to the identical tick hashes.

Run:  PYTHONHASHSEED=0 python3 demo_lockstep.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tick import TruthTrack, kinematic_step
import interp as I
import rollback as RB

TRUTH_HZ, RENDER_HZ = 120, 240
U = 1_000_000                                                # one display unit in fixed-point micro-units


def u(x):
    return "%.3f" % (x / U)


def main():
    print("Truth rate %d Hz, render rate %d fps  ->  %.0f frames per truth tick\n"
          % (TRUTH_HZ, RENDER_HZ, I.frames_per_tick(TRUTH_HZ, RENDER_HZ)))

    print("A) TRUTH TICKS (integer sim, content-addressed; render positions are NOT in these hashes):")
    track = TruthTrack({"p": 0, "v": U}, kinematic_step)     # 1 unit/tick
    for n in range(4):
        track.advance({"a": 0})
    for n in range(track.tick + 1):
        print("   tick %d  p=%s  H=%s" % (n, u(track.states[n]["p"]), track.hashes[n][:12]))

    print("\nB) RENDER OBSERVABLES (240 fps): frames fall between ticks; integer-exact interpolation:")
    for f in range(0, 7):
        fr = I.render_frame(track, f, TRUTH_HZ, RENDER_HZ, ["p"])
        print("   frame %d  ->  tick %d + %d/%d   shown p=%s   (observable, never gated)"
              % (f, fr["tick"], fr["alpha_num"], fr["alpha_den"], u(fr["pos"]["p"])))
    print("   the tick boundary is a chosen discretization; sub-tick positions have no truth-status.")

    print("\nC) ROLLBACK (revert to the last valid hashed state, then re-simulate):")
    G = {"p": 0, "v": U}
    predicted = TruthTrack(G, kinematic_step)                # client predicts remote a=0 throughout
    for n in range(6):
        predicted.advance({"a": 0})
    print("   client predicted to tick %d, final p=%s" % (predicted.tick, u(predicted.states[-1]["p"])))
    authoritative = [{"a": 0}, {"a": 0}, {"a": 0}, {"a": U // 2}, {"a": 0}]   # remote really accelerated at tick 3
    res = RB.reconcile(predicted, authoritative, kinematic_step)
    print("   authority differs at tick 3  ->  last_valid_tick=%d  rollback_depth=%d  changed=%s"
          % (res["last_valid_tick"], res["rollback_depth"], res["changed"]))
    print("   corrected final p=%s" % u(res["corrected"].states[-1]["p"]))
    peer = TruthTrack.from_inputs(G, kinematic_step, authoritative + [{"a": 0}])
    print("   independent peer with the same authoritative inputs converges: %s"
          % (peer.hashes[-1] == res["corrected"].hashes[-1]))
    print("\n   Truth is the tick hash; the frames between were prediction (observable), corrected at bounded cost.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[lockstep] set PYTHONHASHSEED=0 (the truth track must hash identically across processes).\n\n")
        raise SystemExit(2)
    main()
