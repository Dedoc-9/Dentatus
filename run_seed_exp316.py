"""
run_seed_exp316.py - Fork A: EXP-316 Three-Component G_inject_A Seed Validation

Protocol: exp316-v1
declaration_hash: (computed below at runtime from SEED_DECLARATION_exp316.json)

Asserts:
  1.  Declaration hash match
  2.  Primary arccos path active: ||v_A|| >= 1e-6 (no fallback)
  3.  v_A has 3 non-zero components: S_A[0] > 1e-6, S_A[1] > 1e-6, S_A[3] > 1e-6
  4.  Omega_AC_final > 0 and < pi (non-trivial)
  5.  tau_opt varies across partition steps (non-constant)
  6.  norm(S_C) > 0.01, norm(S_A) > 0.001
  7.  H_t chain continuous
  8.  n_leaves > 0
  9.  Omega_AC range spans > pi/8 (not collapsed to single value)
  10. EXP-315 regression: ||v_A||_316 > ||v_A||_315 (3-component > 2-component)

Dev note (EXP-316 -- 3-component v_A):
  G_inject_A[0] = f(mass_norm)      => S_A[0] accumulates
  G_inject_A[1] = f(|Z_before[5]|)  => S_A[1] accumulates (NEW)
  G_inject_A[3] = f(kappa)          => S_A[3] accumulates
  v_A = [S_A0, S_A1, 0, S_A3]  -- three non-zero dims
  Omega_AC = arccos(S_A3 / sqrt(S_A0^2 + S_A1^2 + S_A3^2))
  ||v_A|| > ||v_A||_315 = sqrt(S_A0^2 + S_A3^2) since S_A1 > 0.

Math check:
  Seed stalk y-coord: stalk[5] = 0.5
  G_inject_A[1] = 0.1 * 0.5 / 1.0 = 0.05
  G_inject_A[0] = 0.1 * 2.0 / 2.0 = 0.1
  G_inject_A[3] = 0.1 * 0.3 * kappa / 2.0
  At step 1: S_A ~ (1-0.85)*G_inject_A (first EMA step)
  => S_A[1] / S_A[0] = 0.05 / 0.1 = 0.5  (y_val/mass_norm ratio)
  => cos(Omega_AC) = S_A3 / sqrt(S_A0^2 + S_A1^2 + S_A3^2) slightly smaller
     than EXP-315 => Omega_AC slightly larger at step 1.
"""

import sys, os, json, hashlib, math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_316_recursive, apply_gamma_315_recursive,
    _compute_omega_ac, _g_inject_316,
)
from engine.validity import kappa_integral

DECL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "studies/exp316_3comp_inject/SEED_DECLARATION_exp316.json",
)

with open(DECL_PATH) as f:
    decl = json.load(f)
EXPECTED_HASH = decl["declaration_hash"]
stored = decl.pop("declaration_hash")
canon = json.dumps(decl, sort_keys=True, separators=(",", ":"))
computed = hashlib.sha256(canon.encode()).hexdigest()
assert stored == EXPECTED_HASH and computed == EXPECTED_HASH
print(f"[1] PASS  declaration_hash = {EXPECTED_HASH[:16]}...")

D = 12
B = np.array([1.0, 0.5, 0.3])
BETA_Z = 2.0
J_AC = np.eye(4)
W_MAX = 8
NUMERIC_FLOOR = 1e-6

root_bbox = (np.zeros(3), np.ones(3))
kappa_root = kappa_integral(root_bbox)

prov = Provenance(parent_ids=(), operator_id="seed_exp316", timestamp=now_iso())
seed_stalk = np.array([1.0, 1.0, 1.0, 1.0,
                        0.5, 0.5, 0.5, 1.0,
                        0.0, 0.0, 1.0,
                        kappa_root])

root_claim = Claim(
    provenance=prov, payload="root: d=12 EXP-316",
    stalk=seed_stalk.copy(), t=0, bbox=root_bbox,
)
mu0 = MuState(
    t=0, claims={root_claim.id: root_claim}, entailments={},
    active=frozenset([root_claim.id]),
    S=np.zeros(D), alpha=ALPHA, S_A=np.zeros(8), S_C=np.zeros(4),
)
mu0.seal()
root_id = root_claim.id

mu_final, total_cost, w0 = apply_gamma_316_recursive(
    mu=mu0, claim_id=root_id, partition_key="octree_split",
    beta=1.0, budget=1e9, spent=0.0, K_budget=2048,
    depth=0, focal_point=np.array([0.5, 0.5, 0.5]),
    B=B, beta_Z=BETA_Z, J_AC=J_AC, W_max=W_MAX,
    alpha_leak=0.1, beta_CA=0.3, mass_ref=2.0, kappa_ref=2.0, y_ref=1.0,
)

n_leaves = len(mu_final.active)
S_C_final = mu_final.S_C if mu_final.S_C is not None else np.zeros(4)
S_A_final = mu_final.S_A if mu_final.S_A is not None else np.zeros(8)
S_C_norm = float(np.linalg.norm(S_C_final))
S_A_norm = float(np.linalg.norm(S_A_final))
gh4 = [h for h in (getattr(mu_final, "ghost_history", []) or []) if len(h) == 4]

print(f"    EXP-316: {n_leaves} leaves, total_cost={total_cost:.4f}")
print(f"    norm(S_C) = {S_C_norm:.6f}  norm(S_A) = {S_A_norm:.6f}")
print(f"    S_A[0:4] = {S_A_final[0:4]}")
print(f"    S_A[0]={S_A_final[0]:.8f}  S_A[1]={S_A_final[1]:.8f}  S_A[3]={S_A_final[3]:.8f}")
print(f"    ghost_history (4-tuple entries): {len(gh4)}")
if gh4:
    omegas = [h[2] for h in gh4]
    taus   = [h[3] for h in gh4]
    print(f"    Omega_AC range: [{min(omegas):.4f}, {max(omegas):.4f}] rad")
    print(f"    tau_opt range:  [{min(taus)}, {max(taus)}]")
    print(f"    Final: Omega_AC={omegas[-1]:.4f} rad  tau_opt={taus[-1]}")

v_A_final = J_AC @ S_A_final[:4]
norm_vA = float(np.linalg.norm(v_A_final))

# [2] Primary arccos path
assert norm_vA >= NUMERIC_FLOOR, f"||v_A||={norm_vA:.2e} < NUMERIC_FLOOR -- fallback activated"
print(f"[2] PASS  primary arccos path active: ||v_A|| = {norm_vA:.6f} >= {NUMERIC_FLOOR}")

# [3] Three non-zero components in v_A
assert float(S_A_final[0]) >= NUMERIC_FLOOR, f"S_A[0]={S_A_final[0]:.2e} < FLOOR (mass-norm channel)"
assert float(S_A_final[1]) >= NUMERIC_FLOOR, f"S_A[1]={S_A_final[1]:.2e} < FLOOR (y-agg channel, EXP-316)"
assert float(S_A_final[3]) >= NUMERIC_FLOOR, f"S_A[3]={S_A_final[3]:.2e} < FLOOR (kappa channel)"
print(f"[3] PASS  3-component v_A active: S_A[0]={S_A_final[0]:.6f}  S_A[1]={S_A_final[1]:.6f}  S_A[3]={S_A_final[3]:.6f}")

# [4] Omega_AC non-trivial
assert len(gh4) > 0, "no EXP-316 ghost_history entries"
omega_final = gh4[-1][2]
assert 0.0 < omega_final < math.pi, f"Omega_AC={omega_final:.6f} outside (0, pi)"
print(f"[4] PASS  Omega_AC = {omega_final:.6f} rad ({math.degrees(omega_final):.1f} deg) in (0, pi)")

# [5] tau_opt varies
all_taus = [h[3] for h in gh4]
assert len(set(all_taus)) > 1, f"tau_opt constant = {all_taus[0]} across all {len(gh4)} steps"
print(f"[5] PASS  tau_opt varies: {sorted(set(all_taus))} across {len(gh4)} steps")

# [6] S channel norms
assert S_C_norm > 0.01, f"norm(S_C) too small: {S_C_norm}"
assert S_A_norm > 0.001, f"norm(S_A) too small: {S_A_norm}"
print(f"[6] PASS  norm(S_C)={S_C_norm:.6f} > 0.01  norm(S_A)={S_A_norm:.6f} > 0.001")

# [7] H_t chain
assert mu_final._H is not None
print(f"[7] PASS  H_t = {mu_final._H[:16]}...")

# [8] Leaves
assert n_leaves > 0
print(f"[8] PASS  n_leaves = {n_leaves} > 0")

# [9] Omega_AC spans > pi/8
omegas_all = [h[2] for h in gh4]
omega_range = max(omegas_all) - min(omegas_all)
assert omega_range > math.pi / 8, (
    f"Omega_AC range={omega_range:.4f} rad < pi/8={math.pi/8:.4f}"
)
print(f"[9] PASS  Omega_AC range = {omega_range:.4f} rad > pi/8 = {math.pi/8:.4f}")

# [10] EXP-315 regression: ||v_A||_316 > ||v_A||_315 (3-component richer)
root_claim2 = Claim(
    provenance=Provenance(parent_ids=(), operator_id="seed_exp315_reg", timestamp=now_iso()),
    payload="root: d=12 EXP-315 reg",
    stalk=seed_stalk.copy(), t=0, bbox=root_bbox,
)
mu0_315 = MuState(
    t=0, claims={root_claim2.id: root_claim2}, entailments={},
    active=frozenset([root_claim2.id]),
    S=np.zeros(D), alpha=ALPHA, S_A=np.zeros(8), S_C=np.zeros(4),
)
mu0_315.seal()
mu_315, _, _ = apply_gamma_315_recursive(
    mu=mu0_315, claim_id=root_claim2.id, partition_key="octree_split",
    beta=1.0, budget=1e9, spent=0.0, K_budget=2048,
    depth=0, focal_point=np.array([0.5, 0.5, 0.5]),
    B=B, beta_Z=BETA_Z, J_AC=J_AC, W_max=W_MAX,
    alpha_leak=0.1, beta_CA=0.3, mass_ref=2.0, kappa_ref=2.0,
)
S_A_315 = mu_315.S_A if mu_315.S_A is not None else np.zeros(8)
norm_vA_315 = float(np.linalg.norm(J_AC @ S_A_315[:4]))
assert norm_vA > norm_vA_315, (
    f"||v_A||_316={norm_vA:.6f} not > ||v_A||_315={norm_vA_315:.6f} -- S_A[1] channel inactive"
)
print(f"[10] PASS  ||v_A||_316={norm_vA:.6f} > ||v_A||_315={norm_vA_315:.6f}  (3-component richer)")

# G_inject formula verification
mass_norm_check = float(np.linalg.norm(seed_stalk[0:4]))
kappa_check = float(seed_stalk[11])
y_check = float(seed_stalk[5])
from engine.operators import _g_inject_316 as _gi316
G_C_chk, G_A_chk = _gi316(mass_norm_check, kappa_check, 0.1, 0.3, 2.0, 2.0,
                           Z_before=seed_stalk, y_ref=1.0)
print(f"\n  G_inject verification (single-step root):")
print(f"  G_inject_A[0]={G_A_chk[0]:.6f}  G_inject_A[1]={G_A_chk[1]:.6f}  G_inject_A[3]={G_A_chk[3]:.6f}")
norm_vA_pred_step1 = math.sqrt(G_A_chk[0]**2 + G_A_chk[1]**2 + G_A_chk[3]**2)
omega_pred_step1 = math.acos(G_A_chk[3] / (norm_vA_pred_step1 + 1e-15))
print(f"  predicted ||v_A|| step1 (raw inject): {norm_vA_pred_step1:.6f}")
print(f"  predicted Omega_AC step1: arccos({G_A_chk[3]:.4f}/{norm_vA_pred_step1:.4f}) = {omega_pred_step1:.4f} rad ({math.degrees(omega_pred_step1):.1f} deg)")

# Observables
Z_final = mu_final.Z()
B_A = S_A_norm / (float(np.linalg.norm(Z_final[0:8])) + 1e-15)
B_C = S_C_norm / (float(np.linalg.norm(Z_final[8:12])) + 1e-15)
print(f"\n  OBS: B_A(t)={B_A:.6f}  B_C(t)={B_C:.6f}")
print(f"  OBS: final Omega_AC={omega_final:.4f} rad ({math.degrees(omega_final):.1f} deg)")
print(f"  OBS: final tau_opt={gh4[-1][3]}  tau_opt_range={min(all_taus)}-{max(all_taus)}")
print(f"  OBS: K_ratio={float(w0.max()/w0.min()):.4f}  K_align=octant_{int(np.argmax(w0))}")
print(f"  OBS: ||v_A||={norm_vA:.6f}  S_A[1]/S_A[0]={S_A_final[1]/(S_A_final[0]+1e-15):.4f}  (y/mass ratio)")

print(f"\nFork A: ALL TESTS PASSED ({n_leaves} leaves, 3-component v_A active)")
