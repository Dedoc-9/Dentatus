"""
run_p_invariance_exp305.py -- EXP-305 P_yz mirror invariance test (Fork B).

Protocol: exp305-v1
declaration_hash: 2a05be65524a8ce244ea9597917a5a3f771094a2bc25fd33f801ad1c6cc99e64

Preregistered test (ENGINE_AXIOMS_exp305.md sec 5):
  1. Build Seed_0_axial (mu0) and mu_mirror via P_yz.
  2. Run apply_gamma_305(mu0, axis_bisect_x) -> mu1.
  3. Run apply_gamma_305(mu_mirror, axis_bisect_x) -> mu1_mirror.
  4. Assert: det_sign(mu1_mirror[i]) == det_sign(mu1[i]) for all i (by index).
  Expected: PASS for uniform bbox subdivision.

P_yz operator (preregistered):
  dim 4  (x):  * -1   (polar vector)
  dim 8  (nx): * -1   (axial pseudo-vector)
  dims 0-3, 5-7, 9-10: unchanged

Implementation note E-305-001 (bbox reflection required):
  Applying P_yz to stalk only (x -> -x) while keeping bbox [0,1]^3 violates
  the Sector B barycentric predicate: bbox centroid [0.5,...] != stalk_B_x=-0.5.
  Correct P_yz requires reflecting bbox x-axis simultaneously:
    mirror_lo = [-hi_x, lo_y, lo_z]
    mirror_hi = [-lo_x, hi_y, hi_z]
  This is an implicit requirement underspecified in the preregistration.
  Documented here; does not alter the formal gate.

Note E-305-002 (Sector C direction under P_yz with seed nx=0):
  seed stalk_C = [0, 0, 1]. P_yz flips dim 8 (nx): 0 -> 0 (unchanged).
  Thus stalk_C_parent is IDENTICAL in both forward and mirror passes.
  Phi_C decomposes the same stalk with the same RNG seed=0, producing
  identical child normals in both passes. This is expected: the seed stalk
  lies on the P_yz symmetry axis for Sector C. A non-zero nx seed stalk
  would expose direction divergence (deferred to future run).
  The formal gate (det_sign consistency) is unaffected.
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
    apply_gamma_305,
    SECTOR_A_DIMS, SECTOR_B_DIMS, SECTOR_C_DIMS
)
from engine.validity import (
    is_valid, is_valid_b, is_spatially_valid,
    is_unit_norm, is_valid_block_diagonal
)

# ---------------------------------------------------------------------------
# Load seed declaration and verify hash
# ---------------------------------------------------------------------------
with open("studies/exp305_axial_engine/SEED_DECLARATION_exp305.json") as f:
    DECL = json.load(f)

stored_hash = DECL["declaration_hash"]
verify_fields = {k: v for k, v in DECL.items() if k not in ("declaration_hash", "status")}
canonical = json.dumps(verify_fields, sort_keys=True, separators=(',', ':'))
computed_hash = hashlib.sha256(canonical.encode()).hexdigest()
assert computed_hash == stored_hash, (
    f"SEED HASH MISMATCH\n  stored:   {stored_hash}\n  computed: {computed_hash}"
)
print(f"Seed hash verified: {stored_hash[:16]}...")

BETA        = DECL.get("beta", 0.1)
B0          = DECL.get("B0", 100.0)
D           = DECL["d"]
SEED_STALK  = np.array(DECL["seed_stalk"], dtype=float)
BBOX_LO     = np.array(DECL["seed_bbox_lo"], dtype=float)
BBOX_HI     = np.array(DECL["seed_bbox_hi"], dtype=float)

b0A, b1A = SECTOR_A_DIMS[0], SECTOR_A_DIMS[-1] + 1
b0B, b1B = SECTOR_B_DIMS[0], SECTOR_B_DIMS[-1] + 1
b0C, b1C = SECTOR_C_DIMS[0], SECTOR_C_DIMS[-1] + 1

# ---------------------------------------------------------------------------
# P_yz operator
# ---------------------------------------------------------------------------
# Preregistered: polar flip dims=[4], axial flip dims=[8]
P_YZ_FLIP_STALK_DIMS = [4, 8]
P_YZ_POLAR_DIMS = [4]
P_YZ_AXIAL_DIMS = [8]

def apply_p_yz_stalk(stalk):
    """P_yz: flip dim 4 (x, polar) and dim 8 (nx, axial)."""
    s = stalk.copy()
    for d in P_YZ_FLIP_STALK_DIMS:
        s[d] *= -1.0
    return s


def apply_p_yz_bbox(lo, hi):
    """
    P_yz bbox reflection: x -> -x.
    [lo_x, hi_x] -> [-hi_x, -lo_x].
    y, z unchanged.
    """
    mirror_lo = lo.copy()
    mirror_hi = hi.copy()
    mirror_lo[0] = -hi[0]
    mirror_hi[0] = -lo[0]
    return mirror_lo, mirror_hi


# ---------------------------------------------------------------------------
# Build forward seed (mu0)
# ---------------------------------------------------------------------------
seed_prov = Provenance(parent_ids=(), operator_id="Seed_0_axial", timestamp=now_iso())
seed = Claim(
    provenance=seed_prov,
    payload="Seed_0_axial: d=11 EXP-305.",
    stalk=SEED_STALK.copy(), t=0, bbox=(BBOX_LO.copy(), BBOX_HI.copy())
)
mu0 = MuState(
    claims={seed.id: seed}, entailments={},
    active=frozenset([seed.id]), t=0, S=np.zeros(D), alpha=ALPHA,
)
mu0.seal()

# ---------------------------------------------------------------------------
# Build P_yz mirror seed (mu_mirror)
# ---------------------------------------------------------------------------
mirror_stalk = apply_p_yz_stalk(SEED_STALK)
mirror_lo, mirror_hi = apply_p_yz_bbox(BBOX_LO, BBOX_HI)

mirror_prov = Provenance(parent_ids=(), operator_id="Seed_0_mirror_Pyz", timestamp=now_iso())
mirror_seed = Claim(
    provenance=mirror_prov,
    payload="Seed_0_mirror: P_yz applied to Seed_0_axial.",
    stalk=mirror_stalk, t=0, bbox=(mirror_lo, mirror_hi)
)
mu_mirror = MuState(
    claims={mirror_seed.id: mirror_seed}, entailments={},
    active=frozenset([mirror_seed.id]), t=0, S=np.zeros(D), alpha=ALPHA,
)
mu_mirror.seal()

print(f"\nForward seed stalk [4,8]: x={SEED_STALK[4]:.4f}  nx={SEED_STALK[8]:.4f}")
print(f"Mirror  seed stalk [4,8]: x={mirror_stalk[4]:.4f}  nx={mirror_stalk[8]:.4f}")
print(f"Forward bbox: [{BBOX_LO[0]:.2f},{BBOX_HI[0]:.2f}] x [{BBOX_LO[1]:.2f},{BBOX_HI[1]:.2f}] x [{BBOX_LO[2]:.2f},{BBOX_HI[2]:.2f}]")
print(f"Mirror  bbox: [{mirror_lo[0]:.2f},{mirror_hi[0]:.2f}] x [{mirror_lo[1]:.2f},{mirror_hi[1]:.2f}] x [{mirror_lo[2]:.2f},{mirror_hi[2]:.2f}]")
print(f"H_fwd:    {mu0._H[:16]}...")
print(f"H_mirror: {mu_mirror._H[:16]}...")

# Verify is_valid_b holds for mirror seed (w=1, no entailments yet -> trivially true)
assert is_valid_b(mu_mirror), "mirror seed fails is_valid_b"
assert is_unit_norm(mu_mirror), "mirror seed fails is_unit_norm"

# ---------------------------------------------------------------------------
# Run Gamma_305 on both with axis_bisect_x
# ---------------------------------------------------------------------------
print(f"\n--- Gamma305(forward, axis_bisect_x) ---")
mu1, cost_fwd = apply_gamma_305(
    mu=mu0, claim_id=seed.id, partition_key="axis_bisect_x",
    payloads=["fwd_x0", "fwd_x1"], beta=BETA, budget=B0, spent=0.0
)
print(f"  H_fwd1: {mu1._H[:16]}...  cost={cost_fwd:.4f}")

print(f"\n--- Gamma305(mirror, axis_bisect_x) ---")
mu1_mirror, cost_mirror = apply_gamma_305(
    mu=mu_mirror, claim_id=mirror_seed.id, partition_key="axis_bisect_x",
    payloads=["mir_x0", "mir_x1"], beta=BETA, budget=B0, spent=0.0
)
print(f"  H_mir1: {mu1_mirror._H[:16]}...  cost={cost_mirror:.4f}")

# Identify children by partition index (by bbox lo_x, lower first)
# Forward: lower lo_x < mid; mirror: lower lo_x < mirror_mid
fwd_ids_sorted = sorted(mu1.active, key=lambda cid: mu1.claims[cid].bbox[0][0])
mir_ids_sorted = sorted(mu1_mirror.active, key=lambda cid: mu1_mirror.claims[cid].bbox[0][0])

print(f"\n--- Per-child observables ---")
print(f"{'idx':<4} {'fwd_bbox_lo_x':>14} {'mir_bbox_lo_x':>14} {'fwd_det':>9} {'mir_det':>9} "
      f"{'fwd_nx':>9} {'mir_nx':>9} {'fwd_x':>9} {'mir_x':>9}")

det_signs_fwd  = []
det_signs_mirror = []
nx_fwd_list  = []
nx_mirror_list = []
x_fwd_list   = []
x_mirror_list = []

for i, (fid, mid) in enumerate(zip(fwd_ids_sorted, mir_ids_sorted)):
    fc = mu1.claims[fid];          mc = mu1_mirror.claims[mid]
    fe = mu1.entailments[(seed.id, fid)]
    me = mu1_mirror.entailments[(mirror_seed.id, mid)]

    det_signs_fwd.append(fe.det_sign)
    det_signs_mirror.append(me.det_sign)
    nx_fwd_list.append(float(fc.stalk[8]))
    nx_mirror_list.append(float(mc.stalk[8]))
    x_fwd_list.append(float(fc.stalk[4]))
    x_mirror_list.append(float(mc.stalk[4]))

    print(f"  {i:<2}   {fc.bbox[0][0]:+12.4f}   {mc.bbox[0][0]:+12.4f}   "
          f"{fe.det_sign:+8d}   {me.det_sign:+8d}   "
          f"{fc.stalk[8]:+8.4f}   {mc.stalk[8]:+8.4f}   "
          f"{fc.stalk[4]:+8.4f}   {mc.stalk[4]:+8.4f}")

# ---------------------------------------------------------------------------
# Preregistered assertion: det_sign(fwd_i) == det_sign(mirror_i) for all i
# ---------------------------------------------------------------------------
print(f"\n--- Preregistered gate: det_sign consistency ---")
det_pass = all(d_f == d_m for d_f, d_m in zip(det_signs_fwd, det_signs_mirror))
print(f"  det_sign pairs (fwd, mirror): {list(zip(det_signs_fwd, det_signs_mirror))}")
print(f"  det_sign consistent: {det_pass}  {'PASS' if det_pass else 'FAIL'}")
assert det_pass, "P_yz det_sign consistency FAIL"

# ---------------------------------------------------------------------------
# Sector B P_yz prediction check
# P_yz(fwd_child_x) == mirror of corresponding child x
# Correspondence: fwd[0] (lower x in [0, 0.5]) <-> mirror[1] (upper of mirror [-0.5, 0])
#   P_yz(fwd[0].x = 0.25) = -0.25 => mirror[1].x should be -0.25
#   P_yz(fwd[1].x = 0.75) = -0.75 => mirror[0].x should be -0.75
# ---------------------------------------------------------------------------
print(f"\n--- Sector B P_yz prediction (x-coordinate) ---")
# Cross-map: forward[i] corresponds to mirror[N-1-i] under P_yz for axis_bisect_x
N = len(fwd_ids_sorted)
sector_b_pass = True
for i in range(N):
    j = N - 1 - i   # P_yz reverses x-ordering for axis_bisect_x
    x_fwd = x_fwd_list[i]
    x_mir = x_mirror_list[j]
    predicted = -x_fwd
    err = abs(x_mir - predicted)
    ok = err < 1e-10
    sector_b_pass = sector_b_pass and ok
    print(f"  fwd[{i}].x={x_fwd:+.4f}  P_yz -> -{x_fwd:+.4f}  "
          f"mirror[{j}].x={x_mir:+.4f}  err={err:.2e}  {'OK' if ok else 'FAIL'}")
print(f"  Sector B P_yz prediction: {'PASS' if sector_b_pass else 'FAIL'}")
assert sector_b_pass, "Sector B P_yz x-coordinate prediction FAIL"

# ---------------------------------------------------------------------------
# Sector C P_yz observable (NOT a predicate gate -- documented limit E-305-002)
# Since seed nx=0, P_yz does not change stalk_C_parent, so child normals
# are identical in both passes. Report the discrepancy for the record.
# ---------------------------------------------------------------------------
print(f"\n--- Sector C P_yz observable (E-305-002, non-gate) ---")
print(f"  Note: seed stalk_C = [0,0,1], nx=0. P_yz(nx=0)=0. "
      f"stalk_C_parent identical in both passes.")
for i in range(N):
    j = N - 1 - i
    nx_fwd = nx_fwd_list[i]
    nx_mir = nx_mirror_list[j]
    predicted_nx = -nx_fwd
    err = abs(nx_mir - predicted_nx)
    print(f"  fwd[{i}].nx={nx_fwd:+.6f}  predicted_mirror[{j}].nx={predicted_nx:+.6f}  "
          f"actual_mirror[{j}].nx={nx_mir:+.6f}  err={err:.2e}  (E-305-002: expected non-zero)")

# ---------------------------------------------------------------------------
# Octree P_yz (N=8) det_sign gate
# ---------------------------------------------------------------------------
print(f"\n--- Gamma305(forward, octree_split) ---")
mu_oct_fwd, _ = apply_gamma_305(
    mu=mu0, claim_id=seed.id, partition_key="octree_split",
    payloads=[f"fwd_oct{i}" for i in range(8)], beta=BETA, budget=B0, spent=0.0
)
print(f"  H_oct_fwd: {mu_oct_fwd._H[:16]}...")

print(f"\n--- Gamma305(mirror, octree_split) ---")
mu_oct_mir, _ = apply_gamma_305(
    mu=mu_mirror, claim_id=mirror_seed.id, partition_key="octree_split",
    payloads=[f"mir_oct{i}" for i in range(8)], beta=BETA, budget=B0, spent=0.0
)
print(f"  H_oct_mir: {mu_oct_mir._H[:16]}...")

# Sort octants by (ix, iy, iz) from bbox centroid
def oct_sort_key(cid, mu):
    c = mu.claims[cid]
    cx, cy, cz = (c.bbox[0] + c.bbox[1]) / 2.0
    return (cx, cy, cz)

oct_fwd_sorted = sorted(mu_oct_fwd.active, key=lambda c: oct_sort_key(c, mu_oct_fwd))
oct_mir_sorted = sorted(mu_oct_mir.active, key=lambda c: oct_sort_key(c, mu_oct_mir))

oct_det_pass = True
for i, (fid, mid) in enumerate(zip(oct_fwd_sorted, oct_mir_sorted)):
    fe = mu_oct_fwd.entailments[(seed.id, fid)]
    me = mu_oct_mir.entailments[(mirror_seed.id, mid)]
    ok = (fe.det_sign == me.det_sign)
    oct_det_pass = oct_det_pass and ok

print(f"  octree det_sign consistency (N=8): {'PASS' if oct_det_pass else 'FAIL'}")
assert oct_det_pass, "Octree P_yz det_sign consistency FAIL"

# Combined final validity check
for label, mu in [("fwd bisect", mu1), ("mirror bisect", mu1_mirror),
                   ("fwd octree", mu_oct_fwd), ("mirror octree", mu_oct_mir)]:
    assert is_valid(mu),               f"{label}: is_valid FAIL"
    assert is_valid_b(mu),             f"{label}: is_valid_b FAIL"
    assert is_unit_norm(mu),           f"{label}: is_unit_norm FAIL"
    assert is_spatially_valid(mu),     f"{label}: is_spatially_valid FAIL"
    assert is_valid_block_diagonal(mu),f"{label}: is_valid_block_diagonal FAIL"

print(f"\n  All 5 validity predicates (fwd + mirror, bisect + octree): PASS")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n=== EXP-305 P_yz Fork B PASS ===")
print(f"  declaration_hash: {stored_hash}")
print(f"  P_yz operator:    polar_flip=[4]  axial_flip=[8]")
print(f"  H_fwd:     {mu0._H[:16]}...")
print(f"  H_mirror:  {mu_mirror._H[:16]}...")
print(f"  H_fwd1:    {mu1._H[:16]}...")
print(f"  H_mir1:    {mu1_mirror._H[:16]}...")
print(f"  det_sign consistency (bisect_x N=2): PASS")
print(f"  det_sign consistency (octree  N=8):  PASS")
print(f"  Sector B P_yz prediction (x-coord):  PASS")
print(f"  Sector C E-305-002 (nx=0 seed):      documented, non-gate")
print(f"  EXP-305 Fork B status: COMPLETE")
