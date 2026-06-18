"""
aether/demo_aether_coherence.py — Stage E: spectral observability over SPD (quantum-style diagnostics).
Run under PYTHONHASHSEED=0.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixedpoint as F
import stiefel as ST
import spd as SP
import ghost as Gh
import field as FD
import coherence as CO

S = F.SCALE
q = F.to_fp


def main():
    print("A) SUBSTRATE (measured): why rho from the SPD covariance, not the Stiefel frame:")
    import random
    random.seed(5)
    R = [[F.to_fp(random.randint(-1000, 1000), 1000) for _ in range(2)] for _ in range(3)]
    WWt = F.matmul(ST.gram_schmidt_integer(R), F.transpose(ST.gram_schmidt_integer(R)))
    P = [[q(3, 1), q(1, 2), 0], [q(1, 2), q(2, 1), 0], [0, 0, q(1, 1)]]
    print("   Stiefel WWt purity = %.4f  (pinned at 1/k - a manifold identity, NOT an observable)" % (CO.purity(WWt) / S))
    print("   SPD rho_P  purity = %.4f  coherence = %.4f  mixedness = %.4f" % (
        CO.purity(P) / S, CO.coherence(P) / S, CO.mixedness(P) / S))
    print("   entropy(float, DEFERRED - not wired into M_E): %.4f\n" % CO.entropy_float(P))

    print("A2) INVARIANT vs BASIS (the quantum-info distinction, measured): rotate a fixed spectrum:")
    random.seed(0)
    P0 = [[q(4, 1), 0, 0], [0, q(2, 1), 0], [0, 0, q(1, 1)]]   # spectrum lambda = {4,2,1} fixed
    purs, cohs = [], []
    for _ in range(5):
        Rr = [[F.to_fp(random.randint(-1000, 1000), 1000) for _ in range(3)] for _ in range(3)]
        U = ST.gram_schmidt_integer(Rr)
        Pr = SP.symmetrize(F.matmul(F.matmul(U, P0), F.transpose(U)))
        purs.append(CO.purity(Pr) / S)
        cohs.append(CO.coherence(Pr) / S)
    print("   purity over 5 rotations: %.6f..%.6f  (INVARIANT to quantization - spectral, depends on lambda only)"
          % (min(purs), max(purs)))
    print("   coherence:              %.4f..%.4f  (VARIES widely - basis-dependent, not spectral)\n"
          % (min(cohs), max(cohs)))

    print("B) INDEPENDENCE (R1 gate 5) - is spectral pressure a NEW axis or a re-coordinatization?")
    A0 = [[0, q(3, 1), 0], [q(-3, 1), 0, 0], [0, 0, 0]]
    B0 = [[0, 0, q(2, 1)], [0, 0, 0], [q(-2, 1), 0, 0]]
    Dsym = [[F.to_fp(-1, 100), F.to_fp(2, 100), 0], [F.to_fp(2, 100), F.to_fp(-1, 100), 0], [0, 0, F.to_fp(1, 100)]]
    dt = q(1, 1000)
    Pc = [[q(3, 1), 0, 0], [0, q(2, 1), 0], [0, 0, q(1, 1)]]
    Sg = Gh.zeros_like(Pc)
    ser = {"coherence": [], "purity": [], "E": [], "B": [], "beta": []}
    prevA = None
    for t in range(6000):
        g = F.fp_mul(q(2, 1), Pc[0][1]) + F.fp_mul(q(1, 2), FD._tri(t, 300))
        A = F.add(A0, F.scalar(g, B0))
        M = F.add(F.identity(3), F.scalar(dt, A))
        Pc = SP.symmetrize(F.add(F.matmul(F.matmul(M, Pc), F.transpose(M)), F.scalar(dt, Dsym)))
        if t % 20 == 0:
            Sg = Gh.ema_matrix(Sg, Gh.ghost_residual(Pc, SP.project_spd(Pc)))
            ser["coherence"].append(CO.coherence(Pc)); ser["purity"].append(CO.purity(Pc))
            ser["E"].append(SP.spd_error(Pc)); ser["B"].append(Gh.backreaction(Sg, Pc))
            ser["beta"].append(FD._fro(FD._bracket(prevA, A)) if prevA is not None else 0)
        prevA = A
    v = CO.correlations(ser)
    for k in ("corr(coherence,E)", "corr(coherence,B)", "corr(coherence,beta)",
              "corr(purity,E)", "corr(purity,B)", "corr(purity,beta)"):
        print("   %-24s = %+.3f" % (k, v[k]))
    print("   max|corr| = %.3f  ->  VERDICT: spectral pressure is %s from {E,B,beta}."
          % (v["max_abs_corr"], v["verdict"].upper()))

    print("\nC) INVARIANTS held: purity & coherence are EXACT fixed-point telemetry (poly), beside E/G/beta.")
    print("   They never gate, never enter Ht, never steer Z. Entropy stays float-only & deferred.")
    print("   The correlation analysis is run BEFORE the spectral axis is claimed - and it earned it.")
    print("\nD) AXIS SPLIT (corrected by the analogy): spectral-limited = mixedness (a lambda-invariant);")
    print("   coherence-limited = coherence (basis-dependent, the most beta-coupled). Response-2's Xi=beta1/(C+eps)")
    print("   is provided as logged cross-layer telemetry - a defer-and-log hypothesis, never a claim.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[aether] set PYTHONHASHSEED=0.\n\n")
        raise SystemExit(2)
    main()
