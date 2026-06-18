"""
aether/predictive.py — Stage E hardening: the held-out INCREMENTAL PREDICTIVE VALUE gate.

The independence gate (regime/coherence, R1 gate 5) proved the spectral axes are not a re-coordinatization
of the existing pressures. This is the STRICTER and SEPARATE question the architecture must keep honest:

    independent information  ≠  predictive power.

A new axis can be real (independent) without helping forecast anything. This gate measures, as the
empirical proxy for I(spectral ; future residual | existing M̂):

    ΔR²(held-out) = R²(existing pressures + spectral, future target) − R²(existing pressures, future target)

evaluated on a HELD-OUT split (in-sample R² always rises with more features — that would be the
integrity-theater trap). A NEGATIVE CONTROL (append a deterministic pseudo-random feature) bounds the
ΔR² achievable by adding *any* column; the spectral axes only "earn" predictive value if their held-out
ΔR² clears both an absolute floor AND the control by a margin.

This is FLOAT offline analysis (like entropy_float): never hashed, never gating, purely a research/audit
instrument. Stdlib only.
"""
import random

DELTA_FLOOR = 0.05      # absolute held-out ΔR² floor to call an axis "predictive"
CONTROL_MARGIN = 3.0    # and it must beat the negative control's ΔR² by this factor


def _solve(A, b):
    """Gaussian elimination with partial pivoting for A x = b (small dense systems)."""
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        if abs(M[c][c]) < 1e-12:
            M[c][c] = 1e-12
        for r in range(n):
            if r != c:
                f = M[r][c] / M[c][c]
                for k in range(c, n + 1):
                    M[r][k] -= f * M[c][k]
    return [M[i][n] / M[i][i] for i in range(n)]


def _standardize_cols(X):
    cols = list(zip(*X)) if X else []
    Z = []
    for c in cols:
        m = sum(c) / len(c)
        sd = (sum((x - m) ** 2 for x in c) / len(c)) ** 0.5 or 1.0
        Z.append([(x - m) / sd for x in c])
    return [list(r) for r in zip(*Z)] if Z else X


def fit_eval_r2(Xtr, ytr, Xte, yte, ridge=1e-6):
    """OLS (with a tiny ridge on the non-intercept terms) fit on train; return held-out R² on test."""
    design = lambda X: [[1.0] + list(r) for r in X]
    Dtr = design(Xtr)
    p = len(Dtr[0])
    A = [[sum(Dtr[r][i] * Dtr[r][j] for r in range(len(Dtr))) + (ridge if i == j and i > 0 else 0.0)
          for j in range(p)] for i in range(p)]
    bv = [sum(Dtr[r][i] * ytr[r] for r in range(len(Dtr))) for i in range(p)]
    beta = _solve(A, bv)
    Dte = design(Xte)
    pred = [sum(beta[i] * Dte[r][i] for i in range(p)) for r in range(len(Dte))]
    mu = sum(yte) / len(yte)
    ss_tot = sum((y - mu) ** 2 for y in yte) or 1e-12
    ss_res = sum((yte[r] - pred[r]) ** 2 for r in range(len(yte)))
    return 1.0 - ss_res / ss_tot


def _held_out_r2(X, y, split=0.7):
    Xz = _standardize_cols(X)
    cut = int(split * len(Xz))
    return fit_eval_r2(Xz[:cut], y[:cut], Xz[cut:], y[cut:])


def incremental_value(baseline_cols, augment_cols, target, split=0.7, seed=0):
    """baseline_cols / augment_cols: lists of equal-length feature columns. target: the (future) series,
    already aligned/shifted by the caller. Returns held-out R² for baseline, augmented, and a
    negative-control (baseline + one pseudo-random column), the two ΔR², and a verdict.

    verdict 'predictive' iff ΔR²_aug ≥ DELTA_FLOOR and ΔR²_aug ≥ CONTROL_MARGIN·max(ΔR²_ctl, 0);
    else 'descriptive' (independent but not forecasting-useful for this target)."""
    n = len(target)
    base = [list(r) for r in zip(*[c[:n] for c in baseline_cols])]
    aug = [list(r) for r in zip(*[c[:n] for c in (baseline_cols + augment_cols)])]
    rng = random.Random(seed)
    noise = [rng.random() for _ in range(n)]
    ctl = [list(r) for r in zip(*[c[:n] for c in baseline_cols], noise)]
    r2_base = _held_out_r2(base, target, split)
    r2_aug = _held_out_r2(aug, target, split)
    r2_ctl = _held_out_r2(ctl, target, split)
    d_aug = r2_aug - r2_base
    d_ctl = r2_ctl - r2_base
    predictive = d_aug >= DELTA_FLOOR and d_aug >= CONTROL_MARGIN * max(d_ctl, 0.0)
    return {"r2_base": r2_base, "r2_aug": r2_aug, "r2_ctl": r2_ctl,
            "delta_aug": d_aug, "delta_ctl": d_ctl,
            "verdict": "predictive" if predictive else "descriptive"}
