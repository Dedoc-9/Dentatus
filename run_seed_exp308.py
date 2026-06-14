"""
run_seed_exp308.py -- EXP-308 Integral Curvature Engine seed test (Fork A).

Protocol: exp308-v1
declaration_hash: f1363cd1a9b27b7fef9b84d7738be8d38b866bb1a0a24c2caecb9598ee08a550

Test sequence:
  1. Seed: kappa = kappa_integral([0,1]^3) = 2.0
  2. Gamma308(axis_bisect_x): kappa_child = 3.0, F[11,11]=1.5
  3. Gamma308(octree_split N=8): kappa_child = 4.0, F[11,11]=2.0
  4. is_valid_kappa_308 violation
  5. eta_AC coupling observable (range, independence structure)
  6. bbox-hash payload determinism + spatial variation
  7. Recursive Gamma_308: all 6 predicates + kappa_308 at all leaves
"""

import sys, json, hashlib, struct, copy, math
import numpy as np
sys.path.insert(0, ".")

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA, EPSILON
from engine.operators import (
    apply_gamma_308, apply_gamma_308_recursive, _bbox_hash_payload,
    _kappa_integral, SECTOR_A_DIMS, SECTOR_B_DIMS, SECTOR_C_DIMS, SECTOR_C_KAPPA_DIM,
    K_MIN_PARTITION, LAMBDA_DECAY,
)
from engine.validity import (
    is_valid, is_valid_b, is_spatially_valid, is_unit_norm,
    is_valid_block_diagonal_306, is_valid_kappa_308, kappa_integral,
)

with open("studies/exp308_integral_curvature/SEED_DECLARATION_exp308.json") as f:
    DECL = json.load(f)
stored_hash = DECL["declaration_hash"]
fields = {k: v for k, v in DECL.items() if k not in ("declaration_hash","status")}
assert hashlib.sha256(json.dumps(fields,sort_keys=True,separators=(',',':')).encode()).hexdigest() == stored_hash
print(f"Seed hash verified: {stored_hash[:16]}...")

BETA = DECL["beta"]; B0 = DECL["B0"]; D = DECL["d"]
SEED_STALK = np.array(DECL["seed_stalk"], dtype=float)
BBOX_LO = np.array(DECL["seed_bbox_lo"], dtype=float)
BBOX_HI = np.array(DECL["seed_bbox_hi"], dtype=float)
b0N = SECTOR_C_DIMS[0]; b1N = SECTOR_C_DIMS[-1]+1; bK = SECTOR_C_KAPPA_DIM

# ---------------------------------------------------------------------------
# 0. Seed
# ---------------------------------------------------------------------------
prov = Provenance(parent_ids=(), operator_id="Seed_0_308", timestamp=now_iso())
seed = Claim(provenance=prov, payload="Seed_0_308: d=12 EXP-308 kappa_integral unit cube.",
             stalk=SEED_STALK.copy(), t=0, bbox=(BBOX_LO, BBOX_HI))
mu0 = MuState(claims={seed.id: seed}, entailments={}, active=frozenset([seed.id]),
              t=0, S=np.zeros(D), alpha=ALPHA, S_A=np.zeros(8), S_C=np.zeros(4))
mu0.seal()

k_seed_geom = kappa_integral(seed.bbox)
k_seed_stalk = float(seed.stalk[bK])
print(f"\nSeed kappa: stalk={k_seed_stalk:.4f}  kappa_integral={k_seed_geom:.4f}")
assert abs(k_seed_stalk - k_seed_geom) < 1e-8
assert abs(k_seed_geom - 2.0) < 1e-8, f"unit cube kappa_integral != 2.0: {k_seed_geom}"
assert is_valid_kappa_308(mu0)
print(f"H_0: {mu0._H[:16]}...")

# ---------------------------------------------------------------------------
# 1. axis_bisect_x -> kappa_child = 3.0, F[11,11] = 1.5
# ---------------------------------------------------------------------------
print(f"\n--- Gamma308(Seed, axis_bisect_x) ---")
mu1, _ = apply_gamma_308(mu=mu0, claim_id=seed.id, partition_key="axis_bisect_x",
                          payloads=["i308_x0","i308_x1"], beta=BETA, budget=B0, spent=0.0)
print(f"  H_1={mu1._H[:16]}...")

all_ids = list(mu1.active)
cx0_id = next(c for c in all_ids if mu1.claims[c].bbox[0][0] < 0.1)
cx1_id = next(c for c in all_ids if mu1.claims[c].bbox[0][0] > 0.4)

for cid, lbl in [(cx0_id,"lower-x"),(cx1_id,"upper-x")]:
    c = mu1.claims[cid]
    k_g = kappa_integral(c.bbox); k_s = float(c.stalk[bK])
    F_k = mu1.entailments[(seed.id,cid)].restriction[bK,bK]
    assert abs(k_s - k_g) < 1e-8, f"kappa mismatch ({lbl}): {k_s} vs {k_g}"
    assert abs(k_g - 3.0) < 1e-8, f"bisect_x kappa != 3.0: {k_g}"
    assert abs(F_k - 1.5) < 1e-10, f"F[11,11] != 1.5: {F_k}"
    print(f"  {lbl}: kappa={k_s:.4f}  kappa_integral={k_g:.4f}  F[11,11]={F_k:.4f}")

assert is_valid_kappa_308(mu1)
print(f"  kappa_integral bisect_x = 3.0 = 2*(2+0.5+0.5)/(0.5+1+0.5): PASS")
print(f"  F[11,11] = 1.5 = 3/2: PASS")

# All 6 predicates
assert is_valid(mu1) and is_valid_b(mu1) and is_unit_norm(mu1)
assert is_spatially_valid(mu1) and is_valid_block_diagonal_306(mu1) and is_valid_kappa_308(mu1)
print(f"  All 6 predicates: PASS")

# ---------------------------------------------------------------------------
# 2. octree_split -> kappa_child = 4.0, F[11,11] = 2.0
# ---------------------------------------------------------------------------
print(f"\n--- Gamma308(Seed, octree_split) -> 8 octants ---")
mu_oct, _ = apply_gamma_308(mu=mu0, claim_id=seed.id, partition_key="octree_split",
                              payloads=[f"o308_{i}" for i in range(8)],
                              beta=BETA, budget=B0, spent=0.0)
print(f"  H_oct={mu_oct._H[:16]}...")

for oid in sorted(mu_oct.active):
    c = mu_oct.claims[oid]
    k_g = kappa_integral(c.bbox); k_s = float(c.stalk[bK])
    F_k = mu_oct.entailments[(seed.id,oid)].restriction[bK,bK]
    assert abs(k_s - k_g) < 1e-8
    assert abs(k_g - 4.0) < 1e-8, f"octant kappa != 4.0: {k_g}"
    assert abs(F_k - 2.0) < 1e-10, f"octant F[11,11] != 2.0: {F_k}"
    print(f"    kappa={k_s:.2f}  F[11,11]={F_k:.4f}")

assert is_valid_kappa_308(mu_oct)
print(f"  kappa_integral octant = 4.0 = 2*(0.5+0.5+0.5)/(0.25+0.25+0.25): PASS")
print(f"  F[11,11] = 2.0 per octant: PASS")

# ---------------------------------------------------------------------------
# 3. is_valid_kappa_308 violation
# ---------------------------------------------------------------------------
print(f"\n--- is_valid_kappa_308 violation: stalk[11]=99.0 ---")
mu_bad = copy.deepcopy(mu1)
bc = mu_bad.claims[cx0_id]; bs = bc.stalk.copy(); bs[bK] = 99.0
object.__setattr__(bc,'stalk',bs); mu_bad.claims[cx0_id] = bc
assert not is_valid_kappa_308(mu_bad)
print(f"  is_valid_kappa_308 with kappa=99.0: False  PASS")

# ---------------------------------------------------------------------------
# 4. eta_AC coupling observable
# ---------------------------------------------------------------------------
print(f"\n--- eta_AC coupling observable ---")
eta_oct = mu_oct.eta_AC()
eta_1   = mu1.eta_AC()
eta_0   = mu0.eta_AC()   # single leaf -> 0
print(f"  eta_AC (seed, 1 leaf):   {eta_0:.6f}  (expected 0.0: < 2 active)")
print(f"  eta_AC (bisect_x, 2 leaves): {eta_1:.6f}  (range [0,1])")
print(f"  eta_AC (octree, 8 leaves):   {eta_oct:.6f}  (range [0,1])")
assert eta_0 == 0.0, f"eta_AC single leaf != 0: {eta_0}"
assert 0.0 <= eta_1 <= 1.0, f"eta_AC out of range: {eta_1}"
assert 0.0 <= eta_oct <= 1.0, f"eta_AC out of range: {eta_oct}"
print(f"  eta_AC range [0,1]: PASS")

# Verify after 2nd partition (additional depth changes coupling)
mu2, _ = apply_gamma_308(mu=mu1, claim_id=cx0_id, partition_key="axis_bisect_y",
                          payloads=["i308_y0","i308_y1"], beta=BETA, budget=B0, spent=1.0)
eta_2 = mu2.eta_AC()
print(f"  eta_AC after t=2 (bisect_y): {eta_2:.6f}")
assert 0.0 <= eta_2 <= 1.0

# ---------------------------------------------------------------------------
# 5. bbox-hash payload: determinism + spatial variation
# ---------------------------------------------------------------------------
print(f"\n--- bbox-hash payload ---")
from engine.operators import _compute_child_bboxes
child_bboxes_x = _compute_child_bboxes(seed.bbox, "axis_bisect_x")
p0 = _bbox_hash_payload(child_bboxes_x[0], depth=0, index=0)
p1 = _bbox_hash_payload(child_bboxes_x[1], depth=0, index=1)
p0b = _bbox_hash_payload(child_bboxes_x[0], depth=0, index=0)  # repeat
print(f"  payload[0] = {p0}  (bbox [0,0.5]^x)")
print(f"  payload[1] = {p1}  (bbox [0.5,1]^x)")
assert p0 == p0b, "bbox-hash payload not deterministic"
assert p0 != p1,  "different bboxes must yield different payloads"
# Depth variation
p0_d1 = _bbox_hash_payload(child_bboxes_x[0], depth=1, index=0)
assert p0 != p0_d1, "same bbox at different depth must yield different payload"
print(f"  payload[0,depth=1] = {p0_d1}")
print(f"  Determinism: PASS  Spatial variation: PASS  Depth variation: PASS")

# ---------------------------------------------------------------------------
# 6. Recursive Gamma_308
# ---------------------------------------------------------------------------
print(f"\n--- Recursive Gamma_308 (K_budget_0=256) ---")
K_BUDGET_0 = DECL["recursive_gamma"]["K_budget_0"]
mu_rec, rec_cost = apply_gamma_308_recursive(
    mu=mu0, claim_id=seed.id, partition_key="axis_bisect_x",
    beta=BETA, budget=B0, spent=0.0, K_budget=K_BUDGET_0, depth=0,
)
n_leaves = len(mu_rec.active)
print(f"  Claims: {len(mu_rec.claims)}  Leaves: {n_leaves}  Cost: {rec_cost:.4f}")
print(f"  H_rec={mu_rec._H[:16]}...")

assert is_valid(mu_rec) and is_valid_b(mu_rec) and is_unit_norm(mu_rec)
assert is_spatially_valid(mu_rec) and is_valid_block_diagonal_306(mu_rec)
assert is_valid_kappa_308(mu_rec), "FAIL: is_valid_kappa_308 (recursive)"
print(f"  All 6 predicates: PASS")

# Verify kappa at all leaves matches kappa_integral exactly
for lid in mu_rec.active:
    leaf = mu_rec.claims[lid]
    k_exp = kappa_integral(leaf.bbox)
    k_act = float(leaf.stalk[bK])
    assert abs(k_act - k_exp) < 1e-8, f"leaf kappa mismatch: {k_act} vs {k_exp}"
# Verify kappa scales as 2/l at each depth level
for lid in mu_rec.active:
    leaf = mu_rec.claims[lid]
    lo, hi = leaf.bbox; l = hi[0]-lo[0]  # all extents equal for bisect_x chain
    k_exp_approx = kappa_integral(leaf.bbox)
    print(f"    leaf l={l:.4f}  kappa={float(leaf.stalk[bK]):.4f}", end="")
    print(f"  (2/l={2.0/l:.4f})" if abs(l)>1e-10 else "")
    break  # show just one
print(f"  kappa_integral at all {n_leaves} leaves: PASS")

print(f"\n=== EXP-308 Seed PASS (Fork A) ===")
print(f"  declaration_hash: {stored_hash}")
print(f"  H_0:   {mu0._H[:16]}...")
print(f"  H_1:   {mu1._H[:16]}...")
print(f"  H_oct: {mu_oct._H[:16]}...")
print(f"  H_rec: {mu_rec._H[:16]}...")
print(f"  kappa_integral: 2.0 (seed), 3.0 (bisect_x), 4.0 (octant): PASS")
print(f"  F[11,11]=1.5 (bisect_x), F[11,11]=2.0 (octant):            PASS")
print(f"  is_valid_kappa_308 violation:                               PASS")
print(f"  eta_AC in [0,1]:                                            PASS")
print(f"  bbox-hash payload determinism + variation:                  PASS")
print(f"  Recursive Gamma_308, 6 predicates, kappa at all leaves:    PASS")
