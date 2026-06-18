"""
aether/demo_aether_physics.py — a spinning top on a hardened integer manifold.

  A. EXACT GATE        — a rational orthonormal frame (3-4-5 rotation) is EXACTLY orthonormal; no epsilon.
  B. THE 1-ULP TRUTH   — even a fixed-point Lie bracket carries a quantization residual; that is WHY we audit.
  C. SPINNING TOP      — evolve a frame 1,000,000 fixed-point steps; the Stiefel auditor self-retracts on
                         every epsilon breach, so it provably never strays off the manifold. Deterministic.
  D. GHOSTSNAP         — a collapsed frame is re-orthonormalized and the recovery is logged as a shard.

Run:  PYTHONHASHSEED=0 python3 demo_aether_physics.py
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixedpoint as F
import stiefel as S
import evolve as E


def main():
    print("A) EXACT GATE (rational frame — orthonormal with NO tolerance):")
    ok, _ = S.is_orthonormal_exact([[3, 4], [-4, 3]], 5)
    ok3, _ = S.is_orthonormal_exact([[2, 1, 2], [-2, 2, 1], [1, 2, -2]], 3)
    bad, viol = S.is_orthonormal_exact([[3, 4], [-4, 4]], 5)
    print("   3-4-5 rotation exact:", ok, "| 3x3 orthogonal exact:", ok3)
    print("   perturbed -> caught at entry (%d,%d): got %d expected %d\n" % (viol[0]["i"], viol[0]["j"], viol[0]["got"], viol[0]["expected"]))

    print("B) THE 1-ULP TRUTH (fixed-point is deterministic, NOT exact):")
    A = [[0, F.to_fp(1, 2)], [F.to_fp(-1, 2), 0]]
    B = [[0, F.to_fp(1, 3)], [F.to_fp(-1, 3), 0]]
    br = E.lie_bracket(A, B)
    defect = max(abs(br[i][j] + br[j][i]) for i in range(2) for j in range(2))
    print("   [A,B] should be 0; fixed-point gives a %d-ulp residual (skew_defect=%d)." % (max(abs(br[0][0]), abs(br[1][1])), defect))
    print("   exact-integer skew check is still perfect:", E.is_skew_symmetric([[0, 2, -3], [-2, 0, 5], [3, -5, 0]])[0])
    print("   -> this residual is exactly why aether GATES on a declared epsilon and retracts.\n")

    print("C) SPINNING TOP (1,000,000 fixed-point steps, audited):")
    gen = [[0, F.to_fp(1), 0], [F.to_fp(-1), 0, F.to_fp(1, 2)], [0, F.to_fp(-1, 2), 0]]   # skew generator
    W = F.identity(3)
    dt = F.to_fp(1, 1000)
    t0 = time.time()
    res = E.evolve_audited(W, gen, dt, steps=1_000_000, audit_every=2000)
    secs = time.time() - t0
    chk = S.check_orthogonality(res["W"])
    print("   1,000,000 steps in %.1fs: self-retractions=%d, peak energy E=%.2e" % (secs, res["retractions"], res["max_E"]))
    print("   final on-manifold: %s (E=%d <= epsilon=%d)" % (chk["ok"], chk["E"], chk["epsilon"]))
    again = E.evolve_audited(F.identity(3), gen, dt, 1_000_000, audit_every=2000)
    print("   bit-for-bit deterministic re-run:", again["final_hash"] == res["final_hash"], "\n")

    print("C2) GHOST CHANNEL (Stage B — dual residual, observable-only):")
    import fixedpoint as _F
    print("   structural Hₜ (μ⊕Z⊕S⊕W⊕pv):", res["structural_hash"][:16], " protocol:", res["protocol_version"])
    print("   legacy Hₜ (W-only, byte-identical to Stage A):", res["final_hash"][:16])
    print("   ghost samples=%d  B(t)=‖S‖/(‖Z‖+ε)=%.3e  η_CLT=%d  (sensors, never gates)"
          % (res["ghost_samples"], res["B_t"] / _F.SCALE, res["eta_clt"]["eta"]))


    print("D) GHOSTSNAP (collapse -> verified recovery):")
    drifted = E.evolve_raw(F.identity(3), gen, dt, 5000)                                  # no audit -> let it drift
    before = S.frobenius_energy(drifted)
    rec = S.handle_retraction(drifted, last_valid=F.identity(3))
    print("   collapse E=%.2e -> retract -> E=%d  (shard %s, drift=%.2e)"
          % (before, S.frobenius_energy(rec["recovered"]), rec["shard"]["shard_hash"][:12], rec["shard"]["energy_drift"]))
    print("\n   The manifold is not 'perfect' in real space; it is exactly constrained in integer space —")
    print("   deviations beyond epsilon are not bugs, they are events that trigger a verified recovery.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[aether] set PYTHONHASHSEED=0 (manifold state hashes must match across machines).\n\n")
        raise SystemExit(2)
    main()
