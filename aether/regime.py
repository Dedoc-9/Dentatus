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
