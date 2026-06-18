"""
aether/stiefel.py — the Stiefel Auditor: verifiable orthonormality on a fixed-point manifold.

The honesty bar is razor-sharp here. We CANNOT claim a fixed-point frame is perfectly orthonormal in real
arithmetic (impossible — fixed point quantizes). We CAN prove that within the integer lattice the residual
energy E = ||W^T W - I||_F^2 never exceeds a STRICT, DECLARED integer threshold, and that when it does, the
system deterministically self-retracts back onto the manifold and LOGS the recovery as a verifiable event.

Two gates, honestly separated:
  * is_orthonormal_exact(columns, denom)  — EXACT, tolerance-free, for states held in rationals (WtW ==
    denom^2 I). No epsilon. The pure gate.
  * check_orthogonality(W, epsilon)       — for an evolved FIXED-POINT frame: E = Σ R_ij^2 against a DECLARED
    integer epsilon (STIEFEL_EPSILON_INT). The epsilon is a named cut, not a hidden float tolerance.

Imports fixedpoint + chronicle read-only.
"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chronicle"))
import fixedpoint as F
import core                                                  # chronicle/core.py

# A DECLARED structural tolerance (a named model cut, like quorum's k). E = Σ R_ij^2 must stay <= this.
# Sized so ordinary fixed-point evolution trips it (forcing a retraction) while a retracted frame passes.
STIEFEL_EPSILON_INT = F.SCALE * F.SCALE // (1 << 20)          # ~ (SCALE / 1024)^2


class StiefelError(Exception):
    pass


# ----------------------------------------------------------------- exact (rational) gate — no epsilon
def gram_int(columns):
    n = len(columns)
    return [[sum(columns[i][r] * columns[j][r] for r in range(len(columns[i]))) for j in range(n)] for i in range(n)]


def is_orthonormal_exact(columns, denom):
    if denom == 0:
        raise StiefelError("denom must be nonzero")
    G = gram_int(columns)
    d2 = denom * denom
    viol = [{"i": i, "j": j, "got": G[i][j], "expected": (d2 if i == j else 0)}
            for i in range(len(columns)) for j in range(len(columns)) if G[i][j] != (d2 if i == j else 0)]
    return (not viol, viol)


# ----------------------------------------------------------------- fixed-point residual energy + gate
def residual(W):
    """R = W^T W - I  (fixed-point integer matrix)."""
    G = F.matmul(F.transpose(W), W)
    n = len(W)
    return [[G[i][j] - (F.SCALE if i == j else 0) for j in range(n)] for i in range(n)]


def frobenius_energy(W):
    """E = ||W^T W - I||_F^2 = Σ R_ij^2  (exact integer)."""
    R = residual(W)
    return sum(R[i][j] * R[i][j] for i in range(len(R)) for j in range(len(R[0])))


def check_orthogonality(W, epsilon=STIEFEL_EPSILON_INT):
    """The Stiefel audit gate. Returns {ok, E, epsilon}. PASS iff E <= epsilon (a declared integer cut)."""
    E = frobenius_energy(W)
    return {"ok": E <= epsilon, "E": E, "epsilon": epsilon}


def state_hash(W):
    return core.state_hash({"W": W, "scale_bits": F.SCALE_BITS})


# ----------------------------------------------------------------- integer Gram-Schmidt retraction
def gram_schmidt_integer(W):
    """Deterministic modified Gram-Schmidt in fixed point (exact integer sqrt via math.isqrt). Forces W back
    onto the Stiefel manifold. Pure integer -> bit-for-bit replayable. Raises on a zero-norm (rank failure)."""
    cols = [[W[r][c] for r in range(len(W))] for c in range(len(W[0]))]
    out = []
    for c in cols:
        v = list(c)
        for u in out:
            dot = sum(F.fp_mul(v[k], u[k]) for k in range(len(v)))
            v = [v[k] - F.fp_mul(dot, u[k]) for k in range(len(v))]
        norm2 = sum(v[k] * v[k] for k in range(len(v)))
        norm = math.isqrt(norm2) if norm2 > 0 else 0
        if norm == 0:
            raise StiefelError("rank failure: zero-norm column during Gram-Schmidt")
        v = [(v[k] * F.SCALE) // norm for k in range(len(v))]
        out.append(v)
    n = len(out[0])
    return [[out[c][r] for c in range(len(out))] for r in range(n)]


def handle_retraction(W, epsilon=STIEFEL_EPSILON_INT, signer=None, last_valid=None):
    """Self-correction: re-orthonormalize and emit a verifiable RETRACTION shard {old_E, new_E, energy_drift}.
    If Gram-Schmidt cannot reach epsilon (singular) and a last_valid hashed state is given, REVERT to it."""
    old_E = frobenius_energy(W)
    try:
        Wr = gram_schmidt_integer(W)
        new_E = frobenius_energy(Wr)
        if new_E <= epsilon:
            shard = {"event": "RETRACTION", "pre_hash": state_hash(W), "post_hash": state_hash(Wr),
                     "old_E": old_E, "new_E": new_E, "energy_drift": old_E - new_E, "epsilon": epsilon}
            shard["shard_hash"] = core.state_hash(shard)
            if signer is not None:
                shard["signature"] = signer.sign(core.canonical_bytes(shard))
                shard["algo"] = signer.algo
            return {"recovered": Wr, "shard": shard}
    except StiefelError:
        Wr = None
    if last_valid is not None:
        shard = {"event": "REVERT", "pre_hash": state_hash(W), "post_hash": state_hash(last_valid),
                 "old_E": old_E, "reason": "retraction could not reach epsilon"}
        shard["shard_hash"] = core.state_hash(shard)
        return {"recovered": last_valid, "shard": shard}
    raise StiefelError("containment failed: retraction insufficient and no last_valid to revert to")
