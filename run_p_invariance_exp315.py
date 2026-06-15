"""
run_p_invariance_exp315.py - Fork B: EXP-315 Dual G_inject_A P_yz Covariance Test

Protocol: exp315-v1
declaration_hash: e16dd1a01735bc1d6a97100daf2bfb3dfd172e2853b5875a875ccc54ea5933b0

PRIMARY ASSERTIONS (EXP-315 upgrade over EXP-314):
  Primary arccos path active in BOTH fwd and mir (no fallback)
  Omega_AC_fwd == Omega_AC_mir with primary path
  tau_opt_fwd == tau_opt_mir
  Full tau_opt trace matches (not just final step)

Proof:
  G_inject_A[0] = f(||Z_before[0:4]||) -- Sector A norm, P_yz-invariant
  G_inject_A[3] = f(Z_before[11])       -- kappa, P_yz-invariant (EXP-312)
  G_inject_C[3] = f(||Z_before[0:4]||) -- same, P_yz-invariant
  => S_A[0], S_A[3], S_C[3] accumulate P_yz-invariant quantities
  => v_A = [S_A0, 0, 0, S_A3], S_C = [0,0,0,S_C3]
  => cos(Omega_AC) = S_A3 / sqrt(S_A0^2 + S_A3^2)  -- P_yz-invariant QED

Tests:
  [1]  declaration hash
  [2]  Primary arccos path active in fwd (||v_A|| >= 1e-6)
  [3]  Primary arccos path active in mir (||v_A|| >= 1e-6)
  [4]  Omega_AC_fwd == Omega_AC_mir (final step, delta < 1e-10)
  [5]  tau_opt_fwd == tau_opt_mir (final step)
  [6]  fwd_leaves == mir_leaves
  [7]  cost_fwd == cost_mir
  [8]  norm(S_C) P_yz-invariant
  [9]  norm(S_A) P_yz-invariant
  [10] Full tau_opt trace P_yz-invariant (all steps)
"""

import sys, os, json, hashlib, math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_315_recursive,
    _zeeman_weights, _compute_child_bboxes,
    _bbox_hash_payload_312, SPATIAL_KEYS, SECTOR_C_KAPPA_DIM,
)
from engine.validity import kappa_integral

DECL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "studies/exp315_dual_inject/SEED_DECLARATION_exp315.json",
)
EXPECTED_HASH = "e16dd1a01735bc1d6a97100daf2bfb3dfd172e2853b5875a875ccc54ea5933b0"

with open(DECL_PATH) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
canon = json.dumps(decl, sort_keys=True, separators=(",", ":"))
computed = hashlib.sha256(canon.encode()).hexdigest()
assert stored == EXPECTED_HASH and computed == EXPECTED_HASH
print(f"[1] PASS  declaration_hash = {EXPECTED_HASH[:16]}...")

D = 12
bK = SECTOR_C_KAPPA_DIM
B_FWD = np.array([1.0, 0.5, 0.3])
BETA_Z = 2.0
J_AC = np.eye(4)
W_MAX = 8
K_BUDGET = 2048.0
NUMERIC_FLOOR = 1e-6

def p_yz_stalk(s):
    s = s.copy(); s[4] = -s[4]; s[8] = -s[8]; return s
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
seed_stalk = np.array([1., 1., 1., 1., 0.5, 0.5, 0.5, 1., 0.6, 0., 0.8, kappa_seed])
bbox_fwd = (np.zeros(3), np.ones(3))
bbox_mir = p_yz_bbox(bbox_fwd)
seed_stalk_mir = p_yz_stalk(seed_stalk)
seed_stalk_mir[bK] = kappa_integral(bbox_mir)
fp_fwd = np.array([0.5, 0.5, 0.5])
fp_mir = p_yz_focal(fp_fwd)

def make_mu(stalk, bbox, label):
    prov = Provenance(parent_ids=(), operator_id=f"seed_{label}", timestamp=now_iso())
    claim = Claim(provenance=prov, payload=f"{label}: d=12 EXP-315",
                  stalk=stalk.copy(), t=0, bbox=bbox)
    mu = MuState(t=0, claims={claim.id: claim}, entailments={},
                 active=frozenset([claim.id]),
                 S=np.zeros(D), alpha=ALPHA, S_A=np.zeros(8), S_C=np.zeros(4))
    mu.seal()
    return mu, claim.id

mu_fwd0, root_fwd = make_mu(seed_stalk, bbox_fwd, "fwd")
mu_mir0, root_mir = make_mu(seed_stalk_mir, bbox_mir, "mir")

mu_f, cost_f, wf = apply_gamma_315_recursive(
    mu=mu_fwd0, claim_id=root_fwd, partition_key="octree_split",
    beta=1.0, budget=1e9, spent=0.0, K_budget=K_BUDGET, depth=0,
    focal_point=fp_fwd, B=B_FWD, beta_Z=BETA_Z, J_AC=J_AC, W_max=W_MAX,
    alpha_leak=0.1, beta_CA=0.3, mass_ref=2.0, kappa_ref=2.0,
)
mu_m, cost_m, wm = apply_gamma_315_recursive(
    mu=mu_mir0, claim_id=root_mir, partition_key="octree_split",
    beta=1.0, budget=1e9, spent=0.0, K_budget=K_BUDGET, depth=0,
    focal_point=fp_mir, B=B_MIR, beta_Z=BETA_Z, J_AC=J_AC, W_max=W_MAX,
    alpha_leak=0.1, beta_CA=0.3, mass_ref=2.0, kappa_ref=2.0,
)

fwd_l = len(mu_f.active); mir_l = len(mu_m.active)
gh_f = [h for h in (getattr(mu_f, "ghost_history", []) or []) if len(h) == 4]
gh_m = [h for h in (getattr(mu_m, "ghost_history", []) or []) if len(h) == 4]

S_A_f = mu_f.S_A if mu_f.S_A is not None else np.zeros(8)
S_A_m = mu_m.S_A if mu_m.S_A is not None else np.zeros(8)
S_C_f = mu_f.S_C if mu_f.S_C is not None else np.zeros(4)
S_C_m = mu_m.S_C if mu_m.S_C is not None else np.zeros(4)

v_A_f = J_AC @ S_A_f[:4]
v_A_m = J_AC @ S_A_m[:4]
norm_vA_f = float(np.linalg.norm(v_A_f))
norm_vA_m = float(np.linalg.norm(v_A_m))

print(f"  fwd_leaves={fwd_l}  mir_leaves={mir_l}")
print(f"  ||v_A|| fwd={norm_vA_f:.6f}  mir={norm_vA_m:.6f}")
if gh_f and gh_m:
    print(f"  Omega_AC final: fwd={gh_f[-1][2]:.8f}  mir={gh_m[-1][2]:.8f}  delta={abs(gh_f[-1][2]-gh_m[-1][2]):.2e}")
    print(f"  tau_opt final:  fwd={int(gh_f[-1][3])}  mir={int(gh_m[-1][3])}")

# [2] Primary path active fwd
assert norm_vA_f >= NUMERIC_FLOOR, f"fwd fallback activated: ||v_A||={norm_vA_f:.2e}"
print(f"[2] PASS  primary path active (fwd): ||v_A|| = {norm_vA_f:.6f} >= {NUMERIC_FLOOR}")

# [3] Primary path active mir
assert norm_vA_m >= NUMERIC_FLOOR, f"mir fallback activated: ||v_A||={norm_vA_m:.2e}"
print(f"[3] PASS  primary path active (mir): ||v_A|| = {norm_vA_m:.6f} >= {NUMERIC_FLOOR}")

# [4] Omega_AC invariant
assert len(gh_f) > 0 and len(gh_m) > 0
omega_f = gh_f[-1][2]; omega_m = gh_m[-1][2]
d_omega = abs(omega_f - omega_m)
assert d_omega < 1e-10, f"Omega_AC P_yz violation: fwd={omega_f:.8f} mir={omega_m:.8f} delta={d_omega:.2e}"
print(f"[4] PASS  Omega_AC P_yz-invariant: {omega_f:.8f} = {omega_m:.8f}  delta={d_omega:.2e}")

# [5] tau_opt invariant
tau_f = int(gh_f[-1][3]); tau_m = int(gh_m[-1][3])
assert tau_f == tau_m, f"tau_opt P_yz violation: {tau_f} != {tau_m}"
print(f"[5] PASS  tau_opt P_yz-invariant: {tau_f} == {tau_m}")

# [6] leaf count
assert fwd_l == mir_l, f"leaf count violation: {fwd_l} != {mir_l}"
print(f"[6] PASS  fwd_leaves == mir_leaves == {fwd_l}")

# [7] cost
delta_cost = abs(cost_f - cost_m)
assert delta_cost < 1e-8, f"cost P_yz violation: delta={delta_cost:.2e}"
print(f"[7] PASS  cost P_yz-invariant: {cost_f:.6f} = {cost_m:.6f}")

# [8] norm(S_C)
d_SC = abs(float(np.linalg.norm(S_C_f)) - float(np.linalg.norm(S_C_m)))
assert d_SC < 1e-8
print(f"[8] PASS  norm(S_C) P_yz-invariant: {np.linalg.norm(S_C_f):.8f} = {np.linalg.norm(S_C_m):.8f}")

# [9] norm(S_A)
d_SA = abs(float(np.linalg.norm(S_A_f)) - float(np.linalg.norm(S_A_m)))
assert d_SA < 1e-8
print(f"[9] PASS  norm(S_A) P_yz-invariant: {np.linalg.norm(S_A_f):.8f} = {np.linalg.norm(S_A_m):.8f}")

# [10] Full tau_opt trace invariant
n_compare = min(len(gh_f), len(gh_m))
tau_mismatches = sum(1 for k in range(n_compare) if int(gh_f[k][3]) != int(gh_m[k][3]))
max_omega_delta = max(abs(gh_f[k][2] - gh_m[k][2]) for k in range(n_compare))
assert tau_mismatches == 0, f"tau_opt trace mismatches: {tau_mismatches}/{n_compare}"
assert max_omega_delta < 1e-10, f"Omega_AC trace delta: {max_omega_delta:.2e}"
print(f"[10] PASS  Full trace P_yz-invariant: tau_mismatches=0/{n_compare}  max_omega_delta={max_omega_delta:.2e}")

# Confirm primary path NOT fallback for both: check S_A[0] > NUMERIC_FLOOR
assert float(S_A_f[0]) >= NUMERIC_FLOOR, f"S_A[0] fwd too small: {S_A_f[0]:.2e}"
assert float(S_A_m[0]) >= NUMERIC_FLOOR, f"S_A[0] mir too small: {S_A_m[0]:.2e}"
print(f"  S_A[0] fwd={S_A_f[0]:.6f}  mir={S_A_m[0]:.6f}  (mass-norm channel, primary path confirmed)")
print(f"  S_A[3] fwd={S_A_f[3]:.6f}  mir={S_A_m[3]:.6f}  (kappa channel)")

# Observables
all_taus_f = [int(h[3]) for h in gh_f]
print(f"\n  OBS: Omega_AC={omega_f:.4f} rad ({math.degrees(omega_f):.1f} deg)")
print(f"  OBS: tau_opt range fwd={sorted(set(all_taus_f))}  (EXP-401 lag window)")
print(f"  OBS: K_ratio_fwd={float(wf.max()/wf.min()):.4f}")
print(f"  OBS: B_fwd={B_FWD}  B_mir={B_MIR}")

print(f"\nFork B: ALL TESTS PASSED")
print(f"  EXP-315: Primary arccos path P_yz-invariant. fwd==mir=={fwd_l} leaves.")
print(f"  tau_opt trace fully invariant. Ghost #6 degeneracy resolved.")
