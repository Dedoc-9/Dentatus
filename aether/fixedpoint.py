"""
aether/fixedpoint.py — deterministic fixed-point integer arithmetic for manifold evolution.

The DVSM geometry was float (f32/f64), which drifts across machines and violates `fuel` strictness. `aether`
re-implements it in FIXED-POINT integers: a real value v is stored as the integer round(v * SCALE). Every
operation is pure integer with ONE fixed truncation rule, so a run is bit-for-bit identical on any machine.

HONEST BOUND (stated loudly): fixed-point is DETERMINISTIC and REPLAYABLE, but NOT exact. `fp_mul` truncates
toward -inf by a single fixed rule, so quantization error is BOUNDED and REPRODUCIBLE (never random, never
machine-dependent) — but it is not zero. "No drift" means no *nondeterministic* drift across machines; it
does not mean no quantization. Exact, tolerance-free structural checks survive only for states held in exact
rationals/integers (see kernel.is_orthonormal_exact).

Stdlib only.
"""

SCALE_BITS = 32
SCALE = 1 << SCALE_BITS                                       # Q32 fixed-point


def to_fp(num, den=1):
    """Exact rational num/den -> nearest fixed-point integer (round half away from zero, deterministic)."""
    n = num * SCALE
    q, r = divmod(n, den)
    if 2 * abs(r) >= den:
        q += 1 if n >= 0 else -1
    return q


def fp_mul(a, b):
    """Fixed-point multiply with truncation toward ZERO (symmetric), so fp_mul(a,-b) == -fp_mul(a,b).
    Deterministic everywhere; this sign-symmetry is what lets skew/antisymmetric structure survive."""
    p = a * b
    q = abs(p) >> SCALE_BITS
    return q if p >= 0 else -q


def matmul(A, B):
    n, m, p = len(A), len(B), len(B[0])
    return [[sum(fp_mul(A[i][k], B[k][j]) for k in range(m)) for j in range(p)] for i in range(n)]


def transpose(M):
    return [list(r) for r in zip(*M)]


def add(A, B):
    return [[A[i][j] + B[i][j] for j in range(len(A[0]))] for i in range(len(A))]


def sub(A, B):
    return [[A[i][j] - B[i][j] for j in range(len(A[0]))] for i in range(len(A))]


def scalar(s_fp, M):
    return [[fp_mul(s_fp, M[i][j]) for j in range(len(M[0]))] for i in range(len(M))]


def identity(n):
    return [[SCALE if i == j else 0 for j in range(n)] for i in range(n)]
