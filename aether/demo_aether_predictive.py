"""
aether/demo_aether_predictive.py — Stage E hardening: held-out incremental predictive-value gate.
Asks whether the spectral axes FORECAST future error beyond the existing M̂ pressures. Run with
PYTHONHASHSEED=0.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixedpoint as F
import spd as SP
import ghost as Gh
import field as FD
import coherence as CO
import predictive as PR

S = F.SCALE
q = F.to_fp


def series(steps=12000, stride=15):
    A0 = [[0, q(3, 1), 0], [q(-3, 1), 0, 0], [0, 0, 0]]
    B0 = [[0, 0, q(2, 1)], [0, 0, 0], [q(-2, 1), 0, 0]]
    Dsym = [[F.to_fp(-1, 100), F.to_fp(2, 100), 0], [F.to_fp(2, 100), F.to_fp(-1, 100), 0], [0, 0, F.to_fp(1, 100)]]
    dt = q(1, 1000)
    P = [[q(3, 1), 0, 0], [0, q(2, 1), 0], [0, 0, q(1, 1)]]
    Sg = Gh.zeros_like(P)
    prevA = None
    E, Bv, Be, Cc, Mx, Gn = [], [], [], [], [], []
    for t in range(steps):
        g = F.fp_mul(q(2, 1), P[0][1]) + F.fp_mul(q(1, 2), FD._tri(t, 300))
        A = F.add(A0, F.scalar(g, B0))
        M = F.add(F.identity(3), F.scalar(dt, A))
        P = SP.symmetrize(F.add(F.matmul(F.matmul(M, P), F.transpose(M)), F.scalar(dt, Dsym)))
        if t % stride == 0:
            Gm = Gh.ghost_residual(P, SP.project_spd(P)); Sg = Gh.ema_matrix(Sg, Gm)
            E.append(SP.spd_error(P) / (S * S)); Bv.append(Gh.backreaction(Sg, P) / S)
            Be.append((FD._fro(FD._bracket(prevA, A)) if prevA is not None else 0) / S)
            Cc.append(CO.coherence(P) / S); Mx.append(CO.mixedness(P) / S); Gn.append(Gh.frob_norm(Gm) / S)
        prevA = A
    return E, Bv, Be, Cc, Mx, Gn


def main():
    E, Bv, Be, Cc, Mx, Gn = series()
    H = 4
    n = len(Gn) - H
    base = [E[:n], Bv[:n], Be[:n]]      # existing M_hat pressures (geometry, residual, dynamics)
    spec = [Cc[:n], Mx[:n]]             # spectral axes (coherence, mixedness)
    targets = {
        "future ghost ||G||": [Gn[i + H] for i in range(n)],
        "future E_SPD":        [E[i + H] for i in range(n)],
        "future mixedness":    [Mx[i + H] for i in range(n)],
        "future coherence":    [Cc[i + H] for i in range(n)],
    }
    print("Stage-E HARDENING: held-out incremental predictive value of the spectral axes (H=%d)" % H)
    print("independent information (gate 5: PASS)  !=  predictive power (this gate)\n")
    print("  %-20s  R2_base   R2_aug    dR2       verdict" % "target")
    for name, y in targets.items():
        r = PR.incremental_value(base, spec, y)
        print("  %-20s  %+.3f    %+.3f    %+.4f   %s" % (name, r["r2_base"], r["r2_aug"], r["delta_aug"], r["verdict"]))
    print("\nVERDICT: for forecasting future ERROR (ghost, E_SPD) the spectral axes are DESCRIPTIVE, not")
    print("predictive (dR2 ~ 0, indistinguishable from a random-feature control). They strongly predict")
    print("their OWN spectral future (mixedness/coherence) — but that is series PERSISTENCE, a different")
    print("quantity than error, and the existing pressures are simply blind to it. So Stage E is a")
    print("valuable DESCRIPTIVE lens on state character; it does not forecast error. integrity != truth.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[aether] set PYTHONHASHSEED=0.\n\n")
        raise SystemExit(2)
    main()
