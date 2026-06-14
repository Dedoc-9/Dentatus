"""
run_p_invariance_exp307.py -- EXP-307 P_yz invariance test (Fork B).

Protocol: exp307-v1
declaration_hash: 8e288c601093e1dd786ee112c1451f0fa60a2b1cb898ea17a91f63b4a5c89060

Seed: stalk_C=[nx=0.6, ny=0, nz=0.8, kappa=6.0], bbox=[0,1]^3.

Tests:
  1. det_sign gate (bisect_x N=2): fwd and mirror matched by partition index.
  2. Sector B x-prediction: x_mirror == -x_fwd.
  3. Sector C normal P_yz closure: n_mirror == P_yz(n_fwd).
  4. kappa P_yz invariance: kappa_mirror == kappa_fwd.
       P_yz preserves bbox extents -> kappa(bbox_mirror) = kappa(bbox_fwd) EXACT.
  5. Octree N=8: all 4 gates above.
  6. is_valid_kappa on both fwd and mirror states.
"""

import sys, json, hashlib, math
import numpy as np
sys.path.insert(0, ".")

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_307, SECTOR_B_DIMS, SECTOR_C_DIMS, SECTOR_C_KAPPA_DIM,
)
from engine.validity import (
    is_valid, is_valid_b, is_spatially_valid,
    is_unit_norm, is_valid_block_diagonal_306, is_valid_kappa,
    kappa_from_bbox,
)

with open("studies/exp307_shape_operator/SEED_DECLARATION_exp307.json") as f:
    DECL = json.load(f)
stored_hash = DECL["declaration_hash"]
verify_fields = {k: v for k, v in DECL.items() if k not in ("declaration_hash","status")}
canonical = json.dumps(verify_fields, sort_keys=True, separators=(',',':'))
assert hashlib.sha256(canonical.encode()).hexdigest() == stored_hash
print(f"Seed hash verified: {stored_hash[:16]}...")

BETA = DECL.get("beta", 0.1); B0 = DECL.get("B0", 100.0); D = DECL["d"]
b0B, b1B = SECTOR_B_DIMS[0], SECTOR_B_DIMS[-1] + 1
b0N = SECTOR_C_DIMS[0]; b1N = SECTOR_C_DIMS[-1] + 1
bK  = SECTOR_C_KAPPA_DIM

def apply_p_yz_stalk(s):
    s = s.copy(); s[4] = -s[4]; s[8] = -s[8]; return s

def apply_p_yz_bbox(bbox):
    lo, hi = bbox[0].copy(), bbox[1].copy()
    lo[0], hi[0] = -bbox[1][0], -bbox[0][0]
    return (lo, hi)

def make_mu(stalk, bbox_lo, bbox_hi, label="Seed"):
    prov = Provenance(parent_ids=(), operator_id=label, timestamp=now_iso())
    claim = Claim(provenance=prov, payload=f"{label}: d=12 EXP-307 P_yz.",
                  stalk=stalk.copy(), t=0, bbox=(bbox_lo.copy(), bbox_hi.copy()))
    mu = MuState(claims={claim.id: claim}, entailments={}, active=frozenset([claim.id]),
                 t=0, S=np.zeros(D), alpha=ALPHA, S_A=np.zeros(8), S_C=np.zeros(4))
    mu.seal()
    return mu, claim

# Non-zero nx seed (kappa = 6.0 for unit cube)
SEED_STALK = np.array([1.,1.,1.,1., 0.5,0.5,0.5,1., 0.6,0.,0.8,6.0])
assert abs(np.linalg.norm(SEED_STALK[b0N:b1N]) - 1.0) < 1e-10

BBOX_LO = np.array([0.,0.,0.])
BBOX_HI = np.array([1.,1.,1.])
MIRROR_STALK = apply_p_yz_stalk(SEED_STALK)
MIRROR_LO = np.array([-1.,0.,0.])
MIRROR_HI = np.array([ 0.,1.,1.])

print(f"\nSeed   n={list(SEED_STALK[b0N:b1N])}  kappa={SEED_STALK[bK]:.2f}")
print(f"Mirror n={list(MIRROR_STALK[b0N:b1N])}  kappa={MIRROR_STALK[bK]:.2f}")

# Verify seed and mirror kappa are equal (both unit cubes with same extents)
assert abs(kappa_from_bbox((BBOX_LO,BBOX_HI)) - kappa_from_bbox((MIRROR_LO,MIRROR_HI))) < 1e-8

# ---------------------------------------------------------------------------
# 1. axis_bisect_x
# ---------------------------------------------------------------------------
print(f"\n--- axis_bisect_x: forward vs mirror ---")
mu_fwd, seed_fwd = make_mu(SEED_STALK, BBOX_LO, BBOX_HI, label="Seed_fwd_307")
mu_mir, seed_mir = make_mu(MIRROR_STALK, MIRROR_LO, MIRROR_HI, label="Seed_mir_307")

mu_f1, _ = apply_gamma_307(mu=mu_fwd, claim_id=seed_fwd.id, partition_key="axis_bisect_x",
                            payloads=["f307_x0","f307_x1"], beta=BETA, budget=B0, spent=0.0)
mu_m1, _ = apply_gamma_307(mu=mu_mir, claim_id=seed_mir.id, partition_key="axis_bisect_x",
                            payloads=["m307_x0","m307_x1"], beta=BETA, budget=B0, spent=0.0)

fwd_ids = sorted(mu_f1.active, key=lambda cid: mu_f1.claims[cid].bbox[0][0])
mir_ids = sorted(mu_m1.active, key=lambda cid: mu_m1.claims[cid].bbox[0][0], reverse=True)

print(f"  Forward children:")
for i,cid in enumerate(fwd_ids):
    c=mu_f1.claims[cid]; ent=mu_f1.entailments[(seed_fwd.id,cid)]
    print(f"    [{i}] x_lo={c.bbox[0][0]:.2f}  n={list(np.round(c.stalk[b0N:b1N],4))}  "
          f"kappa={c.stalk[bK]:.4f}  det={ent.det_sign:+d}")
print(f"  Mirror children:")
for i,cid in enumerate(mir_ids):
    c=mu_m1.claims[cid]; ent=mu_m1.entailments[(seed_mir.id,cid)]
    print(f"    [{i}] x_lo={c.bbox[0][0]:.2f}  n={list(np.round(c.stalk[b0N:b1N],4))}  "
          f"kappa={c.stalk[bK]:.4f}  det={ent.det_sign:+d}")

n_err_max = 0.0; kappa_err_max = 0.0; bx_err_max = 0.0

for i,(fid,mid) in enumerate(zip(fwd_ids,mir_ids)):
    # det_sign
    assert mu_f1.entailments[(seed_fwd.id,fid)].det_sign == \
           mu_m1.entailments[(seed_mir.id,mid)].det_sign, f"det_sign mismatch [{i}]"
    # Sector B x
    x_fwd = float(mu_f1.claims[fid].stalk[4])
    x_mir = float(mu_m1.claims[mid].stalk[4])
    bx_err = abs(x_mir - (-x_fwd))
    bx_err_max = max(bx_err_max, bx_err)
    assert bx_err < 1e-10, f"Sector B x err={bx_err}"
    # Sector C normal
    n_fwd = mu_f1.claims[fid].stalk[b0N:b1N]
    n_mir = mu_m1.claims[mid].stalk[b0N:b1N]
    n_fwd_pyz = apply_p_yz_stalk(np.pad(n_fwd,(b0N,D-b1N)))[b0N:b1N]
    n_err = float(np.linalg.norm(n_mir - n_fwd_pyz))
    n_err_max = max(n_err_max, n_err)
    assert n_err < 1e-10, f"Sector C n err={n_err} [{i}]"
    # kappa invariance: exact because bbox extents preserved under P_yz
    k_fwd = float(mu_f1.claims[fid].stalk[bK])
    k_mir = float(mu_m1.claims[mid].stalk[bK])
    # Also verify both equal kappa_from_bbox
    k_geom_fwd = kappa_from_bbox(mu_f1.claims[fid].bbox)
    k_geom_mir = kappa_from_bbox(mu_m1.claims[mid].bbox)
    kappa_err = max(abs(k_fwd - k_mir), abs(k_geom_fwd - k_geom_mir))
    kappa_err_max = max(kappa_err_max, kappa_err)
    assert kappa_err < 1e-8, f"kappa P_yz err={kappa_err} [{i}]"
    print(f"  [{i}] n_err={n_err:.2e}  kappa_fwd={k_fwd:.4f}  kappa_mir={k_mir:.4f}  "
          f"kappa_geom_fwd={k_geom_fwd:.4f}  kappa_geom_mir={k_geom_mir:.4f}")

print(f"  det_sign gate (N=2): PASS")
print(f"  Sector B P_yz err: {bx_err_max:.2e}")
print(f"  Sector C n P_yz max_err: {n_err_max:.2e}")
print(f"  kappa P_yz invariance max_err: {kappa_err_max:.2e}")

for mu_test,lbl in [(mu_f1,"fwd"),(mu_m1,"mirror")]:
    assert is_valid(mu_test)                    and True
    assert is_valid_b(mu_test)                  and True
    assert is_unit_norm(mu_test)                and True
    assert is_spatially_valid(mu_test)          and True
    assert is_valid_block_diagonal_306(mu_test) and True
    assert is_valid_kappa(mu_test), f"is_valid_kappa FAIL ({lbl})"
print(f"  All 6 predicates (fwd+mirror): PASS")

# ---------------------------------------------------------------------------
# 2. Octree N=8
# ---------------------------------------------------------------------------
print(f"\n--- octree_split N=8 ---")
mu_fo, _ = apply_gamma_307(mu=mu_fwd, claim_id=seed_fwd.id, partition_key="octree_split",
                            payloads=[f"f307o{i}" for i in range(8)],
                            beta=BETA, budget=B0, spent=0.0)
mu_mo, _ = apply_gamma_307(mu=mu_mir, claim_id=seed_mir.id, partition_key="octree_split",
                            payloads=[f"m307o{i}" for i in range(8)],
                            beta=BETA, budget=B0, spent=0.0)

fwd_oct = sorted(mu_fo.active,
    key=lambda c:(round(mu_fo.claims[c].bbox[0][0],3),
                  round(mu_fo.claims[c].bbox[0][1],3),
                  round(mu_fo.claims[c].bbox[0][2],3)))
mir_oct = sorted(mu_mo.active,
    key=lambda c:(round(-mu_mo.claims[c].bbox[1][0],3),
                  round(mu_mo.claims[c].bbox[0][1],3),
                  round(mu_mo.claims[c].bbox[0][2],3)))

n_err_oct=0.0; k_err_oct=0.0; det_mis=0
for i,(fid,mid) in enumerate(zip(fwd_oct,mir_oct)):
    fd=mu_fo.entailments[(seed_fwd.id,fid)].det_sign
    md=mu_mo.entailments[(seed_mir.id,mid)].det_sign
    if fd != md: det_mis += 1
    n_f=mu_fo.claims[fid].stalk[b0N:b1N]
    n_m=mu_mo.claims[mid].stalk[b0N:b1N]
    n_f_pyz=apply_p_yz_stalk(np.pad(n_f,(b0N,D-b1N)))[b0N:b1N]
    n_err_oct=max(n_err_oct, float(np.linalg.norm(n_m-n_f_pyz)))
    k_f=float(mu_fo.claims[fid].stalk[bK])
    k_m=float(mu_mo.claims[mid].stalk[bK])
    k_err_oct=max(k_err_oct,abs(k_f-k_m))
    print(f"  [{i}] det: {fd:+d}/{md:+d}  n_err={float(np.linalg.norm(n_m-n_f_pyz)):.2e}  "
          f"k_fwd={k_f:.4f}  k_mir={k_m:.4f}")

assert det_mis == 0,   f"det_sign mismatches (N=8): {det_mis}"
assert n_err_oct < 1e-10, f"n P_yz oct max_err={n_err_oct}"
assert k_err_oct < 1e-8,  f"kappa oct max_err={k_err_oct}"
assert is_valid_kappa(mu_fo) and is_valid_kappa(mu_mo)
print(f"\n  det_sign gate (N=8): PASS  (0 mismatches)")
print(f"  Sector C P_yz (N=8): PASS  max_err={n_err_oct:.2e}")
print(f"  kappa P_yz (N=8):    PASS  max_err={k_err_oct:.2e}")
print(f"  is_valid_kappa (fwd+mirror, N=8): PASS")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n=== EXP-307 Fork B PASS ===")
print(f"  declaration_hash:                {stored_hash}")
print(f"  H_fwd (bisect_x):                {mu_f1._H[:16]}...")
print(f"  H_mir (bisect_x):                {mu_m1._H[:16]}...")
print(f"  H_fwd_oct:                       {mu_fo._H[:16]}...")
print(f"  H_mir_oct:                       {mu_mo._H[:16]}...")
print(f"  Seed nx={SEED_STALK[8]:.1f}  kappa={SEED_STALK[bK]:.1f}")
print(f"  det_sign gate (N=2):             PASS")
print(f"  Sector B P_yz:                   PASS  err={bx_err_max:.2e}")
print(f"  Sector C P_yz closure:           PASS  max_err={n_err_max:.2e}")
print(f"  kappa P_yz invariance (N=2):     PASS  max_err={kappa_err_max:.2e}")
print(f"  kappa P_yz invariance (N=8):     PASS  max_err={k_err_oct:.2e}")
print(f"  is_valid_kappa (all states):     PASS")
print(f"  kappa invariance proof: P_yz preserves bbox extents -> kappa = f(extents) invariant")
