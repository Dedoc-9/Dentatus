"""
aether/field.py — Stage D: the self-describing generator FIELD A(W,t,θ), with a commutator-corrected
Magnus-2 step (Bτ) and the BCH bracket hierarchy.

Stage A–C used a CONSTANT skew generator, so the Lie bracket [A,A]=0 and Bτ was dormant. Stage D
promotes the generator to a structured field

    A = A(W, t, θ)

where θ is a DECLARED, HASHED parameter bundle naming the active dynamical regime. The hard causal
restriction: θ (and A) may depend on CONFIGURATION, SCHEDULE, or EXTERNAL FORCING, and on the live
frame W and time t — but NEVER on S, G, B(t), or M̂. The forward path stays ghost-blind; the
residual/meta channels can read the forward path, never the reverse. (Purity is enforced structurally:
A(W, t) takes only W, t and the field's own θ — the ghost state is not in scope.)

Once A moves, the brackets light up and carry the Magnus/BCH structure:

    β₁ = ‖[A_k, A_{k+1}]‖              the dynamics is moving (first Magnus correction — USED by Bτ)
    β₂ = ‖[A_k, [A_k, A_{k+1}]]‖       first NEGLECTED BCH term — Magnus-2 truncation stress
    β₃ = ‖[A_{k+1}, [A_k, A_{k+1}]]‖   the other neglected term

β₂/β₁ and β₃/β₁ are the "representation pressure": small ⇒ Magnus-2 is adequate; growing ⇒ the
truncation is losing validity. This is an OBSERVABLE statement, never an automatic integrator switch.

Magnus-2 single step (the corrected generator over one dt):

    Ω = dt·(A_k + A_{k+1})/2  +  (dt²/12)·[A_k, A_{k+1}]        # the bracket term IS Bτ
    W_{k+1} = (I + Ω)·W_k      (then the Stiefel audit/retraction restores orthonormality)

Stdlib + fixedpoint only.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixedpoint as F

FIELD_PROTOCOL = "aether-field/1"
_HALF = F.to_fp(1, 2)
_TWELFTH = F.to_fp(1, 12)


def _bracket(A, B):
    """[A,B] = A@B − B@A (fixed point). Bracket of two skew matrices is skew under symmetric trunc."""
    return F.sub(F.matmul(A, B), F.matmul(B, A))


def _tri(t, period):
    """Deterministic integer triangle wave in [-SCALE, SCALE] (a bounded SCHEDULE term — no transcendental)."""
    if period <= 0:
        return 0
    phase = t % (2 * period)
    # ramp 0..period..0 mapped to -SCALE..SCALE..-SCALE
    up = phase if phase <= period else 2 * period - phase           # 0..period..0
    return (2 * up * F.SCALE) // period - F.SCALE


class GeneratorField:
    """A(W, t) = A0 + g(W, t; θ)·B0, with two declared non-commuting skew generators A0, B0 and a
    modulation g that mixes a STATE term (k_state · W[r][c]) and a SCHEDULE term (k_sched · tri(t)).
    θ = {A0, B0, k_state, rc, k_sched, period} — all declared and hashable. NEVER reads S/G/B."""

    def __init__(self, A0, B0, k_state=0, rc=(0, 1), k_sched=0, period=1000):
        self.A0 = A0
        self.B0 = B0
        self.k_state = k_state
        self.rc = rc
        self.k_sched = k_sched
        self.period = period

    def theta(self):
        """The declared, hashable parameter bundle (enters the structural identity)."""
        return {"A0": self.A0, "B0": self.B0, "k_state": self.k_state, "rc": list(self.rc),
                "k_sched": self.k_sched, "period": self.period}

    def g(self, W, t):
        r, c = self.rc
        state_term = F.fp_mul(self.k_state, W[r][c])                 # reads W only
        sched_term = F.fp_mul(self.k_sched, _tri(t, self.period))    # reads t/θ only
        return state_term + sched_term

    def A(self, W, t):
        """The generator at (W, t). Reads W, t, θ only — never the ghost state."""
        return F.add(self.A0, F.scalar(self.g(W, t), self.B0))


def magnus2_omega(A_k, A_k1, dt_fp):
    """Ω = dt·(A_k+A_{k+1})/2 + (dt²/12)·[A_k,A_{k+1}] — the Magnus-2 corrected generator for one step.
    The commutator term is Bτ; for a constant generator A_k=A_{k+1} it reduces to dt·A (Bτ dormant)."""
    avg = F.scalar(_HALF, F.add(A_k, A_k1))
    dt2_12 = F.fp_mul(F.fp_mul(dt_fp, dt_fp), _TWELFTH)
    return F.add(F.scalar(dt_fp, avg), F.scalar(dt2_12, _bracket(A_k, A_k1)))


def bracket_hierarchy(A_k, A_k1):
    """(C1, β₁, β₂, β₃): the first BCH bracket and the magnitudes of it and the two next (neglected)
    nested brackets. β₁ = used by Magnus-2; β₂,β₃ = the truncation-stress (representation) signals."""
    C1 = _bracket(A_k, A_k1)
    b1 = _fro(C1)
    b2 = _fro(_bracket(A_k, C1))
    b3 = _fro(_bracket(A_k1, C1))
    return C1, b1, b2, b3


def _fro(M):
    import math
    return math.isqrt(sum(M[i][j] * M[i][j] for i in range(len(M)) for j in range(len(M[0]))))
