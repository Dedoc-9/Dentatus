"""
AetherManifold/demo_manifold_stable.py — deterministic Riemannian optimization on the Stiefel manifold.

  A. CONVERGE       — Riemannian GD fits X to a target frame on St(3,2); energy → 0, orthonormality held.
  B. DETERMINISTIC  — same seed + η + steps → bit-for-bit identical trajectory hash (reproducible result).
  C. TWO-TIER       — a rational frame is EXACTLY orthonormal (no epsilon); an evolved one holds a declared tol.
  D. STABILITY      — shadowing distance of two 1-ulp-apart trajectories → a Lyapunov observable (not a gate).
  E. CONFORMANCE    — edge-case vectors bind (problem, η, steps) to exact hashes a native port must reproduce.
  F. LYAPUNOV       — a forked, compression-bounded discrete Lyapunov certificate (per-region descent).

Run:  PYTHONHASHSEED=0 python3 demo_manifold_stable.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chronicle"))
import objective as O
import riemann as R
import stability as STA
import conformance as C
import lyapunov as L
from _cores import SCALE
fp = O.fp


def main():
    Xstar = [[fp(3, 5), 0], [fp(4, 5), 0], [0, fp(1)]]
    A = O.identity(3); B = R.F.matmul(A, Xstar)
    grad, energy = O.procrustes(A, B)
    X0 = [[fp(1, 2), 0], [fp(1, 2), 0], [0, fp(1)]]

    print("A) CONVERGE (St(3,2), fit X -> target frame; pure fixed-point):")
    res = R.optimize(X0, grad, fp(1, 5), 60, energy)
    print("   energy %.3e -> %.3e   X -> %s   max ortho_defect=%d (held by retraction)\n"
          % (res["energies"][0] / SCALE / SCALE, res["energies"][-1] / SCALE / SCALE,
             [[round(res["X"][i][j] / SCALE, 2) for j in range(2)] for i in range(3)], max(res["defects"])))

    print("B) DETERMINISTIC (reproducible trajectory):")
    res2 = R.optimize(X0, grad, fp(1, 5), 60, energy)
    print("   identical trajectory hash: %s  (%s)\n" % (res["hashes"] == res2["hashes"], res["hashes"][-1][:16]))

    print("C) TWO-TIER (exact vs declared-tolerance):")
    ok, _ = R.ST.is_orthonormal_exact([[3, 4, 0], [0, 0, 5]], 5)
    print("   exact tier  (rational frame): orthonormal with NO epsilon = %s" % ok)
    print("   approx tier (evolved frame):  ortho_defect=%d held under a declared integer tolerance\n" % res["final_defect"])

    print("D) STABILITY (observable, never a gate):")
    d = STA.co_run(X0, grad, fp(1, 5), 60)
    print("   shadowing distance %d -> %d   lyapunov=%.4f  (<=0 contracting/stable)\n"
          % (d[0], d[-1], STA.lyapunov_estimate(d)))

    print("E) CONFORMANCE (edge-case vectors; the native-port oracle):")
    for name, ok, h, defect in C.export_fixtures():
        print("   %-14s ok=%s final_hash=%s defect=%d" % (name, ok, h, defect))
    tampered = dict(C.make_vector("converge"), final_hash="0" * 64)
    print("   a divergent port -> verify=%s" % (C.verify_vector(tampered),))
    print("F) LYAPUNOV CERTIFICATE (forked + compressed, exact integer observable):")
    cert = L.certificate(res["energies"], res["defects"])
    print("   regular run -> monotone_descent=%s  branches=%s  max|compressed ΔV|=%d (< SCALE, cannot overflow)"
          % (cert["monotone_descent"], {k: v["count"] for k, v in cert["branches"].items()}, cert["max_compressed_dV"]))
    resn = R.optimize([[fp(1), fp(99, 100)], [0, fp(1, 100)], [fp(1, 100), 0]], grad, fp(1, 5), 60, energy)
    cn = L.certificate(resn["energies"], resn["defects"], tol=2)
    print("   near-singular -> %d branches %s; descent holds per branch: %s\n"
          % (cn["n_branches"], {k: v["count"] for k, v in cn["branches"].items()},
             all(b["descent_holds"] for b in cn["branches"].values())))

    print("\n   We prove a specific optimization trajectory was computed exactly per the rules and is")
    print("   reproducible. We do NOT prove the minimum is global, nor stability outside the bounds.")
    print("   Stability is an observable of the trace, not a derived truth. integrity != truth.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[AetherManifold] set PYTHONHASHSEED=0 (trajectory hashes must match across machines).\n\n")
        raise SystemExit(2)
    main()
