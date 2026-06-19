# SPDX-License-Identifier: AGPL-3.0-only
"""
AetherManifold/lyapunov.py — a discrete Lyapunov certificate (forked + compressed), as an exact observable.

The continuous Lyapunov derivative is V̇ = ∇V·f. On a SWITCHED / hybrid flow (and Riemannian descent with a
retraction IS switched) it forks into branches V̇ = −fᵢ on regions Ωᵢ, and on large V you compress it so the
certificate stays bounded. This module computes the DISCRETE analogue over a trajectory — ΔVₜ = V(Xₜ₊₁) −
V(Xₜ) — entirely in integers, classifies it by region (the fork), and offers sign-preserving compression
(the bounded-dissipation laws). It is a *measured property of the trace*, never a proof of continuous-time or
global stability.

  * fork:        per-region descent — partition steps into Ωᵢ (e.g. regular vs near-singular) and report
                 whether ΔV ≤ 0 holds in each branch separately.
  * compression: a sign-preserving bounded map  c(ΔV) = sign(ΔV)·(|ΔV|·R)//(R+|ΔV|) ∈ (−R, R)  — the
                 fixed-point V/(1+V) law, so a huge ΔV cannot make the certificate overflow. R is a declared
                 compression scale (a named cut, like ε), and compression never changes the SIGN of ΔV, so
                 descent conclusions are unaffected.
  * composite:   V = maxᵢ Vᵢ (or minᵢ) for multiple candidates; the active index per step is reported.

HONEST BOUND: ΔV ≤ 0 over the observed trajectory is computational *evidence* of monotone descent within the
simulation bounds — not a proof of asymptotic/global stability outside them. Stability is observed, not derived.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cores import SCALE


def discrete_derivative(V):
    """ΔVₜ = V(Xₜ₊₁) − V(Xₜ), the exact integer discrete analogue of V̇."""
    return [V[i + 1] - V[i] for i in range(len(V) - 1)]


def compress(dv, R=SCALE):
    """Sign-preserving bounded compression: |c| = |dv|·R // (R+|dv|) ∈ [0, R). The V/(1+V) law in integers —
    a large ΔV saturates toward ±R instead of overflowing. R is a declared compression scale; sign is exact."""
    if R <= 0:
        raise ValueError("compression scale R must be positive")
    a = abs(dv)
    c = (a * R) // (R + a)
    return c if dv >= 0 else -c


def saturate(dv, cap):
    """Hard saturation to [−cap, cap] (another bounded-dissipation form; exact integer)."""
    return max(-cap, min(cap, dv))


def classify(defects, tol):
    """Region label per step: 'regular' if the orthonormality defect ≤ tol, else 'near_singular'. This is the
    Ωᵢ partition that makes V̇ fork on the switched manifold flow."""
    return ["regular" if d <= tol else "near_singular" for d in defects]


def certificate(V_series, defects, tol=4, R=SCALE):
    """A forked, compression-bounded discrete Lyapunov certificate over a trajectory. Returns:
       {monotone_descent, branches:{label:{count, max_dV, descent_holds}}, max_compressed_dV, n_branches}."""
    dV = discrete_derivative(V_series)
    labels = classify(defects[:len(dV)], tol)
    branches = {}
    for dv, lab in zip(dV, labels):
        b = branches.setdefault(lab, {"count": 0, "max_dV": None, "descent_holds": True})
        b["count"] += 1
        b["max_dV"] = dv if b["max_dV"] is None else max(b["max_dV"], dv)
        if dv > 0:
            b["descent_holds"] = False
    return {"monotone_descent": all(dv <= 0 for dv in dV),
            "branches": branches,
            "max_compressed_dV": max((abs(compress(dv, R)) for dv in dV), default=0),
            "n_branches": len(branches)}


def composite_max(*series):
    """V = maxᵢ Vᵢ pointwise (switched/hybrid composite). Returns (composite_series, active_index_per_step)."""
    n = min(len(v) for v in series)
    comp, active = [], []
    for t in range(n):
        vals = [v[t] for v in series]
        m = max(range(len(vals)), key=lambda i: vals[i])
        comp.append(vals[m]); active.append(m)
    return comp, active
