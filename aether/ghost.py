"""
aether/ghost.py — Stage B: the dual ghost channel (instrumentation, observable-only).

Lτ pushes the frame OFF the Stiefel manifold by a bounded, deterministic quantization. Rτ
(gram_schmidt_integer) projects it back. The DISCARDED residual is the ghost:

    Gₜ = Zₜ − Π_W(Zₜ)                      # Z = running (off-manifold) frame; Π_W = retraction

This module preserves that residual instead of destroying it, as a DUAL accumulator separate from
the forward Z-arithmetic (no algebraic collapse of the two):

    S_{t+1} = α·Sₜ + (1−α)·Gₜ              # matrix EMA, dual space
    B(t)    = ‖S‖_F / (‖Z‖_F + ε)          # backreaction-pressure observable
    η_CLT   = √N·(μ̂ − μ₀)                  # is the leak zero-mean noise (μ₀=0) or structured drift?

DETERMINISM CONTRACT: S accumulates via the SAME symmetric-truncation fp_mul and a fixed-point α as
the forward path — never native floats — so (a) the EMA is bit-for-bit replayable across machines and
(b) the sign-symmetry that lets skew structure survive is preserved in the dual space too.

PURITY CONTRACT: S, G, B(t), η_CLT are OBSERVABLES. Nothing here gates, controls, or mutates Z. The
ghost is a numeric residual, never an entity.

HONEST BOUND: B(t)/η_CLT measure quantization-leak pressure and whether it is unstructured — NOT that
the trajectory is correct, and NEVER a control input. New ghost in the aether ledger: the
quantization-leak residual.

Stdlib + fixedpoint + chronicle (read-only).
"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chronicle"))
import fixedpoint as F
import core                                                  # chronicle/core.py

# Protocol version bump: Stage B binds Sₜ into the structural identity (Hₜ includes the ghost).
PROTOCOL_VERSION = "aether/2"

# Default EMA memory α = 0.9 in fixed point (a declared dual-space constant, like ε).
ALPHA_DEFAULT = F.to_fp(9, 10)


def zeros_like(M):
    return [[0 for _ in range(len(M[0]))] for _ in range(len(M))]


def frob_norm2(M):
    """‖M‖_F^2 = Σ M_ij^2  (exact integer)."""
    return sum(M[i][j] * M[i][j] for i in range(len(M)) for j in range(len(M[0])))


def frob_norm(M):
    """‖M‖_F = isqrt(Σ M_ij^2)  (exact integer floor — deterministic)."""
    return math.isqrt(frob_norm2(M))


def ghost_residual(Z, W_proj):
    """Gₜ = Zₜ − Π_W(Zₜ).  Both are fixed-point frames; the difference is the discarded residual."""
    return F.sub(Z, W_proj)


def ema_matrix(S, G, alpha_fp=ALPHA_DEFAULT):
    """S_{t+1} = α·Sₜ + (1−α)·Gₜ, matrix-valued, via symmetric-truncation fp_mul (dual-space EMA)."""
    one_minus = F.SCALE - alpha_fp
    return F.add(F.scalar(alpha_fp, S), F.scalar(one_minus, G))


def backreaction(S, Z, eps_int=1):
    """B(t) = ‖S‖_F / (‖Z‖_F + ε), returned as a Q32 fixed-point ratio (deterministic integer)."""
    nz = frob_norm(Z) + eps_int
    return (frob_norm(S) * F.SCALE) // nz


def clt_eta(stream, mu0=0):
    """η_CLT = √N·(μ̂ − μ₀) over the ‖Gₜ‖ sample stream. μ₀=0 tests the zero-mean-leak null.
    Returns {N, mean, eta}. Large |eta| ⇒ structured directional leak; ~0 ⇒ unstructured quantization."""
    n = len(stream)
    if n == 0:
        return {"N": 0, "mean": 0, "eta": 0}
    mean = sum(stream) // n
    eta = math.isqrt(n) * (mean - mu0)
    return {"N": n, "mean": mean, "eta": eta}


def structural_hash(mu, Z, S, W, protocol_version=PROTOCOL_VERSION):
    """Hₜ = HASH(μ ⊕ Z ⊕ S ⊕ W ⊕ protocol_version) — the Stage-B structural identity.
    The ghost S is first-class state: two runs with equal W but S¹≠S² are now DISTINCT identities.
    Hash is a structural index only; it encodes no semantic interpretation."""
    return core.state_hash({"mu": mu, "Z": Z, "S": S, "W": W,
                            "protocol_version": protocol_version, "scale_bits": F.SCALE_BITS})
