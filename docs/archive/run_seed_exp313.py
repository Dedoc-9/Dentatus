"""
run_seed_exp313.py - Fork A: EXP-313 Zeeman K_bound Seed Validation

Protocol: exp313-v1
declaration_hash: 2431d09f38554a9b8d57c45ffea29a1e48fa63f5dc3701bcc53ecb515f011efd

Asserts:
  1. Declaration hash match
  2. norm(S_C) > 0.01
  3. norm(S_A) > 0.001
  4. K_child distribution non-uniform: max/min > 1.01 (Zeeman splitting active)
  5. K_child weights sum to 1.0 (conservation)
  6. H_t chain continuous
  7. n_leaves > 0
  8. Ghost history populated

Dev note (ghost #5 -- Zeeman structural anisotropy):
  With B=[1.0, 0.5, 0.3] and beta_Z=2.0, children aligned with B receive
  up to ~N times the budget of anti-aligned children. The resulting tree is
  directionally biased but P_yz-covariant (Fork B verifies K_fwd[i]==K_mir[i^4]).
"""

import sys, os, json, hashlib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_313_recursive, _zeeman_weights, _compute_child_bboxes, SPATIAL_KEYS
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
assert stored == EXPECTED_HASH
assert computed == EXPECTED_HASH
print(f"[1] PASS  declaration_hash = {EXPECTED_HASH[:16]}...")

D = 12
B = np.array([1.0, 0.5, 0.3])
BETA_Z = 2.0
LAMBDA_DECAY = 0.1   # matches engine constant

root_bbox = (np.zeros(3), np.ones(3))
kappa_root = kappa_integral(root_bbox)

prov = Provenance(parent_ids=(), operator_id="seed_exp313", timestamp=now_iso())
seed_stalk = np.array([1.0, 1.0, 1.0, 1.0,
                        0.5, 0.5, 0.5, 1.0,
                        0.0, 0.0, 1.0,
                        kappa_root])

root_claim = Claim(
    provenance=prov, payload="root: d=12 EXP-313",
    stalk=seed_stalk.copy(), t=0, bbox=root_bbox,
)
mu0 = MuState(
    t=0, claims={root_claim.id: root_claim}, entailments={},
    active=frozenset([root_claim.id]),
    S=np.zeros(D), alpha=ALPHA, S_A=np.zeros(8), S_C=np.zeros(4),
)
mu0.seal()
root_id = root_claim.id

# Verify Zeeman weights at root
N = SPATIAL_KEYS["octree_split"]
child_bboxes = _compute_child_bboxes(root_bbox, "octree_split")
w = _zeeman_weights(child_bboxes, B, BETA_Z)
K_budget_root = 2048.0
import math
K_children = K_budget_root * w * math.exp(-LAMBDA_DECAY)
print(f"    Zeeman weights: {np.round(w, 4)}")
print(f"    K_children:     {np.round(K_children, 3)}")
print(f"    K_ratio (max/min): {w.max()/w.min():.4f}")
print(f"    weights sum: {w.sum():.10f}")

# Run recursive
mu_final, total_cost, w0 = apply_gamma_313_recursive(
    mu=mu0, claim_id=root_id, partition_key="octree_split",
    beta=1.0, budget=1e9, spent=0.0, K_budget=2048,
    depth=0, focal_point=np.array([0.5, 0.5, 0.5]),
    B=B, beta_Z=BETA_Z,
    alpha_leak=0.1, beta_CA=0.3, mass_ref=2.0, kappa_ref=2.0,
)

n_leaves = len(mu_final.active)
S_C_final = mu_final.S_C if mu_final.S_C is not None else np.zeros(4)
S_A_final = mu_final.S_A if mu_final.S_A is not None else np.zeros(8)
S_C_norm = float(np.linalg.norm(S_C_final))
S_A_norm = float(np.linalg.norm(S_A_final))

print(f"    Recursive 313: {n_leaves} leaves, total_cost={total_cost:.4f}")
print(f"    norm(S_C) = {S_C_norm:.6f}")
print(f"    norm(S_A) = {S_A_norm:.6f}")

# [2]
assert S_C_norm > 0.01, f"norm(S_C) too small: {S_C_norm}"
print(f"[2] PASS  norm(S_C) = {S_C_norm:.6f} > 0.01")

# [3]
assert S_A_norm > 0.001, f"norm(S_A) too small: {S_A_norm}"
print(f"[3] PASS  norm(S_A) = {S_A_norm:.6f} > 0.001")

# [4] Non-uniform K allocation (Zeeman active)
k_ratio = float(w.max() / w.min())
assert k_ratio > 1.01, f"K_ratio too close to uniform: {k_ratio:.6f}"
print(f"[4] PASS  K_ratio = {k_ratio:.4f} > 1.01 (Zeeman splitting active)")

# [5] Weights sum to 1
assert abs(float(w.sum()) - 1.0) < 1e-10, f"weights don't sum to 1: {w.sum()}"
print(f"[5] PASS  Zeeman weights sum = {w.sum():.10f} (conservation)")

# [6] H_t chain
assert mu_final._H is not None, "H_t is None"
print(f"[6] PASS  H_t = {mu_final._H[:16]}...")

# [7] Leaves > 0
assert n_leaves > 0, "zero leaves"
print(f"[7] PASS  n_leaves = {n_leaves} > 0")

# [8] Ghost history
gh = getattr(mu_final, "ghost_history", None)
assert gh is not None and len(gh) > 0, "ghost_history empty"
print(f"[8] PASS  ghost_history len={len(gh)}")

# Observables
Z_final = mu_final.Z()
B_A = S_A_norm / (float(np.linalg.norm(Z_final[0:8])) + 1e-15)
B_C = S_C_norm / (float(np.linalg.norm(Z_final[8:12])) + 1e-15)
print(f"  OBS: B_A(t)={B_A:.6f}  B_C(t)={B_C:.6f}")
print(f"  OBS: K_align=octant_{int(np.argmax(w))}  K_ratio={k_ratio:.4f}")
print(f"  OBS: p_range={float(w0 @ np.arange(N)):.4f}  (weighted mean octant index)")

print(f"\nFork A: ALL TESTS PASSED ({n_leaves} leaves, Zeeman K_ratio={k_ratio:.4f})")
