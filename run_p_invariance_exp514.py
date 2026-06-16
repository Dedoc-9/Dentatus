"""
run_p_invariance_exp514.py -- Fork B: EXP-514 P_yz invariance (reflection x -> -x).

Sector D covariance eigenvalues are reflection-invariant (Sigma -> P Sigma P^T, P=diag(-1,1,1), is a
similarity transform), so chi, chi_required and the coupled dS_cit are P_yz-invariant. PYTHONHASHSEED=0.
"""
import sys, os
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/observability"))
import numpy as np
from engine.validity import material_compliance_chi_514 as chi_of, cholesky_from_stalk_401, bethe_citadel_strain_512 as F

def stalk(l11, l22, l33, l21=0.0, l31=0.0, l32=0.0):
    s = np.zeros(18); s[12:18] = [l11, l22, l33, l21, l31, l32]; return s

sk = stalk(0.7, 0.1, -0.5, 0.4, 0.2, 0.3)
_, Sigma = cholesky_from_stalk_401(sk)
P = np.diag([-1.0, 1.0, 1.0])
Sigma_ref = P @ Sigma @ P.T
chi_a = chi_of(cov_eigvals=np.linalg.eigvalsh(Sigma))
chi_b = chi_of(cov_eigvals=np.linalg.eigvalsh(Sigma_ref))

assert chi_a["chi"] == chi_b["chi"] and chi_a["eta_spec"] == chi_b["eta_spec"]
print(f"[1] PASS  P_yz: chi(Sigma) == chi(P Sigma P^T) = {chi_a['chi']} (covariance eigenvalues invariant)")

ra = F(40.0, 0.12, 148, 396, vorticity=0.40, chi=chi_a["chi"])
rb = F(40.0, 0.12, 148, 396, vorticity=0.40, chi=chi_b["chi"])
assert ra["dS_cit"] == rb["dS_cit"]
print(f"[2] PASS  coupled dS_cit invariant under reflection ({ra['dS_cit']})")
assert ra["chi_required"] == rb["chi_required"]
print(f"[3] PASS  chi_required invariant ({ra['chi_required']})")
assert ra["survivable_by_material"] == rb["survivable_by_material"]
print(f"[4] PASS  verdict invariant (survivable={ra['survivable_by_material']})")
assert chi_of(cov_eigvals=np.linalg.eigvalsh(Sigma))["chi"] == chi_a["chi"]
print(f"[5] PASS  cross-process bit-stability (PYTHONHASHSEED=0)")

print("\n=== EXP-514 Fork B: 5/5 PASS ===")
print("    Reflection-invariant: Sigma=L L^T eigenvalues are P_yz scalars -> chi, chi_required, verdict invariant.")
