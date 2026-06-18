"""
aether/spd.py — Stage C: the SPD cone via log-Cholesky, with an EXACT positivity gate and a
retraction-repair projection. All fixed-point integer; deterministic and replayable.

The Stiefel manifold (stiefel.py) constrains orthonormal FRAMES (WᵀW=I). The SPD cone constrains
COVARIANCE: P ≻ 0 (symmetric positive-definite) — the Sector-D geometry. Parametrization is Cholesky
P = L·Lᵀ with L lower-triangular and diag(L) > 0; positive-definiteness ⟺ that factorization exists.

Two honestly-separated gates, mirroring stiefel.py:
  * is_spd_exact(P)         — EXACT, tolerance-free: all leading principal minors > 0 (Sylvester),
                              integer determinants on the integer matrix. No epsilon. The pure gate.
  * spd_error(P, epsilon)   — for a DRIFTED fixed-point P: E_SPD = ‖P − Π_SPD(P)‖²_F against a declared
                              integer epsilon. Named cut, not a hidden float tolerance.

The cheap drift signal `gershgorin_margin` is an O(n²) lower bound on λ_min (no sqrt); it is the GATE
observable that drives the adaptive retraction cadence (see evolve.evolve_spd_audited). The expensive
Cholesky retraction Π_SPD fires only when this cheap margin says the state nears the cone boundary.

HONEST BOUND: this is the log-Cholesky PARAMETRIZATION with an exact positivity gate and a Cholesky
retraction — not a full geodesic integrator (the flat log-diagonal metric coordinate needs a fixed-point
ln; deferred). The log-Cholesky metric ≠ the affine-invariant metric; geodesics differ (a declared cut).

Stdlib + fixedpoint + chronicle (read-only).
"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chronicle"))
import fixedpoint as F
import core                                                  # chronicle/core.py

SPD_PROTOCOL = "aether-spd/1"
# Declared positive pivot floor for the retraction-repair (a named cut, like STIEFEL_EPSILON_INT).
PD_FLOOR = F.SCALE >> 16


class SPDError(Exception):
    pass


def symmetrize(P):
    """(P + Pᵀ)/2 in fixed point — the symmetric part; the cone lives on symmetric matrices."""
    n = len(P)
    return [[(P[i][j] + P[j][i]) // 2 for j in range(n)] for i in range(n)]


def fp_div(a, b):
    """Fixed-point divide a/b with truncation toward zero (symmetric), deterministic."""
    if b == 0:
        raise SPDError("division by zero pivot")
    p = a * F.SCALE
    q = abs(p) // abs(b)
    return q if (p >= 0) == (b >= 0) else -q


# ----------------------------------------------------------------- exact (integer) gate — no epsilon
def _leading_minor_det(P, k):
    """Exact integer determinant of the top-left k×k block (Bareiss-free: small k, plain expansion)."""
    M = [[P[i][j] for j in range(k)] for i in range(k)]
    # fraction-free Gaussian elimination (integer-preserving) for an exact sign/det
    det = 1
    for c in range(k):
        piv = None
        for r in range(c, k):
            if M[r][c] != 0:
                piv = r; break
        if piv is None:
            return 0
        if piv != c:
            M[c], M[piv] = M[piv], M[c]; det = -det
        det *= M[c][c]
        for r in range(c + 1, k):
            for cc in range(c + 1, k):
                M[r][cc] = (M[r][cc] * M[c][c] - M[r][c] * M[c][cc])
                if c > 0:
                    M[r][cc] //= M[c - 1][c - 1] if M[c - 1][c - 1] != 0 else 1
    return det


def is_spd_exact(P):
    """EXACT Sylvester gate: P (symmetric integer matrix) is SPD iff every leading principal minor > 0.
    Tolerance-free — operates on the integer entries directly."""
    n = len(P)
    for k in range(1, n + 1):
        if _leading_minor_det(P, k) <= 0:
            return False
    return True


# ----------------------------------------------------------------- Cholesky + retraction-repair
def cholesky_int(P, floor=0):
    """Fixed-point Cholesky L (lower-tri, L·Lᵀ ≈ P). Returns (L, ok, min_diag).
    floor=0: strict — ok=False on a non-positive pivot. floor>0: REPAIR — clamp the pivot up to `floor`
    (the retraction), so a drifted/indefinite P maps to the nearest valid Cholesky factor."""
    n = len(P)
    L = [[0] * n for _ in range(n)]
    ok = True
    min_diag = None
    for i in range(n):
        for j in range(i + 1):
            s = P[i][j] - sum(F.fp_mul(L[i][k], L[j][k]) for k in range(j))
            if i == j:
                if s <= 0:
                    ok = False
                    if floor > 0:
                        s = floor
                    else:
                        L[i][j] = 0
                        min_diag = 0
                        continue
                L[i][j] = math.isqrt(s * F.SCALE)          # L_ii = sqrt(s_real)·SCALE = isqrt(s·SCALE)
                min_diag = L[i][j] if min_diag is None else min(min_diag, L[i][j])
            else:
                L[i][j] = fp_div(s, L[j][j]) if L[j][j] != 0 else 0
    return L, ok, (min_diag or 0)


def recompose(L):
    """P = L·Lᵀ (fixed point)."""
    return F.matmul(L, F.transpose(L))


def project_spd(P, floor=PD_FLOOR):
    """Π_SPD: symmetrize, then Cholesky-repair (clamp pivots ≥ floor), then recompose — the retraction
    onto the SPD cone. Deterministic. Returns the projected SPD matrix."""
    return recompose(cholesky_int(symmetrize(P), floor=floor)[0])


def frob2(M):
    return sum(M[i][j] * M[i][j] for i in range(len(M)) for j in range(len(M[0])))


def spd_error(P, epsilon=None):
    """E_SPD = ‖P − Π_SPD(P)‖²_F — the gate quantity (0 if P is already symmetric-SPD within
    quantization). With epsilon, returns {ok, E, epsilon}."""
    E = frob2(F.sub(P, project_spd(P)))
    if epsilon is None:
        return E
    return {"ok": E <= epsilon, "E": E, "epsilon": epsilon}


def gershgorin_margin(P):
    """Cheap O(n²) lower bound on λ_min (no sqrt): min_i (P_ii − Σ_{j≠i}|P_ij|). > 0 ⇒ provably PD.
    This is the GATE observable that drives the adaptive retraction cadence — never the ghost."""
    n = len(P)
    return min(P[i][i] - sum(abs(P[i][j]) for j in range(n) if j != i) for i in range(n))


def state_hash(P):
    """Legacy SPD identity: HASH(P) only (regression oracle, parallel to stiefel.state_hash)."""
    return core.state_hash({"P": P, "scale_bits": F.SCALE_BITS})
