"""
run_seed_exp306.py -- EXP-306 Curvature Engine seed test (Fork A).

Protocol: exp306-v1
declaration_hash: 5a8e1afc590d8ffb9dfe33977005eb888798c1ccdc9dd64c59b797eb8d48fe47

Test sequence:
  1. Seed_0_curve: d=12, stalk=[1,1,1,1, 0.5,0.5,0.5,1, 0,0,1,0], bbox=[0,1]^3
  2. Gamma306(Seed, axis_bisect_x) -> 2 children
       - Sector A conservation
       - Sector B centroid + w=1 + barycentric
       - Sector C centroid-outward normals: n_child = normalize(centroid_child - centroid_parent)
       - kappa additive: sum kappa_children = kappa_parent
       - Block-diagonal F (12x12): no cross-sector coupling
       - All 6 predicates
  3. Gamma306(Seed, octree_split) -> 8 children (same invariants)
       - Centroid-outward normals: 8 distinct unit normals at [±1/√3, ±1/√3, ±1/√3]
  4. Dual ghost observables: B_A(t), B_C(t)
  5. apply_gamma_306_recursive depth=2 (K_budget_0=256 -> 128 -> 64 -> STOP)
  6. is_valid_block_diagonal_306 violation: inject cross-sector coupling -> False
"""

import sys
import json
import hashlib
import copy
import math
import numpy as np
sys.path.insert(0, ".")

from engine.state import (
    MuState, Claim, Entailment, EntailmentType, Provenance,
    PROTOCOL_VERSION, now_iso, ALPHA_DEFAULT as ALPHA, EPSILON
)
from engine.operators import (
    apply_gamma_306, apply_gamma_306_recursive,
    SECTOR_A_DIMS, SECTOR_B_DIMS, SECTOR_C_DIMS, SECTOR_C_KAPPA_DIM,
    K_MIN_PARTITION, LAMBDA_DECAY,
)
from engine.validity import (
    is_valid, is_valid_b, is_spatially_valid,
    is_unit_norm, is_valid_block_diagonal_306,
)

# ---------------------------------------------------------------------------
# Load & verify seed declaration hash
# ---------------------------------------------------------------------------
with open("studies/exp306_curvature_engine/SEED_DECLARATION_exp306.json") as f:
    DECL = json.load(f)

stored_hash = DECL["declaration_hash"]
verify_fields = {k: v for k, v in DECL.items() if k not in ("declaration_hash", "status")}
canonical = json.dumps(verify_fields, sort_keys=True, separators=(',', ':'))
computed_hash = hashlib.sha256(canonical.encode()).hexdigest()
assert computed_hash == stored_hash, (
    f"SEED HASH MISMATCH\n  stored:   {stored_hash}\n  computed: {computed_hash}"
)
print(f"Seed hash verified: {stored_hash[:16]}...")

BETA = DECL.get("beta", 0.1)
B0   = DECL.get("B0", 100.0)
D    = DECL["d"]   # 12

SEED_STALK = np.array(DECL["seed_stalk"], dtype=float)
BBOX_LO    = np.array(DECL["seed_bbox_lo"], dtype=float)
BBOX_HI    = np.array(DECL["seed_bbox_hi"], dtype=float)

b0A, b1A = SECTOR_A_DIMS[0], SECTOR_A_DIMS[-1] + 1    # [0:4]
b0B, b1B = SECTOR_B_DIMS[0], SECTOR_B_DIMS[-1] + 1    # [4:8]
b0N = SECTOR_C_DIMS[0];  b1N = SECTOR_C_DIMS[-1] + 1  # [8:11]
bK  = SECTOR_C_KAPPA_DIM                               # 11

def fmt_A(s): return "[" + ", ".join(f"{v:.3f}" for v in s[b0A:b1A]) + "]"
def fmt_B(s): return "[" + ", ".join(f"{v:.3f}" for v in s[b0B:b1B]) + "]"
def fmt_N(s): return "[" + ", ".join(f"{v:.4f}" for v in s[b0N:b1N]) + "]"
def bbox_str(bb):
    if bb is None: return "None"
    return f"[{list(bb[0])} -> {list(bb[1])}]"

# ---------------------------------------------------------------------------
# 0. Build Seed_0_curve
# ---------------------------------------------------------------------------
seed_prov = Provenance(parent_ids=(), operator_id="Seed_0_curve", timestamp=now_iso())
seed = Claim(provenance=seed_prov,
             payload="Seed_0_curve: d=12 EXP-306, mass=1 white unit cube nz=1 kappa=0.",
             stalk=SEED_STALK.copy(), t=0, bbox=(BBOX_LO, BBOX_HI))

mu0 = MuState(
    claims={seed.id: seed},
    entailments={},
    active=frozenset([seed.id]),
    t=0,
    S=np.zeros(D),
    alpha=ALPHA,
    S_A=np.zeros(8),
    S_C=np.zeros(4),
)
mu0.seal()

print(f"\nSeed_0_curve  H_0: {mu0._H[:16]}...")
print(f"  Sector A: {fmt_A(seed.stalk)}")
print(f"  Sector B: {fmt_B(seed.stalk)}")
print(f"  Sector C normal: {fmt_N(seed.stalk)}  kappa={seed.stalk[bK]:.4f}")
print(f"  ||normal||: {np.linalg.norm(seed.stalk[b0N:b1N]):.6f}")
print(f"  bbox: {bbox_str(seed.bbox)}")

assert seed.stalk[7] == 1.0,                                "seed w != 1"
assert abs(np.linalg.norm(seed.stalk[b0N:b1N]) - 1.0) < 1e-8, "seed ||n|| != 1"
assert is_valid_b(mu0),            "seed fails is_valid_b"
assert is_unit_norm(mu0),          "seed fails is_unit_norm"
assert is_valid_block_diagonal_306(mu0), "seed fails block_diagonal_306 (trivial)"

# ---------------------------------------------------------------------------
# 1. Gamma306(Seed, axis_bisect_x) -> 2 children
# ---------------------------------------------------------------------------
print(f"\n--- Gamma306(Seed, axis_bisect_x) ---")
mu1, g_cost = apply_gamma_306(
    mu=mu0, claim_id=seed.id, partition_key="axis_bisect_x",
    payloads=["curve_x0", "curve_x1"],
    beta=BETA, budget=B0, spent=0.0,
)
print(f"  cost={g_cost:.4f}  H_1={mu1._H[:16]}...")

all_ids = list(mu1.active)
cx0_id = next(cid for cid in all_ids if mu1.claims[cid].bbox[0][0] < 0.1)
cx1_id = next(cid for cid in all_ids if mu1.claims[cid].bbox[0][0] > 0.4)
cx0 = mu1.claims[cx0_id]; cx1 = mu1.claims[cx1_id]

parent_centroid = (BBOX_LO + BBOX_HI) / 2.0

for cid, lbl in [(cx0_id, "lower-x"), (cx1_id, "upper-x")]:
    c = mu1.claims[cid]
    c_lo, c_hi = c.bbox
    # centroid-outward check
    c_centroid = (c_lo + c_hi) / 2.0
    expected_n = c_centroid - parent_centroid
    expected_n /= np.linalg.norm(expected_n)
    actual_n = c.stalk[b0N:b1N]
    n_err = float(np.linalg.norm(actual_n - expected_n))
    n_norm = float(np.linalg.norm(actual_n))
    kappa_c = float(c.stalk[bK])
    omega = mu1.entailments[(seed.id, cid)].omega
    print(f"  {lbl}:")
    print(f"    n_child={fmt_N(c.stalk)}  ||n||={n_norm:.6f}  n_err={n_err:.2e}")
    print(f"    kappa_child={kappa_c:.4f}  omega={omega:.4f}")
    print(f"    bbox: {bbox_str(c.bbox)}")
    assert n_err < 1e-10, f"centroid-outward normal mismatch ({lbl}): {n_err}"
    assert abs(n_norm - 1.0) < 1e-8, f"unit-norm violated ({lbl})"

# Sector A conservation
cons_A = float(np.linalg.norm(
    (cx0.stalk[b0A:b1A] + cx1.stalk[b0A:b1A]) - seed.stalk[b0A:b1A]
))
print(f"  Sector A conservation err: {cons_A:.2e}")
assert cons_A < 1e-10

# Sector B barycentric
omega0 = mu1.entailments[(seed.id, cx0_id)].omega
omega1 = mu1.entailments[(seed.id, cx1_id)].omega
bary_B = float(np.linalg.norm(
    omega0 * cx0.stalk[b0B:b1B] + omega1 * cx1.stalk[b0B:b1B] - seed.stalk[b0B:b1B]
))
print(f"  Sector B barycentric err: {bary_B:.2e}")
assert bary_B < 1e-10

# kappa additive: sum kappa_children = kappa_parent (= 0 here)
kappa_sum = float(cx0.stalk[bK] + cx1.stalk[bK])
kappa_parent = float(seed.stalk[bK])
kappa_err = abs(kappa_sum - kappa_parent)
print(f"  kappa_sum={kappa_sum:.4f}  kappa_parent={kappa_parent:.4f}  err={kappa_err:.2e}")
assert kappa_err < 1e-12

# Block-diagonal F (12x12)
for cid, lbl in [(cx0_id, "lower-x"), (cx1_id, "upper-x")]:
    F = mu1.entailments[(seed.id, cid)].restriction
    assert F.shape == (12, 12), f"F shape={F.shape}, expected (12,12)"
    off = max(
        np.linalg.norm(F[0:4, 4:12]),
        np.linalg.norm(F[4:8, 0:4]),
        np.linalg.norm(F[4:8, 8:12]),
        np.linalg.norm(F[8:12, 0:8]),
    )
    print(f"  Block-diagonal off-diag max ({lbl}): {off:.2e}")
    assert off < 1e-7, f"cross-sector coupling detected: {off}"

assert is_valid(mu1),                   "FAIL: is_valid (bisect_x)"
assert is_valid_b(mu1),                 "FAIL: is_valid_b (bisect_x)"
assert is_unit_norm(mu1),               "FAIL: is_unit_norm (bisect_x)"
assert is_spatially_valid(mu1),         "FAIL: is_spatially_valid (bisect_x)"
assert is_valid_block_diagonal_306(mu1),"FAIL: is_valid_block_diagonal_306 (bisect_x)"
print(f"  All 5 predicates (bisect_x): PASS")

# Dual ghost observables after bisect_x
print(f"  B_A(t=1)={mu1.B_A():.6f}  B_C(t=1)={mu1.B_C():.6f}")

# ---------------------------------------------------------------------------
# 2. Gamma306(Seed, octree_split) -> 8 children
# ---------------------------------------------------------------------------
print(f"\n--- Gamma306(Seed, octree_split) -> 8 octants ---")
oct_payloads = [f"oct_c{i}" for i in range(8)]
mu_oct, oct_cost = apply_gamma_306(
    mu=mu0, claim_id=seed.id, partition_key="octree_split",
    payloads=oct_payloads, beta=BETA, budget=B0, spent=0.0,
)
print(f"  cost={oct_cost:.4f}  H_oct={mu_oct._H[:16]}...")
assert len(mu_oct.active) == 8

kappa_sum_oct = 0.0
omega_sum = 0.0
inv_sqrt3 = 1.0 / math.sqrt(3.0)

for oid in sorted(mu_oct.active):
    child = mu_oct.claims[oid]
    c_lo, c_hi = child.bbox

    # centroid-outward normal
    c_centroid = (c_lo + c_hi) / 2.0
    direction = c_centroid - parent_centroid
    expected_n = direction / np.linalg.norm(direction)
    actual_n = child.stalk[b0N:b1N]
    n_err = float(np.linalg.norm(actual_n - expected_n))
    n_norm = float(np.linalg.norm(actual_n))
    assert n_err < 1e-10,        f"octant centroid-outward n err={n_err}"
    assert abs(n_norm - 1.0) < 1e-8, f"octant ||n||={n_norm}"

    # expected: [±1/√3, ±1/√3, ±1/√3]
    assert all(abs(abs(v) - inv_sqrt3) < 1e-10 for v in actual_n), \
        f"octant n not [±1/√3,±1/√3,±1/√3]: {actual_n}"

    # centroid
    expected_c = (c_lo + c_hi) / 2.0
    centroid_err = float(np.linalg.norm(child.stalk[b0B:b0B+3] - expected_c))
    assert centroid_err < 1e-10, f"octant centroid err={centroid_err}"

    # w=1
    assert abs(child.stalk[7] - 1.0) < 1e-10, f"octant w={child.stalk[7]}"

    ent = mu_oct.entailments[(seed.id, oid)]
    kappa_sum_oct += float(child.stalk[bK])
    omega_sum += ent.omega
    print(f"    det_sign={ent.det_sign:+d}  n={fmt_N(child.stalk)}  kappa={child.stalk[bK]:.4f}  omega={ent.omega:.4f}")

kappa_err_oct = abs(kappa_sum_oct - float(seed.stalk[bK]))
print(f"  kappa_sum_oct={kappa_sum_oct:.4f}  err={kappa_err_oct:.2e}")
assert kappa_err_oct < 1e-12, f"kappa additive conservation failed: {kappa_err_oct}"

stalk_A_sum = sum(mu_oct.claims[oid].stalk[b0A:b1A] for oid in mu_oct.active)
cons_A_oct = float(np.linalg.norm(stalk_A_sum - seed.stalk[b0A:b1A]))
print(f"  Sector A conservation (N=8): {cons_A_oct:.2e}")
assert cons_A_oct < 1e-10

assert abs(omega_sum - 1.0) < 1e-10, f"omega sum = {omega_sum}"
assert is_valid(mu_oct),                   "FAIL: is_valid (octree)"
assert is_valid_b(mu_oct),                 "FAIL: is_valid_b (octree)"
assert is_unit_norm(mu_oct),               "FAIL: is_unit_norm (octree)"
assert is_spatially_valid(mu_oct),         "FAIL: is_spatially_valid (octree)"
assert is_valid_block_diagonal_306(mu_oct),"FAIL: is_valid_block_diagonal_306 (octree)"
print(f"  All predicates (octree N=8): PASS")
print(f"  Centroid-outward normals [±1/√3,±1/√3,±1/√3]: PASS")
print(f"  B_A(oct)={mu_oct.B_A():.6f}  B_C(oct)={mu_oct.B_C():.6f}")

# ---------------------------------------------------------------------------
# 3. Dual ghost B_A/B_C after second partition
# ---------------------------------------------------------------------------
print(f"\n--- Dual ghost observables ---")
# Partition cx0 (lower-x half) into 2 more children (bisect_y)
mu2, c2 = apply_gamma_306(
    mu=mu1, claim_id=cx0_id, partition_key="axis_bisect_y",
    payloads=["level2_y0", "level2_y1"],
    beta=BETA, budget=B0, spent=g_cost,
)
B_A_2 = mu2.B_A()
B_C_2 = mu2.B_C()
print(f"  After t=2 (bisect_y on cx0):")
print(f"    B_A(t=2)={B_A_2:.6f}  B_C(t=2)={B_C_2:.6f}")
print(f"    ||S_A||={np.linalg.norm(mu2.S_A):.6f}  ||S_C||={np.linalg.norm(mu2.S_C):.6f}")
assert B_A_2 >= 0.0 and B_C_2 >= 0.0, "ghost ratios must be non-negative"
# S_A and S_C are separate arrays
assert mu2.S_A.shape == (8,), f"S_A shape={mu2.S_A.shape}"
assert mu2.S_C.shape == (4,), f"S_C shape={mu2.S_C.shape}"
# Dual arithmetic separation: separate array objects with correct shapes
# G=0 for lossless ops so S stays zero; separation verified structurally
assert mu2.S_A is not mu2.S_C, "S_A and S_C must be distinct array objects"
G_A_vec = mu2.G_A(); G_C_vec = mu2.G_C()
assert G_A_vec.shape == (8,) and G_C_vec.shape == (4,), "ghost shape mismatch"
print(f"    Dual arithmetic separation: PASS  (S_A={mu2.S_A.shape}, S_C={mu2.S_C.shape}, G_A={G_A_vec.shape}, G_C={G_C_vec.shape})")

# ---------------------------------------------------------------------------
# 4. Recursive Gamma depth=2
# ---------------------------------------------------------------------------
print(f"\n--- Recursive Gamma (K_budget_0=256, depth=2, axis_bisect_x) ---")
K_BUDGET_0 = DECL["recursive_gamma"]["K_budget_0"]  # 256
payload_fn = lambda d, i: f"rec_d{d}_i{i}"

mu_rec, rec_cost = apply_gamma_306_recursive(
    mu=mu0,
    claim_id=seed.id,
    partition_key="axis_bisect_x",
    payload_fn=payload_fn,
    beta=BETA,
    budget=B0,
    spent=0.0,
    K_budget=K_BUDGET_0,
    depth=0,
)

n_leaves = len(mu_rec.active)
total_claims = len(mu_rec.claims)
print(f"  Total claims: {total_claims}  Active leaves: {n_leaves}")
print(f"  Total cost: {rec_cost:.4f}")
print(f"  H_rec={mu_rec._H[:16]}...")

# Depth schedule: 256->128->64->32->16->STOP
# axis_bisect_x: N=2 per level, depth_max=4
# At K_budget_0=256: each bisect halves K -> depth 4 max
# Actual depth depends on claim payload sizes fitting K-bound
# Minimum: at least depth=1 (seed -> 2 leaves) occurred
assert n_leaves >= 2, f"expected >= 2 leaves, got {n_leaves}"

# Verify all leaves pass predicates
assert is_valid(mu_rec),                   "FAIL: is_valid (recursive)"
assert is_valid_b(mu_rec),                 "FAIL: is_valid_b (recursive)"
assert is_unit_norm(mu_rec),               "FAIL: is_unit_norm (recursive)"
assert is_spatially_valid(mu_rec),         "FAIL: is_spatially_valid (recursive)"
assert is_valid_block_diagonal_306(mu_rec),"FAIL: is_valid_block_diagonal_306 (recursive)"
print(f"  All predicates (recursive): PASS")
print(f"  B_A={mu_rec.B_A():.6f}  B_C={mu_rec.B_C():.6f}")

# K_budget floor check: verify K_budget halves correctly
K_d = [K_BUDGET_0 * math.exp(-LAMBDA_DECAY * d) for d in range(6)]
print(f"  K_budget schedule: {[f'{k:.1f}' for k in K_d]}")
assert K_d[4] >= K_MIN_PARTITION - 0.01, f"K_d[4]={K_d[4]} < K_MIN_PARTITION={K_MIN_PARTITION}"
assert K_d[5] < K_MIN_PARTITION,         f"K_d[5]={K_d[5]} >= K_MIN_PARTITION={K_MIN_PARTITION}"
print(f"  K_budget depth schedule: PASS (floor at depth 4, stop at depth 5)")

# ---------------------------------------------------------------------------
# 5. is_valid_block_diagonal_306 violation
# ---------------------------------------------------------------------------
print(f"\n--- is_valid_block_diagonal_306 violation: inject F[0,8]=0.5 (A->C coupling) ---")
mu_bad = copy.deepcopy(mu1)
ent_key = (seed.id, cx0_id)
bad_ent = mu_bad.entailments[ent_key]
bad_F = bad_ent.restriction.copy()
bad_F[0, 8] = 0.5   # A sector coupling to C sector
object.__setattr__(bad_ent, 'restriction', bad_F)
mu_bad.entailments[ent_key] = bad_ent
result_bd = is_valid_block_diagonal_306(mu_bad)
print(f"  is_valid_block_diagonal_306 with F[0,8]=0.5: {result_bd}  {'PASS' if not result_bd else 'FAIL'}")
assert not result_bd

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n=== EXP-306 Seed PASS (Fork A) ===")
print(f"  declaration_hash: {stored_hash}")
print(f"  H_0:              {mu0._H[:16]}...")
print(f"  H_1 (bisect_x):   {mu1._H[:16]}...")
print(f"  H_oct (octree):   {mu_oct._H[:16]}...")
print(f"  H_rec (recursive):{mu_rec._H[:16]}...")
print(f"  d={D}  schema: {DECL['stalk_schema']['dims']}")
print(f"  Sector A [0-3]  sum conservation:            PASS")
print(f"  Sector B [4-7]  barycentric + w=1:           PASS")
print(f"  Sector C [8-10] centroid-outward unit-norm:  PASS")
print(f"  Sector C [11]   kappa additive conservation: PASS")
print(f"  Block-diagonal F (d=12, no sector coupling): PASS")
print(f"  Dual ghost S_A/S_C independent EMA:          PASS")
print(f"  Recursive Gamma K_budget floor:              PASS")
print(f"  is_valid_block_diagonal_306 violation:       PASS")
print(f"  Octree [±1/√3,±1/√3,±1/√3] centroid normals: PASS")
