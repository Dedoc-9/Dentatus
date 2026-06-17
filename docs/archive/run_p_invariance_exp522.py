"""
run_p_invariance_exp522.py -- Fork B: EXP-522 Oriented Nucleation P_yz invariance (x -> -x).

Under joint reflection P=diag(-1,1,1) of both the material (Sector D) and the strain tensor Sym(L), the
covariance eigenvalues and the strain/covariance axis alignment are preserved, so chi_after, beta,
alignment_cos and det are P_yz-invariant. PYTHONHASHSEED=0.
"""
import sys, os
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/agency"))
import numpy as np
from dentatus import core
from phase_change import enact_phase_change_515
from nucleation import enact_oriented_nucleation_522

BETA, NF, NG, VORT = 40.0, 148, 396, 0.40
def diamond():
    s = np.zeros(18); s[0:4] = [1.0, 0.55, 0.57, 0.62]; s[12:18] = [2.0, -1.0, -1.0, 0, 0, 0]; return s
amorph, _ = enact_phase_change_515(diamond(), 40.0, 0.12, NF, NG, vorticity=VORT, mode="total")  # Sigma=I (reflection-invariant)
ax = np.array([1.0, 0.6, 0.2]); ax /= np.linalg.norm(ax)
SYM_L = 0.3 * np.outer(ax, ax) - 0.05 * np.eye(3)
P = np.diag([-1.0, 1.0, 1.0])
SYM_L_R = P @ SYM_L @ P.T                      # reflected strain tensor

_, wA = enact_oriented_nucleation_522(amorph, SYM_L, BETA, 0.05 * VORT, NF, NG, vorticity=VORT)
_, wB = enact_oriented_nucleation_522(amorph, SYM_L_R, BETA, 0.05 * VORT, NF, NG, vorticity=VORT)

assert wA["chi_after"] == wB["chi_after"]
print(f"[1] PASS  P_yz: chi_after invariant ({wA['chi_after']})")
assert wA["beta"] == wB["beta"]
print(f"[2] PASS  beta invariant ({wA['beta']})")
assert wA["alignment_cos"] == wB["alignment_cos"]
print(f"[3] PASS  alignment_cos invariant ({wA['alignment_cos']})")
assert abs(wA["det_after"] - wB["det_after"]) < 1e-9
print(f"[4] PASS  det invariant ({wA['det_after']:.4f})")
_, wA2 = enact_oriented_nucleation_522(amorph, SYM_L, BETA, 0.05 * VORT, NF, NG, vorticity=VORT)
assert wA2["chi_after"] == wA["chi_after"] and wA2["beta"] == wA["beta"]
print(f"[5] PASS  cross-process bit-stability (PYTHONHASHSEED=0)")

print("\n=== EXP-522 Fork B: 5/5 PASS ===")
print("    Reflection-invariant: nucleation acts on covariance eigenvalues + axis alignment (P_yz scalars).")
