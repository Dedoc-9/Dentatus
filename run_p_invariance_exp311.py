"""
run_p_invariance_exp311.py - Fork B: EXP-311 P_yz Invariance Test

Protocol: exp311-v1
declaration_hash: 10659ed4d37c027aed4144fd847c3e35986e49e45be596c9cc77b6806d040f35

DEV NOTE (pre-existing constraint):
  Multi-step recursion leaf counts are NOT P_yz-invariant because K_bound =
  len(zlib.compress(payload)) encodes absolute bbox coordinates (not extents).
  P_yz negates x-coords -> different payload bytes -> different K_bound ->
  different budget consumption -> different recursion depth.
  This is a pre-existing architectural property of EXP-308/309 operators.

Tests in this fork use SINGLE-STEP analysis and per-step invariants that
are provably invariant regardless of tree structure:

  1. G_t = 0 identity: both orientations (structural result, depth-independent)
  2. G_inject_C[3] single-step P_yz invariance:
       f(||Z[0:4]||) where ||Z[0:4]|| = Sector A norm = P_yz-invariant
  3. G_inject_A[7] single-step P_yz invariance:
       f(Z[11]) where Z[11]=kappa_integral(bbox) = P_yz-invariant
  4. norm(S_C), norm(S_A) after ONE partition: P_yz-invariant (same G_inject)
  5. LOD value invariance (analytical, from validity module)
  6. Sorted kappa distribution after single partition (8 octants)
"""

import sys, os, json, hashlib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_311, SECTOR_C_KAPPA_DIM, SPATIAL_KEYS, _compute_child_bboxes,
    _bbox_hash_payload,
)
from engine.validity import kappa_integral, lod_value

# === Declaration hash check ===
DECL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "studies/exp311_asymmetric_injection/SEED_DECLARATION_exp311.json",
)
EXPECTED_HASH = "10659ed4d37c027aed4144fd847c3e35986e49e45be596c9cc77b6806d040f35"
with open(DECL_PATH) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
canon = json.dumps(decl, sort_keys=True, separators=(",", ":"))
computed = hashlib.sha256(canon.encode()).hexdigest()
assert stored == EXPECTED_HASH
assert computed == EXPECTED_HASH
print(f"[hash] PASS  {EXPECTED_HASH[:16]}...")

D = 12
bK = SECTOR_C_KAPPA_DIM

# === P_yz transforms ===
def apply_p_yz_stalk(s):
    s = s.copy(); s[4] = -s[4]; s[8] = -s[8]; return s

def apply_p_yz_bbox(bbox):
    lo, hi = bbox[0].copy(), bbox[1].copy()
    lo[0], hi[0] = -bbox[1][0], -bbox[0][0]
    return (lo, hi)

def apply_p_yz_focal(fp):
    f = fp.copy(); f[0] = -f[0]; return f

# === Build seed pair ===
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
    claim = Claim(provenance=prov, payload=f"{label}: d=12 EXP-311", stalk=stalk.copy(), t=0, bbox=bbox)
    mu = MuState(t=0, claims={claim.id: claim}, entailments={}, active=frozenset([claim.id]),
                 S=np.zeros(D), alpha=ALPHA, S_A=np.zeros(8), S_C=np.zeros(4))
    mu.seal()
    return mu, claim.id

mu_fwd, root_fwd = make_mu(seed_stalk, bbox_fwd, "fwd")
mu_mir, root_mir = make_mu(seed_stalk_mir, bbox_mir, "mir")

# === ONE-STEP apply_gamma_311 for each orientation ===
N = SPATIAL_KEYS["octree_split"]
pkey = "octree_split"

def make_payloads(bbox, n):
    children = _compute_child_bboxes(bbox, pkey)
    return [_bbox_hash_payload(children[i], 0, i) for i in range(n)]

mu_f1, cost_f, vc_f = apply_gamma_311(
    mu=mu_fwd, claim_id=root_fwd, partition_key=pkey,
    payloads=make_payloads(bbox_fwd, N),
    beta=0.1, budget=1e9, spent=0.0,
    focal_point=fp_fwd, alpha_leak=0.1, beta_CA=0.3, mass_ref=2.0, kappa_ref=2.0,
)
mu_m1, cost_m, vc_m = apply_gamma_311(
    mu=mu_mir, claim_id=root_mir, partition_key=pkey,
    payloads=make_payloads(bbox_mir, N),
    beta=0.1, budget=1e9, spent=0.0,
    focal_point=fp_mir, alpha_leak=0.1, beta_CA=0.3, mass_ref=2.0, kappa_ref=2.0,
)

S_C_f = mu_f1.S_C if mu_f1.S_C is not None else np.zeros(4)
S_C_m = mu_m1.S_C if mu_m1.S_C is not None else np.zeros(4)
S_A_f = mu_f1.S_A if mu_f1.S_A is not None else np.zeros(8)
S_A_m = mu_m1.S_A if mu_m1.S_A is not None else np.zeros(8)

log_f = getattr(mu_f1, "G_inject_log", [])
log_m = getattr(mu_m1, "G_inject_log", [])
gc_f = log_f[0][0] if log_f else None
gc_m = log_m[0][0] if log_m else None
ga_f = log_f[0][1] if log_f else None
ga_m = log_m[0][1] if log_m else None

print(f"  fwd: vc={vc_f}  norm(S_C)={np.linalg.norm(S_C_f):.8f}  norm(S_A)={np.linalg.norm(S_A_f):.8f}")
print(f"       G_inject_C={gc_f:.8f}  G_inject_A={ga_f:.8f}")
print(f"  mir: vc={vc_m}  norm(S_C)={np.linalg.norm(S_C_m):.8f}  norm(S_A)={np.linalg.norm(S_A_m):.8f}")
print(f"       G_inject_C={gc_m:.8f}  G_inject_A={ga_m:.8f}")

TOL = 1e-8

# [1] G_t = 0 both orientations
def check_G_zero(mu, label):
    Z = mu.Z()
    W = np.column_stack([mu.claims[cid].stalk for cid in mu.active])
    G = Z - W @ np.linalg.lstsq(W, Z, rcond=None)[0]
    return float(np.linalg.norm(G))
g_f = check_G_zero(mu_f1, "fwd")
g_m = check_G_zero(mu_m1, "mir")
assert g_f < 1e-8, f"G_t != 0 fwd: {g_f:.2e}"
assert g_m < 1e-8, f"G_t != 0 mir: {g_m:.2e}"
print(f"[1] PASS  G_t=0 identity: fwd={g_f:.2e}, mir={g_m:.2e}")

# [2] G_inject_C P_yz invariance (single step)
assert gc_f is not None and gc_m is not None, "G_inject_log empty"
assert abs(gc_f - gc_m) < TOL, f"G_inject_C P_yz violation: {gc_f} vs {gc_m}"
print(f"[2] PASS  G_inject_C single-step P_yz invariant: {gc_f:.8f} = {gc_m:.8f}")

# [3] G_inject_A P_yz invariance (single step)
assert abs(ga_f - ga_m) < TOL, f"G_inject_A P_yz violation: {ga_f} vs {ga_m}"
print(f"[3] PASS  G_inject_A single-step P_yz invariant: {ga_f:.8f} = {ga_m:.8f}")

# [4] norm(S_C), norm(S_A) after ONE partition
delta_SC = abs(float(np.linalg.norm(S_C_f)) - float(np.linalg.norm(S_C_m)))
delta_SA = abs(float(np.linalg.norm(S_A_f)) - float(np.linalg.norm(S_A_m)))
assert delta_SC < TOL, f"norm(S_C) P_yz violation (1-step): delta={delta_SC:.2e}"
assert delta_SA < TOL, f"norm(S_A) P_yz violation (1-step): delta={delta_SA:.2e}"
print(f"[4] PASS  norm(S_C) 1-step P_yz invariant: delta={delta_SC:.2e}")
print(f"          norm(S_A) 1-step P_yz invariant: delta={delta_SA:.2e}")

# [5] LOD value invariance (analytical)
lo_f, hi_f = bbox_fwd
lo_m, hi_m = bbox_mir
lod_f = lod_value(bbox_fwd, fp_fwd)
lod_m = lod_value(bbox_mir, fp_mir)
assert abs(lod_f - lod_m) < 1e-10, f"LOD P_yz violation: {lod_f} vs {lod_m}"
print(f"[5] PASS  LOD P_yz invariant: {lod_f:.6e} = {lod_m:.6e}")

# [6] Sorted kappa distribution after one partition
kappas_f = sorted([float(mu_f1.claims[cid].stalk[bK]) for cid in mu_f1.active])
kappas_m = sorted([float(mu_m1.claims[cid].stalk[bK]) for cid in mu_m1.active])
assert len(kappas_f) == len(kappas_m), f"Kappa count mismatch: {len(kappas_f)} vs {len(kappas_m)}"
max_kappa_delta = max(abs(a - b) for a, b in zip(kappas_f, kappas_m))
assert max_kappa_delta < 1e-8, f"Sorted kappa P_yz violation: max_delta={max_kappa_delta:.2e}"
print(f"[6] PASS  sorted kappa P_yz invariant (N={len(kappas_f)}): max_delta={max_kappa_delta:.2e}")

# === Observables ===
print(f"  OBS: validity_class fwd={vc_f}  mir={vc_m}")
print(f"  OBS: cost_fwd={cost_f:.2f}  cost_mir={cost_m:.2f}")

print(f"\nFork B: ALL TESTS PASSED (single-step P_yz invariance confirmed)")
print(f"  DEV NOTE: Multi-step leaf-count P_yz invariance deferred (pre-existing K_bound")
print(f"    absolute-coord encoding issue; scope EXP-312+ or standalone K_bound patch).")
