"""
aether/demo_aether_spd.py — Stage C: the SPD covariance cone (log-Cholesky) with an E-driven adaptive
retraction cadence and a pure ghost channel. Run under PYTHONHASHSEED=0.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixedpoint as F
import spd as SP
import evolve as E

q = lambda x: F.to_fp(x, 1)


def main():
    print("A) EXACT POSITIVITY GATE (Sylvester — no tolerance):")
    print("   [[4,2],[2,3]] SPD:", SP.is_spd_exact([[q(4), q(2)], [q(2), q(3)]]),
          "| [[1,2],[2,1]] SPD:", SP.is_spd_exact([[q(1), q(2)], [q(2), q(1)]]), "\n")

    print("B) Π_SPD RETRACTION (repair an indefinite matrix onto the cone):")
    ind = [[q(1), q(2)], [q(2), q(1)]]
    proj = SP.project_spd(ind)
    print("   indefinite -> Π_SPD -> SPD:", SP.is_spd_exact(proj), "\n")

    print("C) E-DRIVEN ADAPTIVE CADENCE (calm regime — projection effort tracks drift):")
    P0 = [[q(4), q(0)], [q(0), q(4)]]
    Dc = [[F.to_fp(-1, 1000), F.to_fp(3, 100)], [F.to_fp(3, 100), F.to_fp(-1, 1000)]]
    r = E.evolve_spd_audited(P0, Dc, F.to_fp(1, 1000), 4000, horizon=64, measure_every=64, uniform_every=64)
    print("   4000 steps: adaptive retractions=%d  (uniform-every-64 would do %d)  final SPD=%s"
          % (r["retractions"], r["uniform_retractions"], SP.is_spd_exact(r["P"])))

    print("\nD) STRONG DRIFT (the cadence must hold the cone, not skip):")
    P1 = [[q(1), q(0)], [q(0), q(1)]]
    Ds = [[F.to_fp(-2, 10), F.to_fp(5, 10)], [F.to_fp(5, 10), F.to_fp(-2, 10)]]
    raw = P1
    for _ in range(3000):
        raw = E.symmetrize_add(raw, Ds, F.to_fp(1, 1000))
    rs = E.evolve_spd_audited(P1, Ds, F.to_fp(1, 1000), 3000, horizon=64, measure_every=64)
    print("   without retraction final SPD=%s  ->  adaptive final SPD=%s (retractions=%d)"
          % (SP.is_spd_exact(raw), SP.is_spd_exact(rs["P"]), rs["retractions"]))

    print("\nE) GHOST CHANNEL (pure observable — never drives the cadence):")
    print("   structural Hₜ:", rs["structural_hash"][:16], " pv:", rs["protocol_version"])
    print("   ghost samples=%d  B(t)=%.3e  η_CLT=%d   (sensors only)"
          % (rs["ghost_samples"], rs["B_t"] / F.SCALE, rs["eta_clt"]["eta"]))
    print("\n   The covariance is not 'perfect' in real space; it is exactly constrained to the SPD cone in")
    print("   integer space — excursions are events the cheap gate predicts and the retraction repairs.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[aether] set PYTHONHASHSEED=0 (SPD state hashes must match across machines).\n\n")
        raise SystemExit(2)
    main()
