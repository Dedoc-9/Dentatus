"""
game/agency/nucleation.py — EXP-522 Oriented Nucleation (Fork psi).

Closes Ghost #54 (the amorphous lock). EXP-521 re-crystallisation amplifies *residual* order; a fully
isotropic (total-melt) state has none, so it cannot spontaneously re-order. Oriented nucleation supplies
the missing orienting field from the current STRAIN tensor: an amorphous manifold re-crystallises along
the principal axis of Sym(L) -- the world decides its new crystal structure from the forces acting on it
(dendrites aligning to the flow).

Geometry (det-preserving nucleation aligned to the strain eigenbasis):
    Sym(L) = V_s diag(s) V_s^T      (strain tensor; s = strain eigenvalues, V_s = principal axes)
    d = s - mean(s)                 (centred -> zero-sum -> det preserved)
    Sigma' = V_s diag( c * exp(beta * d/||d||) ) V_s^T,   c = geomean(eig Sigma)  (isotropic scale)
    beta chosen so chi(Sigma') = chi_target (the EXP-521 hysteresis target)
The covariance major axis then coincides with the strain major axis (alignment ~ 1). Isotropic stress
(d -> 0) provides no field -> the state stays amorphous.

Clean room: core (chi/bethe/cholesky) + dentatus.semantic only; no engine.* import. Engine FROZEN.
"""
import os, sys
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_REALITY = os.path.dirname(os.path.dirname(_HERE))
if _REALITY not in sys.path:
    sys.path.insert(0, _REALITY)
from dentatus import core as _core
from dentatus.semantic import stalk_D_from_sigma

PROTOCOL = "exp522-v1"
HYSTERESIS_522 = 0.15
ANNEAL_522 = 0.25
ISO_EPS_522 = 1e-6        # below this spread a covariance is amorphous / a strain is isotropic
BETA_MAX_522 = 6.0
NDIG = 9


def _sigma(stalk):
    _, S = _core.cholesky_from_stalk_401(stalk); return S


def _spread(S):
    w = np.maximum(np.linalg.eigvalsh(S), 1e-12); ll = np.log(w)
    return float(np.sqrt(((ll - ll.mean()) ** 2).mean()))


def _chi(S):
    return _core.material_compliance_chi_514(cov_eigvals=np.linalg.eigvalsh(S))["chi"]


def enact_oriented_nucleation_522(stalk, sym_L, beta_Z, strain, n_fragments, n_gamma, *,
                                  vorticity=None, dt=None, hysteresis=HYSTERESIS_522,
                                  anneal_rate=ANNEAL_522, iso_eps=ISO_EPS_522, margin=1e-3, iters=50):
    """Re-crystallise an AMORPHOUS Sector D along the principal axis of the strain tensor sym_L (3x3).
    Returns (new_stalk, witness). status in {nucleated, not_amorphous, no_orienting_field, hold}."""
    stalk = np.asarray(stalk, float)
    S0 = _sigma(stalk); chi_cur = _chi(S0)
    base = {"protocol": PROTOCOL, "chi_before": round(chi_cur, NDIG), "det_before": round(float(np.linalg.det(S0)), NDIG)}

    if _spread(S0) >= iso_eps:                                  # has residual order -> EXP-521 handles it
        base.update({"status": "not_amorphous", "chi_after": round(chi_cur, NDIG)})
        return stalk.copy(), base

    sv, sV = np.linalg.eigh(np.asarray(sym_L, float))           # strain eigvals/eigvecs (ascending)
    d = sv - sv.mean()
    if float(np.linalg.norm(d)) < iso_eps:                      # isotropic stress: no orienting field
        base.update({"status": "no_orienting_field", "chi_after": round(chi_cur, NDIG)})
        return stalk.copy(), base
    dn = d / np.linalg.norm(d)

    nd = {}
    if vorticity is not None: nd["vorticity"] = float(vorticity)
    elif dt is not None: nd["dt"] = float(dt)
    bc = _core.bethe_citadel_strain_512(beta_Z, strain, n_fragments, n_gamma, chi=chi_cur, **nd)
    chi_req = bc["chi_required"]; chi_req = 0.0 if chi_req is None else float(chi_req)
    if chi_cur - chi_req < hysteresis:                          # Schmitt dead-zone (same as EXP-521)
        base.update({"status": "hold", "chi_after": round(chi_cur, NDIG), "chi_required": round(chi_req, NDIG)})
        return stalk.copy(), base
    chi_target = min(chi_cur, max(chi_req + hysteresis, chi_cur - anneal_rate))

    c = float(np.exp(np.log(np.maximum(np.linalg.eigvalsh(S0), 1e-12)).mean()))   # isotropic scale (det)
    def sigma_beta(b):
        return (sV * (c * np.exp(b * dn))) @ sV.T
    lo, hi = 0.0, BETA_MAX_522                                  # widen along strain axes until chi_target
    for _ in range(int(iters)):
        mid = 0.5 * (lo + hi)
        if _chi(sigma_beta(mid)) <= chi_target + margin: hi = mid
        else: lo = mid
    beta = hi
    S1 = sigma_beta(beta); Dnew = stalk_D_from_sigma(S1)
    new_stalk = stalk.copy(); new_stalk[12:18] = Dnew
    chi_new = _core.material_compliance_chi_514(stalk=new_stalk)["chi"]
    # alignment: covariance major eigenvector vs strain major eigenvector (|cos| -> 1)
    _, cV = np.linalg.eigh(S1)
    align = abs(float(cV[:, -1] @ sV[:, -1]))
    base.update({"status": "nucleated", "chi_after": round(chi_new, NDIG), "chi_required": round(chi_req, NDIG),
                 "beta": round(float(beta), NDIG), "alignment_cos": round(align, NDIG),
                 "det_after": round(float(np.linalg.det(S1)), NDIG)})
    return new_stalk, base
