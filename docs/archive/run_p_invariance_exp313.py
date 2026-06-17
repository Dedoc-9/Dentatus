"""
run_p_invariance_exp313.py - Fork B: EXP-313 Zeeman P_yz Covariance Test

Protocol: exp313-v1
declaration_hash: 2431d09f38554a9b8d57c45ffea29a1e48fa63f5dc3701bcc53ecb515f011efd

PRIMARY ASSERTION (EXP-313 upgrade over EXP-312):
  K_fwd[i] == K_mir[i XOR 4] for all i in {0..7}
  Budget allocated to spatial position is P_yz-covariant.
  B transforms as a polar vector: B_mir = P_yz(B_fwd) = (-B_x, B_y, B_z).

Proof: centroid_mir[i^4] . B_mir
       = P_yz(centroid_fwd[i]) . P_yz(B)
       = centroid_fwd[i] . B    (dot product O(3)-invariant)
       => w_fwd[i] == w_mir[i^4] => K_fwd[i] == K_mir[i^4]  QED

Tests:
  [1]  declaration hash
  [2]  K_fwd[i] == K_mir[i XOR 4] for all i (budget covariance, delta < 1e-10)
  [3]  fwd_leaves == mir_leaves (full multi-step P_yz)
  [4]  cost_fwd == cost_mir
  [5]  norm(S_C) P_yz-invariant
  [6]  norm(S_A) P_yz-invariant
  [7]  G_t = 0 identity
  [8]  G_inject_C single-step invariant
  [9]  G_inject_A single-step invariant
"""

import sys, os, json, hashlib, math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_313, apply_gamma_313_recursive,
    _zeeman_weights, _compute_child_bboxes,
    _bbox_hash_payload_312, SPATIAL_KEYS, SECTOR_C_KAPPA_DIM,
)
from engine.validity import kappa_integral

DECL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "studies/exp313_zeeman_kbound/SEED_DECLARATION_exp313.json",
)
EXPECTED_HASH = "2431d09f38554a9b8d57c45ffea29a1e48fa63f5dc3701bcc53ecb515f011efd"
with open(DECL_PATH) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
canon = json.dumps(decl, sort_keys=True, separators=(",", ":"))
computed = hashlib.sha256(canon.encode()).hexdigest()
assert stored == EXPECTED_HASH and computed == EXPECTED_HASH
print(f"[1] PASS  declaration_hash = {EXPECTED_HASH[:16]}...")

D = 12; bK = SECTOR_C_KAPPA_DIM
B_FWD = np.array([1.0, 0.5, 0.3])
BETA_Z = 2.0
N = SPATIAL_KEYS["octree_split"]
LAMBDA_DECAY = 0.1
K_BUDGET = 2048.0

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
seed_stalk = np.array([1.,1.,1.,1., 0.5,0.5,0.5,1., 0.6,0.,0.8, kappa_seed])
bbox_fwd = (np.zeros(3), np.ones(3))
bbox_mir = p_yz_bbox(bbox_fwd)
seed_stalk_mir = p_yz_stalk(seed_stalk)
seed_stalk_mir[bK] = kappa_integral(bbox_mir)
fp_fwd = np.array([0.5, 0.5, 0.5])
fp_mir = p_yz_focal(fp_fwd)

def make_mu(stalk, bbox, label):
    prov = Provenance(parent_ids=(), operator_id=f"seed_{label}", timestamp=now_iso())
    claim = Claim(provenance=prov, payload=f"{label}: d=12 EXP-313",
                  stalk=stalk.copy(), t=0, bbox=bbox)
    mu = MuState(t=0, claims={claim.id: claim}, entailments={},
                 active=frozenset([claim.id]),
                 S=np.zeros(D), alpha=ALPHA, S_A=np.zeros(8), S_C=np.zeros(4))
    mu.seal()
    return mu, claim.id

# ============================================================
# [2] Budget covariance: K_fwd[i] == K_mir[i XOR 4]
# ============================================================
child_bboxes_fwd = _compute_child_bboxes(bbox_fwd, "octree_split")
child_bboxes_mir = _compute_child_bboxes(bbox_mir, "octree_split")

w_fwd = _zeeman_weights(child_bboxes_fwd, B_FWD, BETA_Z)
w_mir = _zeeman_weights(child_bboxes_mir, B_MIR, BETA_Z)

K_fwd = K_BUDGET * w_fwd * math.exp(-LAMBDA_DECAY)
K_mir = K_BUDGET * w_mir * math.exp(-LAMBDA_DECAY)

print("  Zeeman K budget (fwd vs mir[i^4]):")
max_delta = 0.0
for i in range(N):
    j = i ^ 4
    delta = abs(float(K_fwd[i]) - float(K_mir[j]))
    max_delta = max(max_delta, delta)
    print(f"    K_fwd[{i}]={K_fwd[i]:.6f}  K_mir[{j}]={K_mir[j]:.6f}  delta={delta:.2e}")

assert max_delta < 1e-10, f"K budget covariance violation: max_delta={max_delta:.2e}"
print(f"[2] PASS  K_fwd[i] == K_mir[i XOR 4] for all i: max_delta={max_delta:.2e}")

# ============================================================
# [3],[4],[5],[6] -- multi-step recursive runs
# ============================================================
mu_fwd0, root_fwd = make_mu(seed_stalk, bbox_fwd, "fwd")
mu_mir0, root_mir = make_mu(seed_stalk_mir, bbox_mir, "mir")

mu_f, cost_f, _ = apply_gamma_313_recursive(
    mu=mu_fwd0, claim_id=root_fwd, partition_key="octree_split",
    beta=1.0, budget=1e9, spent=0.0, K_budget=K_BUDGET, depth=0,
    focal_point=fp_fwd, B=B_FWD, beta_Z=BETA_Z,
    alpha_leak=0.1, beta_CA=0.3, mass_ref=2.0, kappa_ref=2.0,
)
mu_m, cost_m, _ = apply_gamma_313_recursive(
    mu=mu_mir0, claim_id=root_mir, partition_key="octree_split",
    beta=1.0, budget=1e9, spent=0.0, K_budget=K_BUDGET, depth=0,
    focal_point=fp_mir, B=B_MIR, beta_Z=BETA_Z,
    alpha_leak=0.1, beta_CA=0.3, mass_ref=2.0, kappa_ref=2.0,
)

fwd_l = len(mu_f.active); mir_l = len(mu_m.active)
print(f"  fwd_leaves={fwd_l}  mir_leaves={mir_l}")
assert fwd_l == mir_l, f"leaf count P_yz violation: {fwd_l} != {mir_l}"
print(f"[3] PASS  fwd_leaves == mir_leaves == {fwd_l}")

delta_cost = abs(cost_f - cost_m)
assert delta_cost < 1e-8, f"cost P_yz violation: delta={delta_cost:.2e}"
print(f"[4] PASS  cost P_yz-invariant: {cost_f:.6f} = {cost_m:.6f}")

S_C_f = mu_f.S_C if mu_f.S_C is not None else np.zeros(4)
S_C_m = mu_m.S_C if mu_m.S_C is not None else np.zeros(4)
S_A_f = mu_f.S_A if mu_f.S_A is not None else np.zeros(8)
S_A_m = mu_m.S_A if mu_m.S_A is not None else np.zeros(8)

d_SC = abs(float(np.linalg.norm(S_C_f)) - float(np.linalg.norm(S_C_m)))
assert d_SC < 1e-8, f"norm(S_C) P_yz violation: delta={d_SC:.2e}"
print(f"[5] PASS  norm(S_C) P_yz-invariant: {np.linalg.norm(S_C_f):.8f} = {np.linalg.norm(S_C_m):.8f}")

d_SA = abs(float(np.linalg.norm(S_A_f)) - float(np.linalg.norm(S_A_m)))
assert d_SA < 1e-8, f"norm(S_A) P_yz violation: delta={d_SA:.2e}"
print(f"[6] PASS  norm(S_A) P_yz-invariant: {np.linalg.norm(S_A_f):.8f} = {np.linalg.norm(S_A_m):.8f}")

# ============================================================
# [7],[8],[9] -- single-step
# ============================================================
mu_fwd1, root_fwd1 = make_mu(seed_stalk, bbox_fwd, "fwd1")
mu_mir1, root_mir1 = make_mu(seed_stalk_mir, bbox_mir, "mir1")

payloads_fwd = [_bbox_hash_payload_312(child_bboxes_fwd[i], 0, i) for i in range(N)]
payloads_mir = [_bbox_hash_payload_312(child_bboxes_mir[i], 0, i) for i in range(N)]

mu_f1, _, vc_f = apply_gamma_313(
    mu=mu_fwd1, claim_id=root_fwd1, partition_key="octree_split",
    payloads=payloads_fwd, beta=0.1, budget=1e9, spent=0.0,
    focal_point=fp_fwd, B=B_FWD, beta_Z=BETA_Z,
    alpha_leak=0.1, beta_CA=0.3, mass_ref=2.0, kappa_ref=2.0,
)
mu_m1, _, vc_m = apply_gamma_313(
    mu=mu_mir1, claim_id=root_mir1, partition_key="octree_split",
    payloads=payloads_mir, beta=0.1, budget=1e9, spent=0.0,
    focal_point=fp_mir, B=B_MIR, beta_Z=BETA_Z,
    alpha_leak=0.1, beta_CA=0.3, mass_ref=2.0, kappa_ref=2.0,
)

def check_G_zero(mu):
    Z = mu.Z()
    W = np.column_stack([mu.claims[cid].stalk for cid in mu.active])
    return float(np.linalg.norm(Z - W @ np.linalg.lstsq(W, Z, rcond=None)[0]))

g_f = check_G_zero(mu_f1); g_m = check_G_zero(mu_m1)
assert g_f < 1e-8 and g_m < 1e-8
print(f"[7] PASS  G_t=0 identity: fwd={g_f:.2e}  mir={g_m:.2e}")

log_f = getattr(mu_f1, "G_inject_log", [])
log_m = getattr(mu_m1, "G_inject_log", [])
gc_f, ga_f = log_f[0]
gc_m, ga_m = log_m[0]
assert abs(gc_f - gc_m) < 1e-8
print(f"[8] PASS  G_inject_C P_yz-invariant: {gc_f:.8f} = {gc_m:.8f}")
assert abs(ga_f - ga_m) < 1e-8
print(f"[9] PASS  G_inject_A P_yz-invariant: {ga_f:.8f} = {ga_m:.8f}")

# Observables
print(f"  OBS: K_ratio={float(w_fwd.max()/w_fwd.min()):.4f}")
print(f"  OBS: B_fwd={B_FWD}  B_mir={B_MIR}")
print(f"  OBS: K_align_fwd=octant_{int(np.argmax(w_fwd))}  K_align_mir=octant_{int(np.argmax(w_mir))}")
print(f"  OBS: cost_fwd={cost_f:.4f}  cost_mir={cost_m:.4f}")

print(f"\nFork B: ALL TESTS PASSED")
print(f"  EXP-313: Zeeman K_budget covariance confirmed.")
print(f"  K_fwd[i] == K_mir[i XOR 4] for all i. fwd_leaves == mir_leaves == {fwd_l}.")
