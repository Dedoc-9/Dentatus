"""
run_p_invariance_exp401.py - Fork B: EXP-401 Covariance Tensor P_yz Test

Protocol: exp401-v1
Inherits: exp316-v1
declaration_hash: ff1fb75eb819cf1e79e778886ebfdd4291f48e3d2cc7d1dbd0630a603a124323

CRITICAL DISTINCTION FROM PRIOR FORKS:
  Covariance is a TENSOR, not a scalar. Under P_yz (x -> -x):
    Sigma_mir = R * Sigma_fwd * R^T  where R = diag(-1, 1, 1)
  This is NOT Sigma_mir == Sigma_fwd. Off-diagonal terms involving x NEGATE.

P_yz covariance proof:
  G_D[3] = f(B_hat[0]*B_hat[1]): B_hat[0] -> -B_hat[0] => G_D[3] -> -G_D[3]
  G_D[4] = f(B_hat[0]*B_hat[2]): B_hat[0] -> -B_hat[0] => G_D[4] -> -G_D[4]
  G_D[5] = f(B_hat[1]*B_hat[2]): unchanged (no x term)
  => S_D[3]_mir = -S_D[3]_fwd   (l21 negates)
  => S_D[4]_mir = -S_D[4]_fwd   (l31 negates)
  => S_D[5]_mir =  S_D[5]_fwd   (l32 invariant)
  => Sigma_mir = R * Sigma_fwd * R^T  QED

EXP-316 P_yz invariance (all prior assertions) still holds:
  S_A[0], S_A[1], S_A[3], S_C[3]: all invariant (unchanged)
  Omega_AC, tau_opt: invariant

Tests:
  [1]  Declaration hash
  [2]  EXP-316 regression: fwd=mir=92 leaves
  [3]  EXP-316 regression: Omega_AC P_yz-invariant (delta < 1e-10)
  [4]  EXP-316 regression: tau_opt trace invariant (0 mismatches)
  [5]  S_D[3] (l21): fwd = -mir  (anti-symmetric, delta < 1e-8)
  [6]  S_D[4] (l31): fwd = -mir  (anti-symmetric, delta < 1e-8)
  [7]  S_D[5] (l32): fwd = mir   (symmetric, delta < 1e-8)
  [8]  Sigma tensor covariance: Sigma_mir = R * Sigma_fwd * R^T (max_delta < 1e-8)
  [9]  Both Sigma_fwd and Sigma_mir are positive-definite
  [10] ||S_D|| P_yz-invariant: ||S_D||_fwd = ||S_D||_mir (norm is invariant even though components anti-symmetric)
"""

import sys, os, json, hashlib, math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_401_recursive, _ALPHA_D_401, p_yz_stalk_401,
    SECTOR_C_KAPPA_DIM,
)
from engine.validity import kappa_integral, is_valid_covariance_401, cholesky_from_stalk_401

DECL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "studies/exp401_aniso_cov/SEED_DECLARATION_exp401.json",
)
EXPECTED_HASH = "ff1fb75eb819cf1e79e778886ebfdd4291f48e3d2cc7d1dbd0630a603a124323"

with open(DECL_PATH) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
canon = json.dumps(decl, sort_keys=True, separators=(",", ":"))
computed = hashlib.sha256(canon.encode()).hexdigest()
assert stored == EXPECTED_HASH and computed == EXPECTED_HASH
print(f"[1] PASS  declaration_hash = {EXPECTED_HASH[:16]}...")

D = 18
bK = SECTOR_C_KAPPA_DIM  # = 11
B_FWD = np.array([1.0, 0.5, 0.3])
BETA_Z = 2.0
J_AC = np.eye(4)
W_MAX = 8
K_BUDGET = 2048.0

R_pyz = np.diag([-1.0, 1.0, 1.0])  # P_yz reflection matrix

def p_yz_bbox(bbox):
    lo, hi = bbox[0].copy(), bbox[1].copy()
    lo[0], hi[0] = -bbox[1][0], -bbox[0][0]
    return (lo, hi)
def p_yz_focal(fp):
    f = fp.copy(); f[0] = -f[0]; return f
def p_yz_B(B):
    B2 = B.copy(); B2[0] = -B2[0]; return B2

B_MIR = p_yz_B(B_FWD)

kappa_seed = kappa_integral((np.zeros(3), np.ones(3)))
seed_stalk_fwd = np.array([1., 1., 1., 1., 0.5, 0.5, 0.5, 1., 0.6, 0., 0.8, kappa_seed,
                             0., 0., 0., 0., 0., 0.])
bbox_fwd = (np.zeros(3), np.ones(3))
bbox_mir = p_yz_bbox(bbox_fwd)
seed_stalk_mir = p_yz_stalk_401(seed_stalk_fwd)
seed_stalk_mir[bK] = kappa_integral(bbox_mir)
fp_fwd = np.array([0.5, 0.5, 0.5])
fp_mir = p_yz_focal(fp_fwd)

def make_mu(stalk, bbox, label):
    prov = Provenance(parent_ids=(), operator_id=f"seed_{label}", timestamp=now_iso())
    claim = Claim(provenance=prov, payload=f"{label}: d=18 EXP-401",
                  stalk=stalk.copy(), t=0, bbox=bbox)
    mu = MuState(t=0, claims={claim.id: claim}, entailments={},
                 active=frozenset([claim.id]),
                 S=np.zeros(12), alpha=ALPHA, S_A=np.zeros(8), S_C=np.zeros(4), S_D=np.zeros(6))
    mu.seal()
    return mu, claim.id

mu_fwd0, root_fwd = make_mu(seed_stalk_fwd, bbox_fwd, "fwd")
mu_mir0, root_mir = make_mu(seed_stalk_mir, bbox_mir, "mir")

mu_f, cost_f, wf = apply_gamma_401_recursive(
    mu=mu_fwd0, claim_id=root_fwd, partition_key="octree_split",
    beta=1.0, budget=1e9, spent=0.0, K_budget=K_BUDGET, depth=0,
    focal_point=fp_fwd, B=B_FWD, beta_Z=BETA_Z, J_AC=J_AC, W_max=W_MAX,
    alpha_leak=0.1, beta_CA=0.3, mass_ref=2.0, kappa_ref=2.0, y_ref=1.0, alpha_D=_ALPHA_D_401,
)
mu_m, cost_m, wm = apply_gamma_401_recursive(
    mu=mu_mir0, claim_id=root_mir, partition_key="octree_split",
    beta=1.0, budget=1e9, spent=0.0, K_budget=K_BUDGET, depth=0,
    focal_point=fp_mir, B=B_MIR, beta_Z=BETA_Z, J_AC=J_AC, W_max=W_MAX,
    alpha_leak=0.1, beta_CA=0.3, mass_ref=2.0, kappa_ref=2.0, y_ref=1.0, alpha_D=_ALPHA_D_401,
)

fwd_l = len(mu_f.active); mir_l = len(mu_m.active)
S_A_f = mu_f.S_A if mu_f.S_A is not None else np.zeros(8)
S_A_m = mu_m.S_A if mu_m.S_A is not None else np.zeros(8)
S_D_f = mu_f.S_D if mu_f.S_D is not None else np.zeros(6)
S_D_m = mu_m.S_D if mu_m.S_D is not None else np.zeros(6)
gh_f = [h for h in (getattr(mu_f, "ghost_history", []) or []) if len(h) == 4]
gh_m = [h for h in (getattr(mu_m, "ghost_history", []) or []) if len(h) == 4]

print(f"  fwd_leaves={fwd_l}  mir_leaves={mir_l}")
print(f"  S_D_fwd = {S_D_f}")
print(f"  S_D_mir = {S_D_m}")
print(f"  S_D[3] fwd={S_D_f[3]:.8f}  mir={S_D_m[3]:.8f}  (l21: expect anti-symmetric)")
print(f"  S_D[4] fwd={S_D_f[4]:.8f}  mir={S_D_m[4]:.8f}  (l31: expect anti-symmetric)")
print(f"  S_D[5] fwd={S_D_f[5]:.8f}  mir={S_D_m[5]:.8f}  (l32: expect symmetric)")

# [2] EXP-316 regression: leaf count
assert fwd_l == mir_l == 92, f"leaf count regression: fwd={fwd_l} mir={mir_l}"
print(f"[2] PASS  EXP-316 regression: fwd=mir=92 leaves")

# [3] EXP-316 regression: Omega_AC invariant
assert len(gh_f) > 0 and len(gh_m) > 0
omega_f = gh_f[-1][2]; omega_m = gh_m[-1][2]
d_omega = abs(omega_f - omega_m)
assert d_omega < 1e-10, f"Omega_AC P_yz violation: delta={d_omega:.2e}"
print(f"[3] PASS  Omega_AC P_yz-invariant: {omega_f:.8f} = {omega_m:.8f}  delta={d_omega:.2e}")

# [4] EXP-316 regression: tau_opt trace invariant
n_cmp = min(len(gh_f), len(gh_m))
tau_mismatches = sum(1 for k in range(n_cmp) if int(gh_f[k][3]) != int(gh_m[k][3]))
assert tau_mismatches == 0, f"tau_opt trace mismatches: {tau_mismatches}/{n_cmp}"
print(f"[4] PASS  tau_opt trace invariant: 0/{n_cmp} mismatches")

# [5] S_D[3] anti-symmetric (l21)
d_l21 = abs(S_D_f[3] + S_D_m[3])  # fwd + mir should = 0
assert d_l21 < 1e-8, f"l21 anti-symmetry violation: fwd={S_D_f[3]:.8f} mir={S_D_m[3]:.8f} sum={d_l21:.2e}"
print(f"[5] PASS  S_D[3] (l21) anti-symmetric: fwd={S_D_f[3]:.8f}  mir={S_D_m[3]:.8f}  sum={d_l21:.2e}")

# [6] S_D[4] anti-symmetric (l31)
d_l31 = abs(S_D_f[4] + S_D_m[4])
assert d_l31 < 1e-8, f"l31 anti-symmetry violation: sum={d_l31:.2e}"
print(f"[6] PASS  S_D[4] (l31) anti-symmetric: fwd={S_D_f[4]:.8f}  mir={S_D_m[4]:.8f}  sum={d_l31:.2e}")

# [7] S_D[5] symmetric (l32)
d_l32 = abs(S_D_f[5] - S_D_m[5])
assert d_l32 < 1e-8, f"l32 symmetry violation: delta={d_l32:.2e}"
print(f"[7] PASS  S_D[5] (l32) symmetric: fwd={S_D_f[5]:.8f}  mir={S_D_m[5]:.8f}  delta={d_l32:.2e}")

# [8] Tensor covariance: Sigma_mir = R * Sigma_fwd * R^T
stalk_f18 = np.zeros(18); stalk_f18[12:18] = S_D_f
stalk_m18 = np.zeros(18); stalk_m18[12:18] = S_D_m
L_f, Sig_f = cholesky_from_stalk_401(stalk_f18)
L_m, Sig_m = cholesky_from_stalk_401(stalk_m18)
Sig_f_transformed = R_pyz @ Sig_f @ R_pyz.T
tensor_delta = np.max(np.abs(Sig_m - Sig_f_transformed))
assert tensor_delta < 1e-8, f"Tensor covariance violation: Sigma_mir != R*Sigma_fwd*R^T, max_delta={tensor_delta:.2e}"
print(f"[8] PASS  Sigma_mir = R*Sigma_fwd*R^T  max_delta={tensor_delta:.2e}")
print(f"     Sigma_fwd:\n{Sig_f}")
print(f"     R*Sigma_fwd*R^T:\n{Sig_f_transformed}")
print(f"     Sigma_mir:\n{Sig_m}")

# [9] Both PD
assert is_valid_covariance_401(stalk_f18), "Sigma_fwd not positive-definite"
assert is_valid_covariance_401(stalk_m18), "Sigma_mir not positive-definite"
print(f"[9] PASS  Both Sigma_fwd and Sigma_mir positive-definite")

# [10] ||S_D|| invariant
norm_f = float(np.linalg.norm(S_D_f))
norm_m = float(np.linalg.norm(S_D_m))
d_norm = abs(norm_f - norm_m)
assert d_norm < 1e-8, f"||S_D|| P_yz violation: delta={d_norm:.2e}"
print(f"[10] PASS  ||S_D|| P_yz-invariant: fwd={norm_f:.8f} = mir={norm_m:.8f}  delta={d_norm:.2e}")

print(f"\n  OBS: ||S_D||={norm_f:.8f}  S_D[3]={S_D_f[3]:.6f} (l21)  S_D[5]={S_D_f[5]:.6f} (l32)")
print(f"  OBS: Sigma_fwd off-diag: s12={Sig_f[0,1]:.6f}  s13={Sig_f[0,2]:.6f}  s23={Sig_f[1,2]:.6f}")
print(f"  OBS: B_fwd={B_FWD}  B_mir={B_MIR}")
print(f"  OBS: Omega_AC={omega_f:.4f} rad  tau_opt_final={int(gh_f[-1][3])}")

print(f"\nFork B: ALL TESTS PASSED")
print(f"  EXP-401: Sigma_mir = R*Sigma_fwd*R^T. Covariance tensor P_yz-covariant.")
print(f"  S_D[3,4] anti-symmetric, S_D[5] symmetric. Series 400 open.")
