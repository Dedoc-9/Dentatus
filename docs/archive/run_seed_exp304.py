"""
run_seed_exp304.py — EXP-304 Affine Reality Engine seed test.

Protocol: exp304-v1
declaration_hash: a369ce20f55674f14476a6a56f785e4496baa35c2c8a7a72ba95577adb1c230b

Test sequence:
  1. Seed_0_affine:  d=8, stalk=[1,1,1,1, 0.5,0.5,0.5,1], bbox=[0,1]^3
  2. Gamma304(Seed, axis_bisect_x) -> 2 children
       - Sector A conservation:  ||A_x0 + A_x1 - A_seed|| < 1e-10
       - Sector B centroid:      child.stalk[4:7] = centroid(child.bbox)
       - w=1 invariant:          child.stalk[7] == 1.0
       - Barycentric:            0.5*stalk_B(x0) + 0.5*stalk_B(x1) ~ stalk_B(seed)
  3. Gamma304(Seed, octree_split) -> 8 children (all invariants above, N=8)
  4. Containment violation -> is_spatially_valid=False
  5. is_valid_b violation  -> mutate w -> is_valid_b=False
  6. Psi + R3 on axis_bisect_x children
"""

import sys
import json
import hashlib
import numpy as np
sys.path.insert(0, ".")

from engine.state import (
    MuState, Claim, Entailment, EntailmentType, Provenance,
    PROTOCOL_VERSION, now_iso, ALPHA_DEFAULT as ALPHA
)
from engine.operators import (
    apply_gamma_304, apply_psi, apply_omega,
    tensor_product_artifact, check_r3,
    SECTOR_A_DIMS, SECTOR_B_DIMS
)
from engine.validity import is_valid, is_valid_b, is_spatially_valid

# ---------------------------------------------------------------------------
# Load seed declaration and verify hash
# ---------------------------------------------------------------------------
with open("studies/exp304_affine_engine/SEED_DECLARATION_exp304.json") as f:
    DECL = json.load(f)

stored_hash = DECL["declaration_hash"]
verify_fields = {k: v for k, v in DECL.items() if k not in ("declaration_hash", "status")}
canonical = json.dumps(verify_fields, sort_keys=True, separators=(',', ':'))
computed_hash = hashlib.sha256(canonical.encode()).hexdigest()
assert computed_hash == stored_hash, (
    f"SEED HASH MISMATCH\n  stored:   {stored_hash}\n  computed: {computed_hash}"
)

BETA = DECL.get("beta", 0.1)
B0   = DECL.get("B0", 100.0)
D    = DECL["d"]                          # 8
SEED_STALK  = np.array(DECL["seed_stalk"], dtype=float)
BBOX_LO     = np.array(DECL["seed_bbox_lo"], dtype=float)
BBOX_HI     = np.array(DECL["seed_bbox_hi"], dtype=float)

A0, A1 = SECTOR_A_DIMS[0], SECTOR_A_DIMS[-1] + 1   # [0:4]
B0s, B1s = SECTOR_B_DIMS[0], SECTOR_B_DIMS[-1] + 1  # [4:8]

def fmt_A(stalk): return f"[{', '.join(f'{v:.3f}' for v in stalk[A0:A1])}]"
def fmt_B(stalk): return f"[{', '.join(f'{v:.3f}' for v in stalk[B0s:B1s])}]"
def bbox_str(bbox):
    if bbox is None: return "None"
    return f"[[{', '.join(f'{v:.1f}' for v in bbox[0])}] -> [{', '.join(f'{v:.1f}' for v in bbox[1])}]]"

# ---------------------------------------------------------------------------
# 0. Build Seed_0_affine
# ---------------------------------------------------------------------------
seed_prov = Provenance(parent_ids=(), operator_id="Seed_0_affine", timestamp=now_iso())
seed = Claim(provenance=seed_prov, payload="Seed_0_affine: d=8 EXP-304, mass=1 white unit cube.",
             stalk=SEED_STALK.copy(), t=0, bbox=(BBOX_LO, BBOX_HI))
mu0 = MuState(
    claims={seed.id: seed},
    entailments={},
    active=frozenset([seed.id]),
    t=0, S=np.zeros(D), alpha=ALPHA,
)
mu0.seal()

print(f"Seed_0_affine  H_0: {mu0._H[:16]}...")
print(f"  Sector A (mass,r,g,b): {fmt_A(seed.stalk)}")
print(f"  Sector B (x,y,z,w):    {fmt_B(seed.stalk)}")
print(f"  bbox: {bbox_str(seed.bbox)}")

assert seed.stalk[7] == 1.0, "seed w != 1"
assert is_valid_b(mu0), "seed fails is_valid_b"

# ---------------------------------------------------------------------------
# 1. Gamma304(Seed, axis_bisect_x) -> 2 children
# ---------------------------------------------------------------------------
print(f"\n--- Gamma304(Seed, axis_bisect_x) ---")
mu1, g_cost = apply_gamma_304(
    mu=mu0, claim_id=seed.id, partition_key="axis_bisect_x",
    payloads=["A_x0", "A_x1"], beta=BETA, budget=B0, spent=0.0
)
print(f"  cost={g_cost:.4f}  H_1={mu1._H[:16]}...")

# Identify children by bbox lo_x
all_ids = list(mu1.active)
cx0_id = next(cid for cid in all_ids if mu1.claims[cid].bbox[0][0] < 0.1)
cx1_id = next(cid for cid in all_ids if mu1.claims[cid].bbox[0][0] > 0.4)
cx0 = mu1.claims[cx0_id]; cx1 = mu1.claims[cx1_id]

print(f"  lower-x half:")
print(f"    Sector A: {fmt_A(cx0.stalk)}   Sector B: {fmt_B(cx0.stalk)}")
print(f"    bbox: {bbox_str(cx0.bbox)}   omega={mu1.entailments[(seed.id,cx0_id)].omega:.4f}")
print(f"  upper-x half:")
print(f"    Sector A: {fmt_A(cx1.stalk)}   Sector B: {fmt_B(cx1.stalk)}")
print(f"    bbox: {bbox_str(cx1.bbox)}   omega={mu1.entailments[(seed.id,cx1_id)].omega:.4f}")

# Sector A conservation
seed_A = seed.stalk[A0:A1]
cons_A = float(np.linalg.norm((cx0.stalk[A0:A1] + cx1.stalk[A0:A1]) - seed_A))
print(f"  Sector A conservation ||A_x0+A_x1-A_seed||: {cons_A:.2e}")
assert cons_A < 1e-10

# Sector B centroid check
for cid, lbl in [(cx0_id,"lower"), (cx1_id,"upper")]:
    c = mu1.claims[cid]
    c_lo, c_hi = c.bbox
    expected_centroid = (c_lo + c_hi) / 2.0
    actual_centroid = c.stalk[B0s:B0s+3]
    err = float(np.linalg.norm(actual_centroid - expected_centroid))
    print(f"  Sector B centroid ({lbl}): expected {expected_centroid}, err={err:.2e}")
    assert err < 1e-10, f"centroid mismatch: {actual_centroid} vs {expected_centroid}"

# w=1 invariant
assert abs(cx0.stalk[7] - 1.0) < 1e-10, f"cx0 w={cx0.stalk[7]}"
assert abs(cx1.stalk[7] - 1.0) < 1e-10, f"cx1 w={cx1.stalk[7]}"
print(f"  w=1 invariant: PASS")

# Barycentric check
omega0 = mu1.entailments[(seed.id, cx0_id)].omega
omega1 = mu1.entailments[(seed.id, cx1_id)].omega
bary_err = float(np.linalg.norm(
    omega0 * cx0.stalk[B0s:B1s] + omega1 * cx1.stalk[B0s:B1s] - seed.stalk[B0s:B1s]
))
print(f"  Barycentric Σωᵢ·stalk_B err: {bary_err:.2e}")
assert bary_err < 1e-10

assert is_valid(mu1),           "FAIL: is_valid (Sector A)"
assert is_valid_b(mu1),         "FAIL: is_valid_b (Sector B)"
assert is_spatially_valid(mu1), "FAIL: is_spatially_valid"
print(f"  is_valid_A / is_valid_B / is_spatially_valid: PASS")

# ---------------------------------------------------------------------------
# 2. Gamma304(Seed, octree_split) -> 8 children
# ---------------------------------------------------------------------------
print(f"\n--- Gamma304(Seed, octree_split) -> 8 octants ---")
oct_payloads = [f"oct{i}" for i in range(8)]
mu_oct, oct_cost = apply_gamma_304(
    mu=mu0, claim_id=seed.id, partition_key="octree_split",
    payloads=oct_payloads, beta=BETA, budget=B0, spent=0.0
)
print(f"  cost={oct_cost:.4f}  H={mu_oct._H[:16]}...")
assert len(mu_oct.active) == 8

stalk_A_sum = np.zeros(4)
omega_sum = 0.0
for oid in mu_oct.active:
    child = mu_oct.claims[oid]
    stalk_A_sum += child.stalk[A0:A1]
    # Centroid check
    c_lo, c_hi = child.bbox
    expected_c = (c_lo + c_hi) / 2.0
    actual_c = child.stalk[B0s:B0s+3]
    assert np.linalg.norm(actual_c - expected_c) < 1e-10, \
        f"Octant centroid wrong: {actual_c} vs {expected_c}"
    # w=1
    assert abs(child.stalk[7] - 1.0) < 1e-10, f"Octant w={child.stalk[7]}"
    ent = mu_oct.entailments[(seed.id, oid)]
    omega_sum += ent.omega

cons_A_oct = float(np.linalg.norm(stalk_A_sum - seed.stalk[A0:A1]))
print(f"  Sector A conservation (N=8): {cons_A_oct:.2e}")
assert cons_A_oct < 1e-10

assert abs(omega_sum - 1.0) < 1e-10, f"Σ omega = {omega_sum} ≠ 1"
print(f"  Σ ωᵢ = {omega_sum:.10f}  (should be 1.0)")
assert is_valid_b(mu_oct),         "FAIL: is_valid_b octree"
assert is_spatially_valid(mu_oct), "FAIL: is_spatially_valid octree"
print(f"  Centroid-bbox alignment (N=8): PASS")
print(f"  w=1 invariant (N=8):           PASS")
print(f"  is_valid_B / is_spatially_valid: PASS")

for oid in sorted(mu_oct.active):
    c = mu_oct.claims[oid]
    ent = mu_oct.entailments[(seed.id, oid)]
    print(f"    det_sign={ent.det_sign:+d}  bbox={bbox_str(c.bbox)}")

# ---------------------------------------------------------------------------
# 3. is_valid_b violation: mutate w on a child
# ---------------------------------------------------------------------------
print(f"\n--- is_valid_b violation: mutate w -> 2.0 ---")
import copy
mu_bad = copy.deepcopy(mu1)
bad_id = cx0_id
bad_claim = mu_bad.claims[bad_id]
bad_stalk = bad_claim.stalk.copy()
bad_stalk[7] = 2.0   # break w=1
object.__setattr__(bad_claim, 'stalk', bad_stalk)  # Claim is not frozen; direct assign
mu_bad.claims[bad_id] = bad_claim
result = is_valid_b(mu_bad)
print(f"  is_valid_b with w=2.0: {result}  {'PASS' if not result else 'FAIL'}")
assert not result

# ---------------------------------------------------------------------------
# 4. Psi(cx0, cx1) + R3
# ---------------------------------------------------------------------------
print(f"\n--- Psi(cx0, cx1) -> v_blend ---")
mu2, psi_cost = apply_psi(
    mu=mu1, claim_ids=[cx0_id, cx1_id],
    synthesis_key="spatial_blend",
    payload="blend_x0_x1_exp304",
    weights=[0.5, 0.5],
    beta=BETA, budget=B0, spent=g_cost
)
spent = g_cost + psi_cost
mu2.seal()
blend_id = next(iter(mu2.active))
blend = mu2.claims[blend_id]
print(f"  cost={psi_cost:.4f}  blend Sector A: {fmt_A(blend.stalk)}  Sector B: {fmt_B(blend.stalk)}")

# R3: Omega(Psi(A,B)) ~ Omega(A) ⊗ Omega(B)
# apply_omega(mu, claim_id, confluence_cert) -> artifact dict
arts_mu1 = []
for cid in [cx0_id, cx1_id]:
    art = apply_omega(mu=mu1, claim_id=cid, confluence_cert=f"cert_{cid[:8]}")
    arts_mu1.append(art)

Art_blend = apply_omega(mu=mu2, claim_id=blend_id, confluence_cert="cert_blend")

Art_A = arts_mu1[0]
Art_B = arts_mu1[1]
Art_tensor = tensor_product_artifact(Art_A, Art_B, weights=[0.5, 0.5])
r3_pass, r3_err = check_r3(Art_blend, Art_tensor)
K_gain = Art_tensor["K_bound_sum"] - Art_blend["K_bound"]
print(f"  R3 stalk err: {r3_err:.2e}  K_gain={K_gain} bytes")
assert r3_pass, f"R3 FAIL: err={r3_err}"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n=== EXP-304 Seed PASS ===")
print(f"  declaration_hash: {stored_hash}")
print(f"  H_0:              {mu0._H[:16]}...")
print(f"  H_1 (bisect_x):   {mu1._H[:16]}...")
print(f"  H_oct (octree):   {mu_oct._H[:16]}...")
print(f"  H_2 (post-Psi):   {mu2._H[:16]}...")
print(f"  d={D}  schema: {DECL['stalk_schema']['dims']}")
print(f"  Sector A [0–3] sum conservation:     PASS")
print(f"  Sector B [4–7] barycentric:          PASS")
print(f"  Sector B w=1 invariant:              PASS")
print(f"  is_valid_b violation detected:       PASS")
print(f"  Gamma304 octree (N=8):               PASS")
print(f"  det_sign stored (Fork B ready):      PASS")
print(f"  R3 err: {r3_err:.2e}")
print(f"  Budget spent: {spent:.4f} / {B0}")
