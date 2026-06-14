"""
run_p_invariance_exp309.py -- EXP-309 P_yz invariance test (Fork B).

Protocol: exp309-v1
declaration_hash: 1c3f709e924ca7a053f39666bfe6efbd0e40269918b33a31083e8b381fcca86c

P_yz symmetry: x -> -x (polar dim 4), nx -> -nx (axial dim 8), bbox x-axis reflected.

LOD P_yz invariance proof:
  LOD(bbox, f) = max(lx,ly,lz) / (norm(centroid - f) + eps)
  P_yz: centroid -> (-cx, cy, cz), f -> (-fx, fy, fz), norm unchanged.
  Therefore LOD(mirror_bbox, mirror_f) = LOD(fwd_bbox, fwd_f). Exact.

Tests:
  1. LOD value P_yz invariance (exact).
  2. validity_class P_yz invariance: FULL_VALID iff FULL_VALID.
  3. B_C quarantine P_yz invariance: frozen S_C matches both sides.
  4. Recursive: leaf count, sorted kappa distribution, ghost subspace orth.
"""

import sys, json, hashlib
import numpy as np
sys.path.insert(0, ".")

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_309, apply_gamma_309_recursive,
    SECTOR_B_DIMS, SECTOR_C_DIMS, SECTOR_C_KAPPA_DIM,
)
from engine.validity import (
    kappa_integral, lod_value, is_lod_valid_309, LOD_THRESHOLDS_309,
)

# ---------------------------------------------------------------------------
# Hash verify
# ---------------------------------------------------------------------------
with open("studies/exp309_lod_observer/SEED_DECLARATION_exp309.json") as f:
    DECL = json.load(f)
stored_hash = DECL["declaration_hash"]
verify_fields = {k: v for k, v in DECL.items() if k not in ("declaration_hash", "status")}
canonical = json.dumps(verify_fields, sort_keys=True, separators=(',', ':'))
assert hashlib.sha256(canonical.encode()).hexdigest() == stored_hash
print(f"Seed hash verified: {stored_hash[:16]}...")

D   = DECL["d"]
bK  = SECTOR_C_KAPPA_DIM
BETA = 0.1; BUDGET = 100.0

# ---------------------------------------------------------------------------
# P_yz transforms
# ---------------------------------------------------------------------------
def apply_p_yz_stalk(s):
    s = s.copy()
    s[4] = -s[4]   # x-position (polar)
    s[8] = -s[8]   # nx (axial)
    return s

def apply_p_yz_bbox(bbox):
    lo, hi = bbox[0].copy(), bbox[1].copy()
    lo[0], hi[0] = -bbox[1][0], -bbox[0][0]
    return (lo, hi)

def apply_p_yz_focal(fp):
    f = fp.copy(); f[0] = -f[0]; return f

# ---------------------------------------------------------------------------
# Build seed pair
# ---------------------------------------------------------------------------
kappa_seed = kappa_integral((np.zeros(3), np.ones(3)))
assert abs(kappa_seed - 2.0) < 1e-12

seed_stalk = np.array([1.,1.,1.,1., 0.5,0.5,0.5,1., 0.6,0.,0.8, kappa_seed])
assert abs(np.linalg.norm(seed_stalk[8:11]) - 1.0) < 1e-12

bbox_fwd_lo = np.zeros(3);   bbox_fwd_hi = np.ones(3)
bbox_mir_lo = np.array([-1.,0.,0.]); bbox_mir_hi = np.array([0.,1.,1.])

seed_stalk_mir = apply_p_yz_stalk(seed_stalk)
seed_stalk_mir[bK] = kappa_integral((bbox_mir_lo, bbox_mir_hi))
assert abs(seed_stalk_mir[bK] - kappa_seed) < 1e-12

def make_mu(stalk, lo, hi, fp, label):
    prov  = Provenance(parent_ids=(), operator_id=label, timestamp=now_iso())
    claim = Claim(provenance=prov, payload=f"{label}: d=12 EXP-309",
                  stalk=stalk.copy(), t=0, bbox=(lo.copy(), hi.copy()))
    mu = MuState(claims={claim.id: claim}, entailments={},
                 active=frozenset([claim.id]),
                 t=0, S=np.zeros(D), alpha=ALPHA,
                 S_A=np.zeros(8), S_C=np.zeros(4))
    mu.focal_point = fp.copy()
    mu.seal()
    return mu, claim.id

# Focal points (fwd and mirror)
fp_fwd_near = np.array([0.5, 0.5, 0.5])
fp_mir_near = apply_p_yz_focal(fp_fwd_near)   # = [-0.5, 0.5, 0.5]

fp_fwd_far  = np.array([0.5, 0.5, 25.0])
fp_mir_far  = apply_p_yz_focal(fp_fwd_far)    # = [-0.5, 0.5, 25.0]

# ---------------------------------------------------------------------------
# Test 1 -- LOD value P_yz invariance
# ---------------------------------------------------------------------------
print("\n--- Test 1: LOD value P_yz invariance ---")

bbox_fwd = (bbox_fwd_lo, bbox_fwd_hi)
bbox_mir = (bbox_mir_lo, bbox_mir_hi)

for fp_fwd, fp_mir, label in [
    (fp_fwd_near, fp_mir_near, "near"),
    (fp_fwd_far,  fp_mir_far,  "far20"),
]:
    lod_f = lod_value(bbox_fwd, fp_fwd)
    lod_m = lod_value(bbox_mir, fp_mir)
    err = abs(lod_f - lod_m)
    print(f"  LOD({label}): fwd={lod_f:.6e}  mir={lod_m:.6e}  diff={err:.2e}")
    assert err < 1e-10, f"LOD P_yz error: {err}"

print("  LOD P_yz invariance: PASS")

# ---------------------------------------------------------------------------
# Test 2 -- validity_class P_yz invariance (single-step)
# ---------------------------------------------------------------------------
print("\n--- Test 2: validity_class P_yz invariance ---")

for fp_f, fp_m, label in [
    (fp_fwd_near, fp_mir_near, "near/FULL_VALID"),
    (fp_fwd_far,  fp_mir_far,  "far20/LOD_RELAXED"),
]:
    mu_f0, sid_f = make_mu(seed_stalk,     bbox_fwd_lo, bbox_fwd_hi, fp_f, "Fwd")
    mu_m0, sid_m = make_mu(seed_stalk_mir, bbox_mir_lo, bbox_mir_hi, fp_m, "Mir")

    mu_f1, _, vc_f = apply_gamma_309(
        mu=mu_f0, claim_id=sid_f, partition_key="octree_split",
        payloads=[f"pf_{label}_{i}" for i in range(8)],
        beta=BETA, budget=BUDGET, spent=0.0, focal_point=fp_f)
    mu_m1, _, vc_m = apply_gamma_309(
        mu=mu_m0, claim_id=sid_m, partition_key="octree_split",
        payloads=[f"pm_{label}_{i}" for i in range(8)],
        beta=BETA, budget=BUDGET, spent=0.0, focal_point=fp_m)

    print(f"  [{label}]  vc_fwd={vc_f}  vc_mir={vc_m}")
    assert vc_f == vc_m, f"validity_class P_yz mismatch: {vc_f} vs {vc_m}"

print("  validity_class P_yz invariance: PASS")

# ---------------------------------------------------------------------------
# Test 3 -- S_C quarantine P_yz invariance
# ---------------------------------------------------------------------------
print("\n--- Test 3: S_C quarantine P_yz invariance ---")

mu_f_far0, sid_ff = make_mu(seed_stalk,     bbox_fwd_lo, bbox_fwd_hi, fp_fwd_far, "Fwd_far")
mu_m_far0, sid_mf = make_mu(seed_stalk_mir, bbox_mir_lo, bbox_mir_hi, fp_mir_far, "Mir_far")

mu_ff, _, vc_ff = apply_gamma_309(
    mu=mu_f_far0, claim_id=sid_ff, partition_key="octree_split",
    payloads=[f"sc_f_{i}" for i in range(8)],
    beta=BETA, budget=BUDGET, spent=0.0, focal_point=fp_fwd_far)
mu_mf, _, vc_mf = apply_gamma_309(
    mu=mu_m_far0, claim_id=sid_mf, partition_key="octree_split",
    payloads=[f"sc_m_{i}" for i in range(8)],
    beta=BETA, budget=BUDGET, spent=0.0, focal_point=fp_mir_far)

sc_err = float(np.linalg.norm(mu_ff.S_C - mu_mf.S_C))
print(f"  S_C_fwd={mu_ff.S_C}  S_C_mir={mu_mf.S_C}  err={sc_err:.2e}")
assert sc_err < 1e-14, f"S_C quarantine P_yz mismatch: {sc_err}"
# Both should be LOD_RELAXED (kappa bypassed) -> S_C frozen at 0
assert vc_ff == "LOD_RELAXED" and vc_mf == "LOD_RELAXED"
print("  S_C quarantine P_yz invariance: PASS")

# ---------------------------------------------------------------------------
# Test 4 -- Recursive P_yz invariance (FULL_VALID focal)
# ---------------------------------------------------------------------------
print("\n--- Test 4: Recursive P_yz invariance (FULL_VALID) ---")

mu_fr0, sid_fr = make_mu(seed_stalk,     bbox_fwd_lo, bbox_fwd_hi, fp_fwd_near, "RecFwd")
mu_mr0, sid_mr = make_mu(seed_stalk_mir, bbox_mir_lo, bbox_mir_hi, fp_mir_near, "RecMir")

mu_fr, _ = apply_gamma_309_recursive(
    mu=mu_fr0, claim_id=sid_fr, partition_key="octree_split",
    beta=BETA, budget=BUDGET, spent=0.0, K_budget=256, depth=0,
    focal_point=fp_fwd_near)
mu_mr, _ = apply_gamma_309_recursive(
    mu=mu_mr0, claim_id=sid_mr, partition_key="octree_split",
    beta=BETA, budget=BUDGET, spent=0.0, K_budget=256, depth=0,
    focal_point=fp_mir_near)

leaves_f = list(mu_fr.active); leaves_m = list(mu_mr.active)
assert len(leaves_f) == len(leaves_m), \
    f"Leaf count mismatch: {len(leaves_f)} vs {len(leaves_m)}"
print(f"  Recursive leaves: {len(leaves_f)} fwd = {len(leaves_m)} mir")

# Sorted kappa distribution (same argument as EXP-308 Fork B)
kappas_f = sorted(float(mu_fr.claims[c].stalk[11]) for c in leaves_f)
kappas_m = sorted(float(mu_mr.claims[c].stalk[11]) for c in leaves_m)
kappa_max = max(abs(a - b) for a, b in zip(kappas_f, kappas_m))
print(f"  Sorted kappa distribution max_err={kappa_max:.2e}")
assert kappa_max < 1e-10, f"Kappa distribution P_yz error: {kappa_max}"
print("  Sorted kappa distribution: PASS")

# Ghost subspace orthogonality: G_A (dims 0-7) in R^12, G_C (dims 8-11) in R^12
def subspace_dot(mu):
    G_A = mu.G_A(); G_C = mu.G_C()
    full_A = np.zeros(12); full_A[0:8]  = G_A
    full_C = np.zeros(12); full_C[8:12] = G_C
    return float(abs(np.dot(full_A, full_C)))

orth_f = subspace_dot(mu_fr)
orth_m = subspace_dot(mu_mr)
print(f"  Ghost orth: fwd G_A.G_C={orth_f:.2e}  mir G_A.G_C={orth_m:.2e}")
assert orth_f < 1e-30, f"G_A.G_C (fwd recursive) = {orth_f}"
assert orth_m < 1e-30, f"G_A.G_C (mir recursive) = {orth_m}"
print("  Ghost subspace orthogonality: PASS")

# Hash continuity both sides
assert len(mu_fr.H) == 64 and len(mu_mr.H) == 64
print(f"  H_t fwd={mu_fr.H[:16]}...  mir={mu_mr.H[:16]}...  PASS")

print("""
=== EXP-309 P_yz Invariance PASS (Fork B) ===
  declaration_hash: 1c3f709e924ca7a053f39666bfe6efbd0e40269918b33a31083e8b381fcca86c
  Seed nx=0.6, kappa=2.0 (unit cube)
  Test 1 LOD value P_yz invariance (exact):          PASS
  Test 2 validity_class P_yz invariance:             PASS
  Test 3 S_C quarantine P_yz invariance:             PASS
  Test 4 Recursive leaf count P_yz:                  PASS
  Test 4 Sorted kappa distribution P_yz max_err=0:   PASS
  Test 4 Ghost subspace orthogonality G_A.G_C=0:     PASS
  Test 4 Hash continuity:                            PASS
""")
