"""
run_p_invariance_exp306.py -- EXP-306 P_yz invariance test (Fork B).

Protocol: exp306-v1
declaration_hash: 5a8e1afc590d8ffb9dfe33977005eb888798c1ccdc9dd64c59b797eb8d48fe47

P_yz operator:
  polar_flip  dim 4 (x):  stalk[4] -> -stalk[4]
  axial_flip  dim 8 (nx): stalk[8] -> -stalk[8]
  bbox x-axis:            (lo[0], hi[0]) -> (-hi[0], -lo[0])

Seed: stalk_C=[nx=0.6, ny=0, nz=0.8] (non-zero nx, closes E-305-002).
  ||n||=1.0  (0.6^2 + 0.8^2 = 1.0)

Tests:
  1. det_sign gate: forward and mirror children same det_sign by partition index.
  2. Sector B prediction: mirror[j].x == -fwd[i].x at P_yz-correspondence.
  3. Sector C P_yz closure (E-305-002 resolved):
       n_mirror_child_j == P_yz(n_fwd_child_i)  at P_yz-correspondence.
  4. kappa invariance: kappa_mirror_child == kappa_fwd_child.
  5. Octree N=8 det_sign gate.
"""

import sys
import json
import hashlib
import numpy as np
sys.path.insert(0, ".")

from engine.state import (
    MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA, EPSILON
)
from engine.operators import (
    apply_gamma_306,
    SECTOR_A_DIMS, SECTOR_B_DIMS, SECTOR_C_DIMS, SECTOR_C_KAPPA_DIM,
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
assert computed_hash == stored_hash, f"SEED HASH MISMATCH"
print(f"Seed hash verified: {stored_hash[:16]}...")

BETA = DECL.get("beta", 0.1)
B0   = DECL.get("B0", 100.0)
D    = DECL["d"]   # 12

b0B, b1B = SECTOR_B_DIMS[0], SECTOR_B_DIMS[-1] + 1  # [4:8]
b0N = SECTOR_C_DIMS[0];  b1N = SECTOR_C_DIMS[-1] + 1  # [8:11]
bK  = SECTOR_C_KAPPA_DIM                               # 11

# ---------------------------------------------------------------------------
# P_yz stalk and bbox operators
# ---------------------------------------------------------------------------
def apply_p_yz_stalk(stalk):
    """flip stalk[4] (x polar) and stalk[8] (nx axial)."""
    s = stalk.copy()
    s[4] = -s[4]
    s[8] = -s[8]
    return s

def apply_p_yz_bbox(bbox):
    """reflect bbox x-axis: (lo[0], hi[0]) -> (-hi[0], -lo[0])."""
    lo, hi = bbox[0].copy(), bbox[1].copy()
    lo[0], hi[0] = -bbox[1][0], -bbox[0][0]
    return (lo, hi)

# ---------------------------------------------------------------------------
# Non-zero nx seed (closes E-305-002)
# ---------------------------------------------------------------------------
SEED_STALK = np.array([1., 1., 1., 1.,   0.5, 0.5, 0.5, 1.,   0.6, 0., 0.8, 0.5], dtype=float)
# Sector C normal: [0.6, 0, 0.8] -- verify unit norm
assert abs(np.linalg.norm(SEED_STALK[b0N:b1N]) - 1.0) < 1e-10, "seed ||n|| != 1"
BBOX_LO = np.array([0., 0., 0.])
BBOX_HI = np.array([1., 1., 1.])

def make_mu(stalk, bbox_lo, bbox_hi, S_A=None, S_C=None, label="Seed"):
    prov = Provenance(parent_ids=(), operator_id=label, timestamp=now_iso())
    claim = Claim(provenance=prov,
                  payload=f"{label}: d=12 EXP-306 P_yz test.",
                  stalk=stalk.copy(), t=0, bbox=(bbox_lo.copy(), bbox_hi.copy()))
    mu = MuState(
        claims={claim.id: claim},
        entailments={},
        active=frozenset([claim.id]),
        t=0,
        S=np.zeros(D),
        alpha=ALPHA,
        S_A=S_A if S_A is not None else np.zeros(8),
        S_C=S_C if S_C is not None else np.zeros(4),
    )
    mu.seal()
    return mu, claim

print(f"\nP_yz seed stalk: {list(np.round(SEED_STALK, 4))}")
print(f"  n=[{SEED_STALK[8]:.1f},{SEED_STALK[9]:.1f},{SEED_STALK[10]:.1f}]  kappa={SEED_STALK[11]:.2f}")

# mirror stalk and bbox
MIRROR_STALK = apply_p_yz_stalk(SEED_STALK)
MIRROR_BBOX_LO = np.array([-1., 0., 0.])
MIRROR_BBOX_HI = np.array([ 0., 1., 1.])

print(f"  P_yz(stalk): {list(np.round(MIRROR_STALK, 4))}")
print(f"  P_yz(bbox): {list(MIRROR_BBOX_LO)} -> {list(MIRROR_BBOX_HI)}")

# ---------------------------------------------------------------------------
# 1. axis_bisect_x: forward and mirror passes
# ---------------------------------------------------------------------------
print(f"\n--- axis_bisect_x: forward vs mirror ---")

mu_fwd, seed_fwd = make_mu(SEED_STALK, BBOX_LO, BBOX_HI, label="Seed_fwd")
mu_mir, seed_mir = make_mu(MIRROR_STALK, MIRROR_BBOX_LO, MIRROR_BBOX_HI, label="Seed_mir")

mu_fwd1, _ = apply_gamma_306(
    mu=mu_fwd, claim_id=seed_fwd.id, partition_key="axis_bisect_x",
    payloads=["fwd_x0", "fwd_x1"], beta=BETA, budget=B0, spent=0.0,
)
mu_mir1, _ = apply_gamma_306(
    mu=mu_mir, claim_id=seed_mir.id, partition_key="axis_bisect_x",
    payloads=["mir_x0", "mir_x1"], beta=BETA, budget=B0, spent=0.0,
)

# Sort children by partition index (entailment order is stable for same seed rng)
fwd_ids = sorted(mu_fwd1.active, key=lambda cid: mu_fwd1.claims[cid].bbox[0][0])
mir_ids = sorted(mu_mir1.active, key=lambda cid: mu_mir1.claims[cid].bbox[0][0], reverse=True)
# fwd: [lower-x(0..0.5), upper-x(0.5..1)]
# mirror (reflected): [upper_mir(-0.5..0), lower_mir(-1..-0.5)]
# P_yz correspondence: fwd[0] <-> mir[0] (both "near zero" x boundary)

print(f"  Forward children:")
for i, cid in enumerate(fwd_ids):
    c = mu_fwd1.claims[cid]
    ent = mu_fwd1.entailments[(seed_fwd.id, cid)]
    print(f"    [{i}] bbox_lo_x={c.bbox[0][0]:.2f}  n={list(np.round(c.stalk[b0N:b1N],4))}  "
          f"kappa={c.stalk[bK]:.4f}  det_sign={ent.det_sign:+d}")

print(f"  Mirror children:")
for i, cid in enumerate(mir_ids):
    c = mu_mir1.claims[cid]
    ent = mu_mir1.entailments[(seed_mir.id, cid)]
    print(f"    [{i}] bbox_lo_x={c.bbox[0][0]:.2f}  n={list(np.round(c.stalk[b0N:b1N],4))}  "
          f"kappa={c.stalk[bK]:.4f}  det_sign={ent.det_sign:+d}")

# Gate 1: det_sign equality at correspondence
for i, (fwd_id, mir_id) in enumerate(zip(fwd_ids, mir_ids)):
    fwd_det = mu_fwd1.entailments[(seed_fwd.id, fwd_id)].det_sign
    mir_det = mu_mir1.entailments[(seed_mir.id, mir_id)].det_sign
    assert fwd_det == mir_det, f"det_sign mismatch at index {i}: fwd={fwd_det} mir={mir_det}"
print(f"  det_sign gate (N=2): PASS (all {len(fwd_ids)} pairs matched)")

# Gate 2: Sector B x-coordinate P_yz prediction
for i, (fwd_id, mir_id) in enumerate(zip(fwd_ids, mir_ids)):
    fwd_x = float(mu_fwd1.claims[fwd_id].stalk[4])  # x = dim 4
    mir_x = float(mu_mir1.claims[mir_id].stalk[4])
    err = abs(mir_x - (-fwd_x))
    assert err < 1e-10, f"Sector B x-prediction err={err} at index {i}"
print(f"  Sector B P_yz prediction (x_mirror = -x_fwd): PASS")

# Gate 3: Sector C normal P_yz closure (E-305-002 resolution)
sector_C_err_max = 0.0
for i, (fwd_id, mir_id) in enumerate(zip(fwd_ids, mir_ids)):
    n_fwd = mu_fwd1.claims[fwd_id].stalk[b0N:b1N]
    n_mir = mu_mir1.claims[mir_id].stalk[b0N:b1N]
    n_fwd_pyz = apply_p_yz_stalk(np.pad(n_fwd, (b0N, D - b1N)))[b0N:b1N]
    err = float(np.linalg.norm(n_mir - n_fwd_pyz))
    sector_C_err_max = max(sector_C_err_max, err)
    print(f"  Sector C [index {i}]: n_fwd={list(np.round(n_fwd,4))}  "
          f"P_yz(n_fwd)={list(np.round(n_fwd_pyz,4))}  n_mir={list(np.round(n_mir,4))}  err={err:.2e}")
    assert err < 1e-10, f"Sector C P_yz closure failed at index {i}: err={err}"
print(f"  Sector C P_yz closure (E-305-002 resolved): PASS  max_err={sector_C_err_max:.2e}")

# Gate 4: kappa invariance
for i, (fwd_id, mir_id) in enumerate(zip(fwd_ids, mir_ids)):
    k_fwd = float(mu_fwd1.claims[fwd_id].stalk[bK])
    k_mir = float(mu_mir1.claims[mir_id].stalk[bK])
    err = abs(k_fwd - k_mir)
    assert err < 1e-12, f"kappa invariance violated at index {i}: fwd={k_fwd} mir={k_mir}"
print(f"  kappa invariance (P_yz): PASS")

# All validity predicates on both states
for mu_test, lbl in [(mu_fwd1,"fwd"), (mu_mir1,"mirror")]:
    assert is_valid(mu_test),                   f"FAIL is_valid ({lbl})"
    assert is_valid_b(mu_test),                 f"FAIL is_valid_b ({lbl})"
    assert is_unit_norm(mu_test),               f"FAIL is_unit_norm ({lbl})"
    assert is_spatially_valid(mu_test),         f"FAIL is_spatially_valid ({lbl})"
    assert is_valid_block_diagonal_306(mu_test),f"FAIL is_valid_block_diagonal_306 ({lbl})"
print(f"  All predicates (fwd + mirror): PASS")

# ---------------------------------------------------------------------------
# 2. Octree N=8 det_sign gate
# ---------------------------------------------------------------------------
print(f"\n--- octree_split N=8: det_sign gate ---")
mu_fwd_oct, _ = apply_gamma_306(
    mu=mu_fwd, claim_id=seed_fwd.id, partition_key="octree_split",
    payloads=[f"foct{i}" for i in range(8)], beta=BETA, budget=B0, spent=0.0,
)
mu_mir_oct, _ = apply_gamma_306(
    mu=mu_mir, claim_id=seed_mir.id, partition_key="octree_split",
    payloads=[f"moct{i}" for i in range(8)], beta=BETA, budget=B0, spent=0.0,
)

# Sort by bbox centroid_x for P_yz pairing (negate mirror x for matching)
fwd_oct_ids = sorted(mu_fwd_oct.active,
                     key=lambda cid: (round(mu_fwd_oct.claims[cid].bbox[0][0],3),
                                      round(mu_fwd_oct.claims[cid].bbox[0][1],3),
                                      round(mu_fwd_oct.claims[cid].bbox[0][2],3)))
mir_oct_ids = sorted(mu_mir_oct.active,
                     key=lambda cid: (round(-mu_mir_oct.claims[cid].bbox[1][0],3),
                                      round(mu_mir_oct.claims[cid].bbox[0][1],3),
                                      round(mu_mir_oct.claims[cid].bbox[0][2],3)))

sector_C_oct_max = 0.0
kappa_oct_max = 0.0
det_mismatches = 0

for i, (fwd_id, mir_id) in enumerate(zip(fwd_oct_ids, mir_oct_ids)):
    fwd_det = mu_fwd_oct.entailments[(seed_fwd.id, fwd_id)].det_sign
    mir_det = mu_mir_oct.entailments[(seed_mir.id, mir_id)].det_sign
    if fwd_det != mir_det:
        det_mismatches += 1

    n_fwd = mu_fwd_oct.claims[fwd_id].stalk[b0N:b1N]
    n_mir = mu_mir_oct.claims[mir_id].stalk[b0N:b1N]
    n_fwd_pyz = apply_p_yz_stalk(np.pad(n_fwd, (b0N, D - b1N)))[b0N:b1N]
    c_err = float(np.linalg.norm(n_mir - n_fwd_pyz))
    sector_C_oct_max = max(sector_C_oct_max, c_err)

    k_fwd = float(mu_fwd_oct.claims[fwd_id].stalk[bK])
    k_mir = float(mu_mir_oct.claims[mir_id].stalk[bK])
    kappa_oct_max = max(kappa_oct_max, abs(k_fwd - k_mir))

    print(f"  [{i}] det_sign: fwd={fwd_det:+d} mir={mir_det:+d}  "
          f"n_fwd={list(np.round(n_fwd,4))}  n_fwd_pyz={list(np.round(n_fwd_pyz,4))}  "
          f"n_mir={list(np.round(n_mir,4))}  C_err={c_err:.2e}  k_fwd={k_fwd:.4f} k_mir={k_mir:.4f}")

assert det_mismatches == 0, f"det_sign mismatches (N=8): {det_mismatches}"
assert sector_C_oct_max < 1e-10, f"Sector C P_yz oct max_err={sector_C_oct_max}"
assert kappa_oct_max < 1e-12,    f"kappa invariance oct max_err={kappa_oct_max}"

print(f"\n  Octree det_sign gate (N=8): PASS  (0 mismatches)")
print(f"  Sector C P_yz closure (N=8): PASS  max_err={sector_C_oct_max:.2e}")
print(f"  kappa invariance (N=8): PASS  max_err={kappa_oct_max:.2e}")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n=== EXP-306 Fork B PASS ===")
print(f"  declaration_hash:               {stored_hash}")
print(f"  H_fwd (bisect_x):               {mu_fwd1._H[:16]}...")
print(f"  H_mir (bisect_x mirror):        {mu_mir1._H[:16]}...")
print(f"  H_fwd_oct (octree):             {mu_fwd_oct._H[:16]}...")
print(f"  H_mir_oct (octree mirror):      {mu_mir_oct._H[:16]}...")
print(f"  Seed nx={SEED_STALK[8]:.1f} (non-zero: E-305-002 resolved)")
print(f"  det_sign gate (bisect_x N=2):   PASS")
print(f"  Sector B P_yz prediction:       PASS  err=0.00e+00")
print(f"  Sector C P_yz closure:          PASS  max_err={sector_C_err_max:.2e}")
print(f"  kappa P_yz invariance:          PASS")
print(f"  det_sign gate (octree N=8):     PASS")
print(f"  Sector C P_yz closure (N=8):    PASS  max_err={sector_C_oct_max:.2e}")
print(f"  E-305-002:                      CLOSED (centroid-outward convention)")
