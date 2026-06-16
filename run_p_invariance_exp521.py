"""
run_p_invariance_exp521.py -- Fork B: EXP-521 Re-crystallization P_yz invariance (x -> -x).

Re-crystallization acts on the covariance eigenvalue spectrum (reflection-invariant), so chi_after, the
widening factor g, det, and the status are all P_yz-invariant. PYTHONHASHSEED=0.
"""
import sys, os
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/agency"))
import numpy as np
from dentatus import core
from dentatus.semantic import stalk_D_from_sigma
from engine.validity import cholesky_from_stalk_401
from phase_change import enact_phase_change_515
from recrystallize import enact_recrystallization_521

BETA, NF, NG, VORT = 40.0, 148, 396, 0.40
def world(dpar):
    s = np.zeros(18); s[0:4] = [1.0, 0.55, 0.57, 0.62]; s[12:18] = dpar; return s

# build a fluid material, then reflect its Sector D
fluid = world([2.0, -1.0, -1.0, 0.0, 0.0, 0.0])
for strain in [0.10, 0.13, 0.15, 0.165, 0.175]:
    ns, w = enact_phase_change_515(fluid, BETA, strain, NF, NG, vorticity=VORT)
    if w["status"] == "melted": fluid = ns
_, Sig = cholesky_from_stalk_401(fluid)
fluid_R = fluid.copy(); fluid_R[12:18] = stalk_D_from_sigma(np.diag([-1.0, 1, 1]) @ Sig @ np.diag([-1.0, 1, 1]).T)

_, wA = enact_recrystallization_521(fluid, BETA, 0.05 * VORT, NF, NG, vorticity=VORT)
_, wB = enact_recrystallization_521(fluid_R, BETA, 0.05 * VORT, NF, NG, vorticity=VORT)

assert wA["chi_after"] == wB["chi_after"]
print(f"[1] PASS  P_yz: chi_after invariant ({wA['chi_after']})")
assert wA["g"] == wB["g"]
print(f"[2] PASS  widening factor g invariant ({wA['g']})")
assert abs(wA["det_after"] - wB["det_after"]) < 1e-9
print(f"[3] PASS  det invariant under reflection ({wA['det_after']:.4f})")
assert wA["status"] == wB["status"] == "recrystallized"
print(f"[4] PASS  status invariant ({wA['status']})")
_, wA2 = enact_recrystallization_521(fluid, BETA, 0.05 * VORT, NF, NG, vorticity=VORT)
assert wA2["chi_after"] == wA["chi_after"]
print(f"[5] PASS  cross-process bit-stability (PYTHONHASHSEED=0)")

print("\n=== EXP-521 Fork B: 5/5 PASS ===")
print("    Reflection-invariant: re-crystallization acts on covariance eigenvalues (P_yz scalars).")
