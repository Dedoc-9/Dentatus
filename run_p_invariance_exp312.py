"""
run_p_invariance_exp312.py - Fork B: EXP-312 P_yz Invariance Test

Protocol: exp312-v1
declaration_hash: 2e6ccdc20da7aefb2a6bb3b024d8a3102c87e706d610ba454122afaf66329cc5

EXP-312 UPGRADE FROM EXP-311 Fork B:
  EXP-311 Fork B was single-step only (multi-step leaf count was P_yz-variant
  due to (1) absolute-coord bbox payload and (2) index-based Sector A decompose).
  EXP-312 closes both sources:
    Fix 1: _bbox_hash_payload_312  -- f(|hi-lo|) extents only, coordinate-free
    Fix 2: uniform Sector A split  -- stalk_A_i = stalk_A / N, P_yz-invariant
  Result: FULL MULTI-STEP P_yz invariance: fwd_leaves == mir_leaves.

Mathematical invariance proof (uniform split):
  stalk_A_i = stalk_A / N  ->  mass_i = mass_parent / N  (equal for all i)
  mass-weighted centroid = (1/N) * sum_i centroid_i = geometric centroid of bbox
  Under P_yz (x -> -x):  P_yz(geometric_centroid) = geometric_centroid of P_yz(bbox)
  LOD = max_extent / ||centroid - fp||
  ||P_yz(c) - P_yz(fp)|| = ||P_yz(c - fp)|| = ||c - fp||  (isometry)
  => LOD_fwd(i) = LOD_mir(i XOR 4) for all octant pairs  => identical LOD gating
  => identical recursion tree => fwd_leaves == mir_leaves  QED

Tests:
  [1] declaration hash match
  [2] fwd_leaves == mir_leaves (FULL MULTI-STEP P_yz invariance -- EXP-312 primary)
  [3] cost_fwd == cost_mir (budget consumption P_yz-invariant)
  [4] norm(S_C) P_yz-invariant (multi-step)
  [5] norm(S_A) P_yz-invariant (multi-step)
  [6] G_t = 0 identity: both orientations
  [7] G_inject_C single-step P_yz invariance
  [8] G_inject_A single-step P_yz invariance
  [9] LOD value P_yz-invariant (analytical)
  [10] sorted kappa distribution P_yz-invariant after one partition
"""

import sys, os, json, hashlib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_312, apply_gamma_312_recursive,
    SECTOR_C_KAPPA_DIM, SPATIAL_KEYS, _compute_child_bboxes,
    _bbox_hash_payload_312,
)
from engine.validity import kappa_integral, lod_value

# === Declaration hash check ===
DECL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "studies/exp312_symmetric_budget/SEED_DECLARATION_exp312.json",
)
EXPECTED_HASH = "2e6ccdc20da7aefb2a6bb3b024d8a3102c87e706d610ba454122afaf66329cc5"
with open(DECL_PATH) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
canon = json.dumps(decl, sort_keys=True, separators=(",", ":"))
computed = hashlib.sha256(canon.encode()).hexdigest()
assert stored == EXPECTED_HASH
assert computed == EXPECTED_HASH
print(f"[1] PASS  declaration_hash = {EXPECTED_HASH[:16]}...")

D = 12; bK = SECTOR_C_KAPPA_DIM

# === P_yz transforms ===
def apply_p_yz_stalk(s):
    s = s.copy(); s[4] = -s[4]; s[8] = -s[8]; return s

def apply_p_yz_bbox(bbox):
    lo, hi = bbox[0].copy(), bbox[1].copy()
    lo[0], hi[0] = -bbox[1][0], -bbox[0][0]
    return (lo, hi)

def apply_p_yz_focal(fp):
    f = fp.copy(); f[0] = -f[0]; return f

# === Seed pair ===
kappa_seed = kappa_integral((np.zeros(3), np.ones(3)))
assert abs(kappa_seed - 2.0) < 1e-12

seed_stalk = np.array([1.,1.,1.,1., 0.5,0.5,0.5,1., 0.6,0.,0.8, kappa_seed])
assert abs(np.linalg.norm(seed_stalk[8:11]) - 1.0) < 1e-12

bbox_fwd = (np.zeros(3), np.ones(3))
bbox_mir = apply_p_yz_bbox(bbox_fwd)
seed_stalk_mir = apply_p_yz_stalk(seed_stalk)
seed_stalk_mir[bK] = kappa_integral(bbox_mir)
assert abs(seed_stalk_mir[bK] - kappa_seed) < 1e-12

fp_fwd = np.array([0.5, 0.5, 0.5])
fp_mir = apply_p_yz_focal(fp_fwd)

def make_mu(stalk, bbox, label):
    prov = Provenance(parent_ids=(), operator_id=f"seed_{label}", timestamp=now_iso())
    claim = Claim(provenance=prov, payload=f"{label}: d=12 EXP-312", stalk=stalk.copy(), t=0, bbox=bbox)
    mu = MuState(t=0, claims={claim.id: claim}, entailments={}, active=frozenset([claim.id]),
                 S=np.zeros(D), alpha=ALPHA, S_A=np.zeros(8), S_C=np.zeros(4))
    mu.seal()
    return mu, claim.id

mu_fwd0, root_fwd = make_mu(seed_stalk, bbox_fwd, "fwd")
mu_mir0, root_mir = make_mu(seed_stalk_mir, bbox_mir, "mir")

# ============================================================
# [2],[3],[4],[5] -- FULL MULTI-STEP P_yz invariance
# ============================================================
mu_f, cost_f = apply_gamma_312_recursive(
    mu=mu_fwd0, claim_id=root_fwd, partition_key="octree_split",
    beta=1.0, budget=1e9, spent=0.0, K_budget=256, depth=0,
    focal_point=fp_fwd, alpha_leak=0.1, beta_CA=0.3, mass_ref=2.0, kappa_ref=2.0,
)
mu_m, cost_m = apply_gamma_312_recursive(
    mu=mu_mir0, claim_id=root_mir, partition_key="octree_split",
    beta=1.0, budget=1e9, spent=0.0, K_budget=256, depth=0,
    focal_point=fp_mir, alpha_leak=0.1, beta_CA=0.3, mass_ref=2.0, kappa_ref=2.0,
)

fwd_leaves = len(mu_f.active)
mir_leaves = len(mu_m.active)
print(f"  fwd_leaves={fwd_leaves}  mir_leaves={mir_leaves}")

assert fwd_leaves == mir_leaves, (
    f"P_yz leaf-count violation: fwd={fwd_leaves} != mir={mir_leaves}"
)
print(f"[2] PASS  fwd_leaves == mir_leaves == {fwd_leaves}  (FULL MULTI-STEP P_yz invariance)")

TOL = 1e-8
delta_cost = abs(cost_f - cost_m)
assert delta_cost < TOL, f"cost P_yz violation: fwd={cost_f:.6f} mir={cost_m:.6f} delta={delta_cost:.2e}"
print(f"[3] PASS  cost P_yz-invariant: {cost_f:.6f} = {cost_m:.6f}  delta={delta_cost:.2e}")

S_C_f = mu_f.S_C if mu_f.S_C is not None else np.zeros(4)
S_C_m = mu_m.S_C if mu_m.S_C is not None else np.zeros(4)
S_A_f = mu_f.S_A if mu_f.S_A is not None else np.zeros(8)
S_A_m = mu_m.S_A if mu_m.S_A is not None else np.zeros(8)

delta_SC = abs(float(np.linalg.norm(S_C_f)) - float(np.linalg.norm(S_C_m)))
assert delta_SC < TOL, f"norm(S_C) P_yz violation (multi-step): delta={delta_SC:.2e}"
print(f"[4] PASS  norm(S_C) P_yz-invariant (multi-step): {np.linalg.norm(S_C_f):.8f} = {np.linalg.norm(S_C_m):.8f}")

delta_SA = abs(float(np.linalg.norm(S_A_f)) - float(np.linalg.norm(S_A_m)))
assert delta_SA < TOL, f"norm(S_A) P_yz violation (multi-step): delta={delta_SA:.2e}"
print(f"[5] PASS  norm(S_A) P_yz-invariant (multi-step): {np.linalg.norm(S_A_f):.8f} = {np.linalg.norm(S_A_m):.8f}")

# ============================================================
# [6],[7],[8] -- single-step invariants (via apply_gamma_312)
# ============================================================
N = SPATIAL_KEYS["octree_split"]
pkey = "octree_split"

def make_payloads_312(bbox, n, depth=0):
    children = _compute_child_bboxes(bbox, pkey)
    return [_bbox_hash_payload_312(children[i], depth, i) for i in range(n)]

mu_fwd1, root_fwd1 = make_mu(seed_stalk, bbox_fwd, "fwd1")
mu_mir1, root_mir1 = make_mu(seed_stalk_mir, bbox_mir, "mir1")

mu_f1, cost_f1, vc_f = apply_gamma_312(
    mu=mu_fwd1, claim_id=root_fwd1, partition_key=pkey,
    payloads=make_payloads_312(bbox_fwd, N),
    beta=0.1, budget=1e9, spent=0.0,
    focal_point=fp_fwd, alpha_leak=0.1, beta_CA=0.3, mass_ref=2.0, kappa_ref=2.0,
)
mu_m1, cost_m1, vc_m = apply_gamma_312(
    mu=mu_mir1, claim_id=root_mir1, partition_key=pkey,
    payloads=make_payloads_312(bbox_mir, N),
    beta=0.1, budget=1e9, spent=0.0,
    focal_point=fp_mir, alpha_leak=0.1, beta_CA=0.3, mass_ref=2.0, kappa_ref=2.0,
)

# [6] G_t = 0
def check_G_zero(mu):
    Z = mu.Z()
    W = np.column_stack([mu.claims[cid].stalk for cid in mu.active])
    G = Z - W @ np.linalg.lstsq(W, Z, rcond=None)[0]
    return float(np.linalg.norm(G))

g_f = check_G_zero(mu_f1)
g_m = check_G_zero(mu_m1)
assert g_f < 1e-8, f"G_t != 0 fwd: {g_f:.2e}"
assert g_m < 1e-8, f"G_t != 0 mir: {g_m:.2e}"
print(f"[6] PASS  G_t=0 identity: fwd={g_f:.2e}, mir={g_m:.2e}")

log_f = getattr(mu_f1, "G_inject_log", [])
log_m = getattr(mu_m1, "G_inject_log", [])
gc_f = log_f[0][0] if log_f else None
gc_m = log_m[0][0] if log_m else None
ga_f = log_f[0][1] if log_f else None
ga_m = log_m[0][1] if log_m else None

assert gc_f is not None and gc_m is not None, "G_inject_log empty"
assert abs(gc_f - gc_m) < TOL, f"G_inject_C P_yz violation: {gc_f} vs {gc_m}"
print(f"[7] PASS  G_inject_C single-step P_yz-invariant: {gc_f:.8f} = {gc_m:.8f}")

assert abs(ga_f - ga_m) < TOL, f"G_inject_A P_yz violation: {ga_f} vs {ga_m}"
print(f"[8] PASS  G_inject_A single-step P_yz-invariant: {ga_f:.8f} = {ga_m:.8f}")

# [9] LOD value analytical
lod_f = lod_value(bbox_fwd, fp_fwd)
lod_m = lod_value(bbox_mir, fp_mir)
assert abs(lod_f - lod_m) < 1e-10, f"LOD P_yz violation: {lod_f} vs {lod_m}"
print(f"[9] PASS  LOD P_yz-invariant: {lod_f:.6e} = {lod_m:.6e}")

# [10] sorted kappa distribution
kappas_f = sorted([float(mu_f1.claims[cid].stalk[bK]) for cid in mu_f1.active])
kappas_m = sorted([float(mu_m1.claims[cid].stalk[bK]) for cid in mu_m1.active])
assert len(kappas_f) == len(kappas_m), f"kappa count mismatch"
max_kappa_delta = max(abs(a - b) for a, b in zip(kappas_f, kappas_m))
assert max_kappa_delta < 1e-8, f"sorted kappa P_yz violation: max_delta={max_kappa_delta:.2e}"
print(f"[10] PASS sorted kappa P_yz-invariant (N={len(kappas_f)}): max_delta={max_kappa_delta:.2e}")

# === Observables ===
Z_f = mu_f.Z(); Z_m = mu_m.Z()
print(f"  OBS: B_C_fwd={np.linalg.norm(S_C_f)/(np.linalg.norm(Z_f[8:12])+1e-15):.6f}"
      f"  B_C_mir={np.linalg.norm(S_C_m)/(np.linalg.norm(Z_m[8:12])+1e-15):.6f}")
print(f"  OBS: B_A_fwd={np.linalg.norm(S_A_f)/(np.linalg.norm(Z_f[0:8])+1e-15):.6f}"
      f"  B_A_mir={np.linalg.norm(S_A_m)/(np.linalg.norm(Z_m[0:8])+1e-15):.6f}")
print(f"  OBS: cost_fwd={cost_f:.4f}  cost_mir={cost_m:.4f}")

print(f"\nFork B: ALL TESTS PASSED")
print(f"  EXP-312 closes Asymmetry Debt: full multi-step P_yz invariance confirmed.")
print(f"  Fix 1: extents-based payload (_bbox_hash_payload_312)")
print(f"  Fix 2: uniform Sector A split (stalk_A_i = stalk_A / N)")
print(f"  fwd_leaves == mir_leaves == {fwd_leaves}")
