"""
game/agency/recrystallize.py — EXP-521 Re-crystallization / Annealing (Fork xi).

Closes Ghost #49: the EXP-515 melt was a one-way entropy ratchet (matter melts to survive shear but
never re-orders). Re-crystallization adds the reverse leg with a DISTINCT, lower cooling threshold ->
true thermal hysteresis. A world that melted to fluid re-crystallizes only when the stress has dropped
SIGNIFICANTLY below the point at which it melted, and only down to a material a hysteresis margin
stiffer than the melt boundary (so it cannot immediately re-melt -> chatter-free).

Schmitt-trigger on the material state (cf. EXP-409 / EXP-603 latches):
    melt   boundary : chi_required(Wi)                 (stress exceeds what the material bears)
    freeze boundary : chi_required(Wi) + hysteresis    (re-order only with this much headroom)
    dead-zone       : chi_required < chi_cur < chi_required + hysteresis  -> HOLD (material memory)

Geometry — reverse of the melt geodesic, det-preserving on the same eigenbasis:
    ℓ_i = ln λ_i(Σ); ℓ̄ = mean(ℓ_i);  ℓ_i(g) = ℓ̄ + g·(ℓ_i − ℓ̄)
    g < 1 : melt   (shrink spread → isotropic → χ↑)        [EXP-515]
    g > 1 : freeze (widen  spread → ordered  → χ↓)         [EXP-521]
Re-crystallization AMPLIFIES the residual ordering; a fully isotropic (amorphous) state has no residual
direction to amplify (Ghost #54) and HOLDs absent an orienting field.

Clean room: core (chi, bethe, cholesky) + dentatus.semantic only; no engine.* import. Engine FROZEN.
"""
import os, sys
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_REALITY = os.path.dirname(os.path.dirname(_HERE))
if _REALITY not in sys.path:
    sys.path.insert(0, _REALITY)
from dentatus import core as _core
from dentatus.semantic import stalk_D_from_sigma

PROTOCOL = "exp521-v1"
HYSTERESIS_521 = 0.15      # cooling-threshold gap (Schmitt band width, in χ units)
ANNEAL_521 = 0.25          # max Δχ re-ordered per step (slow cooling)
G_MAX_521 = 8.0            # spectrum-widening cap
ISO_EPS_521 = 1e-6         # below this log-eigenvalue spread the state is amorphous (Ghost #54)
NDIG = 9


def _sigma(stalk):
    _, S = _core.cholesky_from_stalk_401(stalk); return S


def _chi_of_sigma(S):
    return _core.material_compliance_chi_514(cov_eigvals=np.linalg.eigvalsh(S))["chi"]


def _rescale(S, g):
    """Det-preserving spectrum rescale: ℓ_i -> ℓ̄ + g(ℓ_i-ℓ̄). g>1 widens (order), g<1 shrinks (melt)."""
    w, V = np.linalg.eigh(S); lam = np.maximum(w, 1e-12)
    ll = np.log(lam); lbar = ll.mean()
    lt = np.exp(lbar + g * (ll - lbar))
    return (V * lt) @ V.T


def _spread(S):
    w = np.maximum(np.linalg.eigvalsh(S), 1e-12)
    ll = np.log(w); return float(np.sqrt(((ll - ll.mean()) ** 2).mean()))


def enact_recrystallization_521(stalk, beta_Z, strain, n_fragments, n_gamma, *,
                                vorticity=None, dt=None, hysteresis=HYSTERESIS_521,
                                anneal_rate=ANNEAL_521, margin=1e-3, iters=50):
    """Re-crystallize Sector D if the stress is a hysteresis margin below the melt boundary.
    Returns (new_stalk, witness). status in {hold, recrystallized, amorphous_hold}."""
    stalk = np.asarray(stalk, float)
    S0 = _sigma(stalk); chi_cur = _chi_of_sigma(S0)
    nd = {}
    if vorticity is not None: nd["vorticity"] = float(vorticity)
    elif dt is not None: nd["dt"] = float(dt)
    bc = _core.bethe_citadel_strain_512(beta_Z, strain, n_fragments, n_gamma, chi=chi_cur, **nd)
    chi_req = bc["chi_required"]
    chi_req = 0.0 if chi_req is None else float(chi_req)
    headroom = chi_cur - chi_req
    det0 = float(np.linalg.det(S0))
    base = {"protocol": PROTOCOL, "chi_before": round(chi_cur, NDIG), "chi_required": round(chi_req, NDIG),
            "headroom": round(headroom, NDIG), "hysteresis": hysteresis, "det_before": round(det0, NDIG)}

    if headroom < hysteresis:                                   # Schmitt dead-zone: material remembers
        base.update({"status": "hold", "chi_after": round(chi_cur, NDIG), "g": 1.0,
                     "det_after": round(det0, NDIG)})
        return stalk.copy(), base
    if _spread(S0) < ISO_EPS_521:                               # amorphous: no residual order (Ghost #54)
        base.update({"status": "amorphous_hold", "chi_after": round(chi_cur, NDIG), "g": 1.0,
                     "det_after": round(det0, NDIG)})
        return stalk.copy(), base

    # cool toward a material a hysteresis margin stiffer than the melt boundary, rate-limited (slow anneal)
    chi_target = max(chi_req + hysteresis, chi_cur - anneal_rate)
    chi_target = min(chi_target, chi_cur)
    lo, hi = 1.0, G_MAX_521                                     # find g>1 with chi(rescale)<=chi_target
    for _ in range(int(iters)):
        mid = 0.5 * (lo + hi)
        if _chi_of_sigma(_rescale(S0, mid)) <= chi_target + margin: hi = mid
        else: lo = mid
    g = hi
    S1 = _rescale(S0, g); Dnew = stalk_D_from_sigma(S1)
    new_stalk = stalk.copy(); new_stalk[12:18] = Dnew
    chi_new = _core.material_compliance_chi_514(stalk=new_stalk)["chi"]
    base.update({"status": "recrystallized", "chi_after": round(chi_new, NDIG), "g": round(float(g), NDIG),
                 "det_after": round(float(np.linalg.det(S1)), NDIG)})
    return new_stalk, base
