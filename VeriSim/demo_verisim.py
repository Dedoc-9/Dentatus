"""
VeriSim/demo_verisim.py — verifiable simulation, end to end. "We prove the test was real, not the future."

  A. RUN + SHARD       — run a toy braking scenario in fixed point; emit a content-addressed Shard.
  B. REPLAY COURT      — a stranger re-runs the Shard locally and confirms it bit-for-bit.
  C. TAMPER / DRIFT    — a forged final state fails; an observable-only difference is WARN, a gated one FAIL.
  D. SPOT-CHECK        — prove a single simulation step is in the run via an O(log n) Merkle proof.
  E. BOUNDED           — a runaway scenario halts at the fuel budget; nothing hangs.

Run:  PYTHONHASHSEED=0 python3 demo_verisim.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chronicle"))
import scenarios as SC
import runner as R
import court as C
from _cores import SCALE
from signing import Ed25519Signer, ed25519_available


def main():
    signer = Ed25519Signer() if ed25519_available() else None

    print("A) RUN + SHARD (toy 1-D braking: 30 m/s, 8 m/s^2 decel, 10 ms steps):")
    seed = SC.brake_seed(v0_mps=30, a_mps2=8, dt_ms=10)
    shard = R.run_simulation("brake_1d", seed, input_data={"model": "toy_brake_v1", "v0": 30}, signer=signer)
    print("   shard: %d steps -> stop at %.2f m   merkle_root=%s   signed=%s\n"
          % (shard["steps"], shard["final_state"]["p"] / SCALE, shard["merkle_root"][:16], shard["tessera"]["signature"] is not None))

    print("B) REPLAY COURT (a stranger re-runs it; trusts no producer):")
    v = C.replay(shard)
    print("   verified=%s  (%s)\n" % (v["verified"], v["detail"]))

    print("C) TAMPER / DRIFT (gate vs observable):")
    forged = dict(shard, final_state=dict(shard["final_state"], p=shard["final_state"]["p"] + SCALE))
    print("   forged stopping distance -> replay verified:", C.replay(forged)["verified"])
    gate = ["p", "v", "halted"]
    print("   only step-count (t) differs -> %s (benign observable drift)"
          % C.classify_final(shard, dict(shard["final_state"], t=shard["final_state"]["t"] + 7), gate)["verdict"])
    print("   stopping distance (p) differs -> %s (a real logic change)\n"
          % C.classify_final(shard, dict(shard["final_state"], p=shard["final_state"]["p"] + SCALE), gate)["verdict"])

    print("D) SPOT-CHECK (prove one step is in the run, O(log n), no full replay):")
    ok, leaf = C.spot_check_step(shard, 100)
    print("   step 100 inclusion proof verifies:", ok, "(%s...)\n" % leaf[:12])

    print("E) BOUNDED (a runaway is halted by the fuel budget, never hangs):")
    runaway = SC.projectile_seed(v0_mps=1000000, g_mps2=0, dt_ms=10, max_steps=500)   # never lands; budget=500
    rshard = R.run_simulation("projectile_1d", runaway, fuel_budget=500)
    print("   ran %d steps then halted at the budget (no infinite loop)\n" % rshard["steps"])

    print("   A Shard proves the SIMULATION was real and replayable —")
    print("   never that the model matches reality or that any real-world system is safe. integrity != truth.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[VeriSim] set PYTHONHASHSEED=0 (shard hashes must match across machines).\n\n")
        raise SystemExit(2)
    main()
