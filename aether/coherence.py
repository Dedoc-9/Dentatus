"""
aether/coherence.py — Stage E: spectral observability over the SPD cone (quantum-STYLE diagnostics,
never quantum control).

A density-like descriptor is formed from the SPD covariance (NOT the Stiefel frame):

    ρ_P = P / tr(P)

Substrate matters and was decided by measurement: ρ from the orthonormal Stiefel frame is degenerate —
WᵀW=I pins WWᵀ to a projector with spectrum {1/k}, so purity ≡ 1/k and entropy ≡ log k are CONSTANTS
(manifold identities, not observables). The SPD covariance carries the anisotropy the layer wants to see,
so ρ_P is the informative substrate.

Observables split by the quantum-info analogy (all PURE telemetry — never gate, identity, or steer Z):
  SPECTRAL INVARIANTS (functions of λ(P), unchanged under P→UPUᵀ):  purity, mixedness, entropy
  BASIS-DEPENDENT (varies under rotation at fixed spectrum):       coherence

  purity     P_pur = tr(ρ²) = Σ P_ij² / (Σ P_ii)²         POLYNOMIAL → exact fixed-point
  coherence  C     = ‖ρ − diag(ρ)‖_F = ‖offdiag P‖_F/tr P  POLYNOMIAL → exact fixed-point
  mixedness  1 − P_pur                                      exact fixed-point
  entropy    H = −tr(ρ log ρ)                               eigen+log → FLOAT-only, DEFERRED (not wired)

Determinism split (hard-locked): purity and coherence are algebraic and belong beside E, G, β as exact
fixed-point observables. Entropy needs spectral decomposition + logs; it exists only as float telemetry
with the same status as the deferred SPD log-geodesic — informative, never structural, never a control
primitive.

Independence (measured, R1 gate 5): on a coupled SPD trajectory, corr(C, {E,B,β}) and corr(purity,
{E,B,β}) are all |·| ≤ 0.2 — the spectral pressure is a genuinely new axis, not a re-coordinatization.

Stdlib only.
"""
import math

SCALE_BITS = 32
SCALE = 1 << SCALE_BITS


def _tr(P):
    return sum(P[i][i] for i in range(len(P)))


def purity(P):
    """tr(ρ²) as a Q32 ratio, ρ=P/tr(P). For symmetric P, tr(ρ²)=Σ P_ij²/(ΣP_ii)². Range [1/n, 1]."""
    n = len(P)
    sq = sum(P[i][j] * P[i][j] for i in range(n) for j in range(n))
    tr = _tr(P)
    return (sq * SCALE) // (tr * tr) if tr else 0


def coherence(P):
    """‖ρ − diag(ρ)‖_F = isqrt(Σ_{i≠j} P_ij²)/tr(P), as Q32 — basis-coupling of the covariance modes."""
    n = len(P)
    off = sum(P[i][j] * P[i][j] for i in range(n) for j in range(n) if i != j)
    tr = _tr(P)
    return (math.isqrt(off) * SCALE) // tr if tr else 0


def mixedness(P):
    """1 − purity (Q32). High ⇒ distributed/mixed covariance; ~0 ⇒ concentrated/coherent.
    Like purity, a SPECTRAL INVARIANT: a function of λ(P) only, unchanged by P → U P Uᵀ (verified)."""
    return SCALE - purity(P)


def cross_coupling(beta1, coherence_q32, eps=1):
    """Ξ = β₁ / (C + ε) (Response-2 cross-layer observable). Tests whether dynamical complexity (β₁)
    manifests as basis coherence loss or whether they are orthogonal failure modes. LOGGED telemetry and
    a defer-and-log hypothesis — NOT a claim, NOT a gate. Returned as a Q32-scaled ratio."""
    return (beta1 * SCALE) // (coherence_q32 + eps)


def spectral_pressures(P):
    """The two EXACT fixed-point spectral observables for M̂_E (entropy is deliberately excluded)."""
    return {"coherence": coherence(P), "mixedness": mixedness(P)}


# ----------------------------------------------------------------- DEFERRED: float-only entropy
def entropy_float(P, iters=60):
    """H = −Σ λ̂ log λ̂ over the normalized SPD spectrum (λ̂ = λ/tr). FLOAT-ONLY TELEMETRY — needs a
    spectral decomposition + logs, so it is NOT exact, NOT in any hash, NOT in M̂_E (Stage-E R1 step 4:
    no entropy until a fixed-point/log path is intentionally accepted). Stdlib Jacobi eigenvalues."""
    n = len(P)
    A = [[P[i][j] / SCALE for j in range(n)] for i in range(n)]
    for _ in range(iters):                                  # Jacobi rotation sweep (symmetric)
        p, qx, mx = 0, 1, 0.0
        for i in range(n):
            for j in range(i + 1, n):
                if abs(A[i][j]) > mx:
                    mx, p, qx = abs(A[i][j]), i, j
        if mx < 1e-15:
            break
        app, aqq, apq = A[p][p], A[qx][qx], A[p][qx]
        phi = 0.5 * math.atan2(2 * apq, aqq - app) if (aqq - app) else math.pi / 4
        c, s = math.cos(phi), math.sin(phi)
        for k in range(n):
            akp, akq = A[k][p], A[k][qx]
            A[k][p] = c * akp - s * akq
            A[k][qx] = s * akp + c * akq
        for k in range(n):
            akp, akq = A[p][k], A[qx][k]
            A[p][k] = c * akp - s * akq
            A[qx][k] = s * akp + c * akq
    eig = [A[i][i] for i in range(n)]
    tr = sum(eig)
    H = 0.0
    for lam in eig:
        x = lam / tr if tr else 0
        if x > 1e-15:
            H -= x * math.log(x)
    return H


# ----------------------------------------------------------------- correlation analysis (R1 gate 5)
def pearson(x, y):
    n = len(x)
    if n == 0:
        return 0.0
    mx, my = sum(x) / n, sum(y) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return cov / (sx * sy) if sx > 0 and sy > 0 else 0.0


def correlations(series):
    """Pearson corr of each spectral series vs each existing-axis series. dict in -> dict out.
    Verdict heuristic: max |corr| ≤ 0.5 ⇒ 'separate' (new axis); else 'redundant' (re-coordinatization)."""
    out = {}
    mx = 0.0
    for a in ("coherence", "purity"):
        for b in ("E", "B", "beta"):
            if a in series and b in series:
                r = pearson(series[a], series[b])
                out["corr(%s,%s)" % (a, b)] = r
                mx = max(mx, abs(r))
    out["verdict"] = "separate" if mx <= 0.5 else "redundant"
    out["max_abs_corr"] = mx
    return out
