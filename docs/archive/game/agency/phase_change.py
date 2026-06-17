"""
game/agency/phase_change.py — EXP-515 Enacted Phase Change (Fork lambda).

The EXP-514 firewall REPORTS chi_required (the minimum compliance to survive the present shear) but
never mutates the world (backreaction firewall). This module is the GAME-LAYER policy that ENACTS the
transition: when a manifold is breached (chi_world < chi_required) it re-declares its Sector D toward
isotropy just enough to survive, and emits a witnessed transition (H_before -> H_after).

Melt geometry — volume-preserving anisotropy reduction on the SPD manifold:
    l_i = ln lambda_i(Sigma);  lbar = mean(l_i)
    lambda_i(t) = exp( lbar + (1-t)*(l_i - lbar) )        # shrink spread, preserve det Sigma (volume)
    t=0 -> original;  t=1 -> isotropic at constant volume (lambda_i = geomean)
chi(t) is monotone increasing. Two modes:
    "minimal" : least entropy injection — minimal t* with chi(t*) >= chi_required + margin
    "total"   : full melt t=1 (chi -> 1)
Pure: returns a NEW stalk; never mutates engine state or the input. Engine stays frozen.
"""
import os, sys, hashlib
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_REALITY = os.path.dirname(os.path.dirname(_HERE))
if _REALITY not in sys.path:
    sys.path.insert(0, _REALITY)
from dentatus import core as _core
from dentatus.semantic import stalk_D_from_sigma

PROTOCOL = "exp515-v1"
MARGIN = 1e-3
NDIGITS = 9


def _sigma_of(stalk):
    _, Sigma = _core.cholesky_from_stalk_401(stalk)
    return Sigma


def _eig(Sigma):
    w, V = np.linalg.eigh(Sigma)
    return np.maximum(w, 1e-12), V


def _melt(Sigma, t):
    """Volume-preserving anisotropy-melt geodesic at parameter t in [0,1]."""
    lam, V = _eig(Sigma)
    ll = np.log(lam); lbar = ll.mean()
    lt = np.exp(lbar + (1.0 - t) * (ll - lbar))
    return (V * lt) @ V.T


def _chi(Sigma):
    return _core.material_compliance_chi_514(cov_eigvals=np.linalg.eigvalsh(Sigma))["chi"]


def _witness_hash(Sigma, chi):
    """P_yz-invariant structural index: built from the eigenvalue spectrum (reflection-invariant) +
    chi + protocol. Off-diagonal Sector D bits (signed under x->-x) are excluded."""
    eigs = sorted(float(x) for x in np.linalg.eigvalsh(Sigma))
    parts = ["|".join(f"{round(e, NDIGITS):.{NDIGITS}f}" for e in eigs),
             f"chi={round(float(chi), NDIGITS):.{NDIGITS}f}", f"pv={PROTOCOL}"]
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


def enact_phase_change_515(stalk, beta_Z, strain, n_fragments, n_gamma, *,
                           vorticity=None, dt=None, eps_ref=None,
                           mode="minimal", margin=MARGIN, iters=50):
    """Witnessed material phase change. Returns (new_stalk, witness).

    witness keys: status in {stable, melted, unsurvivable}, chi_before, chi_required, chi_after,
    t_star, mode, det_before, det_after, admit_before, admit_after, H_before, H_after, survivable.
    """
    stalk = np.asarray(stalk, float)
    Sig0 = _sigma_of(stalk)
    chi0 = _chi(Sig0)
    kw = {}
    if vorticity is not None:
        kw["vorticity"] = float(vorticity)
    elif dt is not None:
        kw["dt"] = float(dt)
    if eps_ref is not None:
        kw["eps_ref"] = float(eps_ref)
    bc0 = _core.bethe_citadel_strain_512(beta_Z, strain, n_fragments, n_gamma, chi=chi0, **kw)
    chi_req = bc0["chi_required"]
    survivable = bool(bc0["survivable_by_material"])
    det0 = float(np.linalg.det(Sig0))
    base = {"chi_before": round(chi0, NDIGITS), "chi_required": chi_req, "mode": mode,
            "det_before": round(det0, NDIGITS), "admit_before": bool(bc0["dS_cit"] >= 0.0),
            "H_before": _witness_hash(Sig0, chi0), "survivable": survivable, "protocol": PROTOCOL}

    # already admissible -> no transition
    if bc0["dS_cit"] >= 0.0:
        base.update({"status": "stable", "chi_after": round(chi0, NDIGITS), "t_star": 0.0,
                     "det_after": round(det0, NDIGITS), "admit_after": True, "H_after": base["H_before"]})
        return stalk.copy(), base

    # over-complex: no material (not even isotropic) survives this shear/complexity
    if not survivable or chi_req is None or chi_req > 1.0:
        base.update({"status": "unsurvivable", "chi_after": round(chi0, NDIGITS), "t_star": None,
                     "det_after": round(det0, NDIGITS), "admit_after": False, "H_after": base["H_before"]})
        return stalk.copy(), base

    if mode == "total":
        t_star = 1.0
    else:                                            # minimal entropy injection: bisection for minimal t*
        lo, hi = 0.0, 1.0
        for _ in range(int(iters)):
            mid = 0.5 * (lo + hi)
            if _chi(_melt(Sig0, mid)) >= chi_req + margin:
                hi = mid
            else:
                lo = mid
        t_star = hi
    Sig1 = _melt(Sig0, t_star)
    Dnew = stalk_D_from_sigma(Sig1)
    new_stalk = stalk.copy(); new_stalk[12:18] = Dnew
    chi1 = _core.material_compliance_chi_514(stalk=new_stalk)["chi"]
    bc1 = _core.bethe_citadel_strain_512(beta_Z, strain, n_fragments, n_gamma, chi=chi1, **kw)
    base.update({"status": "melted", "chi_after": round(chi1, NDIGITS), "t_star": round(float(t_star), NDIGITS),
                 "det_after": round(float(np.linalg.det(Sig1)), NDIGITS),
                 "admit_after": bool(bc1["dS_cit"] >= 0.0), "H_after": _witness_hash(Sig1, chi1)})
    return new_stalk, base
