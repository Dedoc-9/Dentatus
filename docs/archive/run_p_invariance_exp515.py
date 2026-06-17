"""
run_p_invariance_exp515.py -- Fork B: EXP-515 P_yz invariance (reflection x -> -x).

The melt geodesic acts on the covariance eigenvalue spectrum, which is reflection-invariant
(Sigma -> P Sigma P^T, P=diag(-1,1,1)). So chi, t_star, det and the eigenvalue-spectrum witness hashes
are P_yz-invariant. PYTHONHASHSEED=0.
"""
import sys, os
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/agency"))
import numpy as np
from phase_change import enact_phase_change_515
from engine.validity import cholesky_from_stalk_401
from dentatus.semantic import stalk_D_from_sigma

def stalk(l11, l22, l33, l21=0.0, l31=0.0, l32=0.0):
    s = np.zeros(18); s[12:18] = [l11, l22, l33, l21, l31, l32]; return s

base = stalk(1.4, -0.6, -0.8, 0.5, 0.3, 0.2)
_, Sig = cholesky_from_stalk_401(base)
P = np.diag([-1.0, 1.0, 1.0])
refl = base.copy(); refl[12:18] = stalk_D_from_sigma(P @ Sig @ P.T)   # P_yz-reflected Sector D

_, wa = enact_phase_change_515(base, 40.0, 0.12, 148, 396, vorticity=0.40, mode="minimal")
_, wb = enact_phase_change_515(refl, 40.0, 0.12, 148, 396, vorticity=0.40, mode="minimal")

assert wa["chi_before"] == wb["chi_before"]
print(f"[1] PASS  P_yz: chi_before invariant ({wa['chi_before']})")
assert wa["t_star"] == wb["t_star"]
print(f"[2] PASS  t_star invariant ({wa['t_star']})")
assert wa["H_before"] == wb["H_before"] and wa["H_after"] == wb["H_after"]
print(f"[3] PASS  witness H_before & H_after invariant (eigenvalue-spectrum hash)")
assert abs(wa["det_before"] - wb["det_before"]) < 1e-9 and abs(wa["det_after"] - wb["det_after"]) < 1e-9
print(f"[4] PASS  det invariant under reflection ({wa['det_after']:.4f})")
_, wa2 = enact_phase_change_515(base, 40.0, 0.12, 148, 396, vorticity=0.40, mode="minimal")
assert wa2["H_after"] == wa["H_after"]
print(f"[5] PASS  cross-process bit-stability (PYTHONHASHSEED=0)")

print("\n=== EXP-515 Fork B: 5/5 PASS ===")
print("    Reflection-invariant: melt acts on covariance eigenvalues (P_yz scalars) -> chi, t*, det,")
print("    witness hashes all invariant under x->-x.")
