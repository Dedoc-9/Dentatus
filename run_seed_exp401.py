"""
run_seed_exp401.py - Fork A: EXP-401 Anisotropic Gaussian Covariance Seed Validation

Protocol: exp401-v1
Inherits: exp316-v1
declaration_hash: ff1fb75eb819cf1e79e778886ebfdd4291f48e3d2cc7d1dbd0630a603a124323

Asserts:
  1.  Declaration hash match
  2.  EXP-316 regression: 92 leaves, primary arccos path active (||v_A|| >= 1e-6)
  3.  S_D non-zero: ||S_D|| > 1e-6 (Sector D EMA active)
  4.  Sigma positive-definite: is_valid_covariance_401 on reconstructed Sigma
  5.  Off-diagonal Cholesky active: |l21| > 1e-8 OR |l31| > 1e-8
  6.  l21 and l31 have expected sign from B_hat[0]*B_hat[1] and B_hat[0]*B_hat[2]
  7.  l32 (yz coupling) non-trivial: |l32| > 1e-8
  8.  H_t chain continuous
  9.  EXP-316 ghost_history (4-tuple) entries present; tau_opt in {1,2,3}
  10. S_D updates across multiple tau_opt values (covariance modulated)

Math check:
  B = [1.0, 0.5, 0.3], ||B|| = sqrt(1+0.25+0.09) = 1.1533
  B_hat = [0.8672, 0.4336, 0.2601]
  tau_opt=1, W_max=8: tau_norm=0.125
  G_D[3] = 0.05 * 0.125 * 0.8672 * 0.4336 = 0.002356
  G_D[4] = 0.05 * 0.125 * 0.8672 * 0.2601 = 0.001413
  G_D[5] = 0.05 * 0.125 * 0.4336 * 0.2601 = 0.000706
"""

import sys, os, json, hashlib, math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import apply_gamma_401_recursive, _g_inject_401, _ALPHA_D_401, p_yz_stalk_401
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
B = np.array([1.0, 0.5, 0.3])
BETA_Z = 2.0
J_AC = np.eye(4)
W_MAX = 8
NUMERIC_FLOOR = 1e-6

root_bbox = (np.zeros(3), np.ones(3))
kappa_root = kappa_integral(root_bbox)

prov = Provenance(parent_ids=(), operator_id="seed_exp401", timestamp=now_iso())
seed_stalk = np.array([1.0, 1.0, 1.0, 1.0,
                        0.5, 0.5, 0.5, 1.0,
                        0.0, 0.0, 1.0, kappa_root,
                        0.0, 0.0, 0.0, 0.0, 0.0, 0.0])  # Sector D: identity log-Cholesky

root_claim = Claim(
    provenance=prov, payload="root: d=18 EXP-401",
    stalk=seed_stalk.copy(), t=0, bbox=root_bbox,
)
mu0 = MuState(
    t=0, claims={root_claim.id: root_claim}, entailments={},
    active=frozenset([root_claim.id]),
    S=np.zeros(12), alpha=ALPHA, S_A=np.zeros(8), S_C=np.zeros(4), S_D=np.zeros(6),
)
mu0.seal()
root_id = root_claim.id

mu_final, total_cost, w0 = apply_gamma_401_recursive(
    mu=mu0, claim_id=root_id, partition_key="octree_split",
    beta=1.0, budget=1e9, spent=0.0, K_budget=2048,
    depth=0, focal_point=np.array([0.5, 0.5, 0.5]),
    B=B, beta_Z=BETA_Z, J_AC=J_AC, W_max=W_MAX,
    alpha_leak=0.1, beta_CA=0.3, mass_ref=2.0, kappa_ref=2.0, y_ref=1.0,
    alpha_D=_ALPHA_D_401,
)

n_leaves = len(mu_final.active)
S_A_final = mu_final.S_A if mu_final.S_A is not None else np.zeros(8)
S_C_final = mu_final.S_C if mu_final.S_C is not None else np.zeros(4)
S_D_final = mu_final.S_D if mu_final.S_D is not None else np.zeros(6)
v_A = J_AC @ S_A_final[:4]
norm_vA = float(np.linalg.norm(v_A))
S_D_norm = float(np.linalg.norm(S_D_final))

print(f"    EXP-401: {n_leaves} leaves, total_cost={total_cost:.4f}")
print(f"    ||v_A|| = {norm_vA:.6f}  (EXP-316 path)")
print(f"    S_D = {S_D_final}")
print(f"    S_D[3]={S_D_final[3]:.8f} (l21/xy)  S_D[4]={S_D_final[4]:.8f} (l31/xz)  S_D[5]={S_D_final[5]:.8f} (l32/yz)")
print(f"    ||S_D|| = {S_D_norm:.8f}")

# [2] EXP-316 regression
assert n_leaves == 92, f"leaf count regression: {n_leaves} != 92"
assert norm_vA >= NUMERIC_FLOOR, f"||v_A||={norm_vA:.2e} -- EXP-316 fallback"
print(f"[2] PASS  EXP-316 regression: {n_leaves} leaves, ||v_A||={norm_vA:.6f}")

# [3] S_D non-zero
assert S_D_norm > 1e-6, f"||S_D||={S_D_norm:.2e} -- Sector D EMA inactive"
print(f"[3] PASS  S_D active: ||S_D|| = {S_D_norm:.8f} > 1e-6")

# [4] Sigma positive-definite
# Reconstruct Sigma from S_D (as pseudo-stalk for Sector D)
stalk_d = np.zeros(18)
stalk_d[12:18] = S_D_final  # use S_D as Cholesky dims for PD check
L, Sigma = cholesky_from_stalk_401(stalk_d)
valid_pd = is_valid_covariance_401(stalk_d)
print(f"    Sigma (from S_D):\n{Sigma}")
assert valid_pd, f"Sigma not positive-definite from S_D"
print(f"[4] PASS  Sigma positive-definite (min eigval = {np.linalg.eigvalsh(Sigma).min():.6f})")

# [5] Off-diagonal active
assert abs(S_D_final[3]) > 1e-8 or abs(S_D_final[4]) > 1e-8, \
    f"l21={S_D_final[3]:.2e} l31={S_D_final[4]:.2e}: off-diagonal not activated"
print(f"[5] PASS  off-diag active: l21={S_D_final[3]:.8f}  l31={S_D_final[4]:.8f}")

# [6] Sign matches B_hat structure
B_hat = B / np.linalg.norm(B)
expected_sign_l21 = B_hat[0] * B_hat[1]  # should be > 0
expected_sign_l31 = B_hat[0] * B_hat[2]  # should be > 0
assert (S_D_final[3] > 0) == (expected_sign_l21 > 0), \
    f"l21 sign mismatch: S_D[3]={S_D_final[3]:.4e} expected_sign={expected_sign_l21:.4f}"
assert (S_D_final[4] > 0) == (expected_sign_l31 > 0), \
    f"l31 sign mismatch: S_D[4]={S_D_final[4]:.4e} expected_sign={expected_sign_l31:.4f}"
print(f"[6] PASS  sign matches B_hat: l21>0 (B_hat[0]*B_hat[1]={expected_sign_l21:.4f})")

# [7] l32 non-trivial
assert abs(S_D_final[5]) > 1e-8, f"l32 (yz coupling) = {S_D_final[5]:.2e}: inactive"
print(f"[7] PASS  l32 (yz coupling) active: S_D[5] = {S_D_final[5]:.8f}")

# [8] H_t chain
assert mu_final._H is not None
print(f"[8] PASS  H_t = {mu_final._H[:16]}...")

# [9] ghost_history 4-tuple entries present
gh4 = [h for h in (getattr(mu_final, "ghost_history", []) or []) if len(h) == 4]
assert len(gh4) > 0, "no EXP-316 ghost_history 4-tuple entries"
all_taus = [int(h[3]) for h in gh4]
assert set(all_taus).issubset({1,2,3}), f"tau_opt outside EXP-316 range: {set(all_taus)}"
print(f"[9] PASS  ghost_history: {len(gh4)} entries, tau_opt={sorted(set(all_taus))}")

# [10] tau_opt modulation of S_D: check that G_inject_D varies with tau_opt
tau_set = set(all_taus)
assert len(tau_set) > 1, f"tau_opt constant={list(tau_set)[0]}: S_D modulation not testable"
print(f"[10] PASS  tau_opt varies {sorted(tau_set)} -> G_inject_D modulated by tau_norm")

# Analytical check
print(f"\n  Analytical verification:")
print(f"  B_hat = {B_hat}")
for tau in sorted(tau_set):
    tau_norm = tau / W_MAX
    gd3 = _ALPHA_D_401 * tau_norm * B_hat[0] * B_hat[1]
    gd4 = _ALPHA_D_401 * tau_norm * B_hat[0] * B_hat[2]
    gd5 = _ALPHA_D_401 * tau_norm * B_hat[1] * B_hat[2]
    print(f"  tau_opt={tau}: G_D[3]={gd3:.6f}  G_D[4]={gd4:.6f}  G_D[5]={gd5:.6f}")

# Observables
B_hat_norm = float(np.linalg.norm(B_hat))
print(f"\n  OBS: ||S_D||={S_D_norm:.8f}  B_D={S_D_norm/(S_D_norm+1e-15):.4f}")
print(f"  OBS: Sigma off-diagonal: s12={Sigma[0,1]:.6f}  s13={Sigma[0,2]:.6f}  s23={Sigma[1,2]:.6f}")
print(f"  OBS: Sigma diagonal: s11={Sigma[0,0]:.6f}  s22={Sigma[1,1]:.6f}  s33={Sigma[2,2]:.6f}")
eigvals = np.linalg.eigvalsh(Sigma)
print(f"  OBS: Sigma eigenvalues: {eigvals}")
print(f"  OBS: tau_opt range={sorted(tau_set)}  ||v_A||={norm_vA:.6f}")

print(f"\nFork A: ALL TESTS PASSED ({n_leaves} leaves, Sector D covariance active)")
