"""
aether/regime.py — Stage D: the dimensionless meta-observability vector M̂ and the regime classifier.

This is the meta-layer: it watches whether DYNAMICS, GEOMETRY, QUANTIZATION, or REPRESENTATION is the
dominant source of approximation error. It is PURE TELEMETRY — it reads already-committed quantities and
classifies; it NEVER controls the runtime, and it is NOT in the structural hash (it is a deterministic
function of the hashed state (θ, Z, S, W), hence recomputable and carrying no new entropy).

Raw error magnitudes are incommensurable (E ~ 1e16, ‖G‖ ~ 1e8, β ~ 1e9 in Q32), so a raw argmax is a
category error. Each component is non-dimensionalized against its DECLARED scale into a pressure:

    M̂ = ( E/ε ,  ‖G‖/‖Z‖ ,  B(t) ,  β₁/‖A‖ ,  β₂/(β₁+δ) ,  β₃/(β₁+δ) )
          geometry  residual    quant   dynamics   representation (Magnus-2 truncation stress)

Regime classification is argmax over four axes {geometry, quantization, dynamics, representation}. The
four regimes are DECLARED COARSE-GRAINING boundaries (where one pressure overtakes another), not inherent
phase transitions — so the classifier always returns the label AND its margin over the runner-up.

Stdlib + fixedpoint only.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixedpoint as F

_DELTA = 1   # δ guard against division by zero when β₁ = 0 (no dynamics)


def _ratio(num, den):
    """Dimensionless Q32 ratio num/den (deterministic integer division; den floored at 1)."""
    return (num * F.SCALE) // (den if den > 0 else 1)


def meta_vector(E, epsilon, normG, normZ, B_t, beta1, normA, beta2, beta3):
    """Assemble the six dimensionless pressures (all Q32). Pure function of measured scalars."""
    return {
        "geometry":       _ratio(E, epsilon),          # E/ε
        "residual":       _ratio(normG, normZ),        # ‖G‖/‖Z‖
        "quantization":   B_t,                          # B(t) already dimensionless (Q32 ratio)
        "dynamics":       _ratio(beta1, normA),        # β₁/‖A‖
        "representation2": _ratio(beta2, beta1 + _DELTA),  # β₂/(β₁+δ)
        "representation3": _ratio(beta3, beta1 + _DELTA),  # β₃/(β₁+δ)
    }


def classify(mhat):
    """Argmax over the four regime axes. Returns {regime, margin, pressures}. The boundary between
    regimes is a declared construct — `margin` (top − runner-up, Q32) states how dominant it is."""
    axes = {
        "geometry-limited":      mhat["geometry"],
        "quantization-limited":  max(mhat["quantization"], mhat["residual"]),
        "dynamics-limited":      mhat["dynamics"],
        "representation-limited": max(mhat["representation2"], mhat["representation3"]),
    }
    ranked = sorted(axes.items(), key=lambda kv: kv[1], reverse=True)
    top, second = ranked[0], ranked[1]
    return {"regime": top[0], "margin": top[1] - second[1], "axes": axes}


def representation_pressure(mhat):
    """The Stage-D axis: max(β₂,β₃)/(β₁+δ). Small ⇒ Magnus-2 adequate; growing ⇒ truncation stressed.
    An OBSERVABLE statement about integrator validity — never an automatic switch."""
    return max(mhat["representation2"], mhat["representation3"])


# ----------------------------------------------------------------- Stage E: spectral axis (M̂_E)
def extend_spectral(mhat, coherence, mixedness):
    """Append the Stage-E spectral pressures to M̂ -> M̂_E. coherence, mixedness are exact Q32 (from
    aether/coherence.py). Pure telemetry — still NOT in identity, still never gates."""
    m = dict(mhat)
    m["coherence"] = coherence
    m["mixedness"] = mixedness
    return m


def classify_E(mhat_E):
    """Six-axis regime argmax. The quantum-info analogy (verified) splits the Stage-E observables into two
    DISTINCT axes that the first cut wrongly bundled:
      * spectral-limited  = mixedness (1−purity) — a UNITARY/SPECTRAL INVARIANT, a function of λ(P) only
                            (rotation-independent: 'what is the eigenvalue distribution').
      * coherence-limited = coherence — BASIS-DEPENDENT (varies under rotation at fixed spectrum), and
                            empirically the most dynamics(β)-coupled of the spectral observables.
    Both passed R1 gate 5 (|corr| ≤ 0.2 vs E/B/β). Returns {regime, margin, axes}; boundaries are declared
    coarse-graining constructs."""
    axes = {
        "geometry-limited":       mhat_E["geometry"],
        "quantization-limited":   max(mhat_E["quantization"], mhat_E["residual"]),
        "dynamics-limited":       mhat_E["dynamics"],
        "representation-limited": max(mhat_E["representation2"], mhat_E["representation3"]),
        "spectral-limited":       mhat_E.get("mixedness", 0),         # invariant (function of λ)
        "coherence-limited":      mhat_E.get("coherence", 0),         # basis-dependent
    }
    ranked = sorted(axes.items(), key=lambda kv: kv[1], reverse=True)
    return {"regime": ranked[0][0], "margin": ranked[0][1] - ranked[1][1], "axes": axes}
