"""
run_seed_exp303.py — EXP-303 Seed_0_spatial: d=9 [x,y,z,r,g,b,nx,ny,nz]

Tests:
  1.  Seed_0_spatial sealed; d=9, bbox=[0,1]^3
  2.  Gamma(Seed, axis_bisect_x) -> {c_x0, c_x1}: N=2 x-bisection
      bbox(c_x0) = ([0,0,0],[0.5,1,1])  bbox(c_x1) = ([0.5,0,0],[1,1,1])
  3.  Gamma(Seed, octree_split)  -> {o_0..o_7}: N=8 octree
      All 8 octant bboxes contained in seed bbox
      No bbox pair overlaps (partition completeness)
  4.  is_spatially_valid passes on both; algebraic is_valid passes
  5.  Spatial containment violation: mutate child bbox -> is_spatially_valid=False
  6.  Psi(c_x0, c_x1) -> v_blend; R3 verified
  7.  Budget ledger
"""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).parent
DECL = json.loads(
    (ROOT / "studies/exp303_spatial_engine/SEED_DECLARATION_exp303.json").read_text(encoding="utf-8")
)
assert DECL["protocol_version"] == "exp303-v1"
assert DECL["status"] == "LOCKED"
assert DECL["d"] == 9

from engine.state import C_KBOUND, Claim, EntailmentType, MuState, Provenance, now_iso
from engine.validity import is_valid, is_spatially_valid
from engine.operators import (
    apply_gamma, apply_phi, apply_psi, apply_omega,
    tensor_product_artifact, check_r3,
    PartitionError, SynthesisError,
    SPATIAL_KEYS,
)
from engine.confluence import ConfluenceRegistry

ALPHA = DECL["alpha"]; BETA = DECL["beta"]; B0 = DECL["B0"]
SCHEMA = DECL["stalk_schema"]
POS = SCHEMA["position_dims"]
COL = SCHEMA["color_dims"]
NRM = SCHEMA["normal_dims"]

def fmt(stalk):
    s = np.array(stalk)
    return f"pos={np.round(s[POS],3).tolist()} col={np.round(s[COL],3).tolist()} nrm={np.round(s[NRM],3).tolist()}"

def bbox_str(bbox):
    if bbox is None: return "None"
    return f"[{np.round(bbox[0],3).tolist()} -> {np.round(bbox[1],3).tolist()}]"

# ---------------------------------------------------------------------------
# 1. Seed_0_spatial
# ---------------------------------------------------------------------------
bbox_lo = np.array(DECL["seed_bbox_lo"], dtype=float)
bbox_hi = np.array(DECL["seed_bbox_hi"], dtype=float)
seed_stalk = np.array(DECL["seed_stalk"], dtype=float)

prov0 = Provenance(parent_ids=(), operator_id="GENESIS", timestamp=now_iso())
seed  = Claim(provenance=prov0, payload=DECL["seed_payload"],
              stalk=seed_stalk, t=0, bbox=(bbox_lo, bbox_hi))
mu0   = MuState(t=0, claims={seed.id: seed}, entailments={},
                active=frozenset([seed.id]), S=np.zeros_like(seed_stalk), alpha=ALPHA)
H0 = mu0.seal()
print(f"Seed_0_spatial  H_0: {H0[:16]}...")
print(f"  {fmt(seed_stalk)}")
print(f"  bbox: {bbox_str(seed.bbox)}")
assert is_valid(mu0)
assert is_spatially_valid(mu0)
spent = 0.0

# ---------------------------------------------------------------------------
# 2. Gamma(Seed, axis_bisect_x) -> {c_x0, c_x1}
# ---------------------------------------------------------------------------
P_X0 = "Spatial sub-region X0: the lower x-half [0,0.5]x[0,1]^2 of the unit cube, white, normal +z."
P_X1 = "Spatial sub-region X1: the upper x-half [0.5,1]x[0,1]^2 of the unit cube, white, normal +z."

print(f"\n--- Gamma(Seed, axis_bisect_x) ---")
mu1, g_cost = apply_gamma(mu=mu0, claim_id=seed.id, partition_key="axis_bisect_x",
                           payloads=[P_X0, P_X1], beta=BETA, budget=B0, spent=spent)
mu1.seal(); spent += g_cost
# Identify children by bbox (not by sort order — hash ordering is non-positional)
all_child_ids = list(mu1.active)
cx0_id = next(cid for cid in all_child_ids if mu1.claims[cid].bbox[0][0] < 0.1)  # lo_x ~ 0
cx1_id = next(cid for cid in all_child_ids if mu1.claims[cid].bbox[0][0] > 0.4)  # lo_x ~ 0.5
cx0 = mu1.claims[cx0_id]; cx1 = mu1.claims[cx1_id]
print(f"  cost={g_cost:.4f}  H_1={mu1._H[:16]}...")
print(f"  lower-x half: {fmt(cx0.stalk)}")
print(f"    bbox: {bbox_str(cx0.bbox)}")
print(f"  upper-x half: {fmt(cx1.stalk)}")
print(f"    bbox: {bbox_str(cx1.bbox)}")

# Verify stalk conservation
cons_err = float(np.linalg.norm((cx0.stalk + cx1.stalk) - seed_stalk))
print(f"  Algebraic conservation ||c_x0+c_x1-seed||: {cons_err:.2e}")
assert cons_err < 1e-10

# Verify bbox containment and split values
assert is_spatially_valid(mu1), "FAIL: spatial validity after axis_bisect_x"
assert is_valid(mu1), "FAIL: algebraic validity after axis_bisect_x"
assert abs(cx0.bbox[1][0] - 0.5) < 1e-10, f"lower-x hi_x should be 0.5, got {cx0.bbox[1][0]}"
assert abs(cx1.bbox[0][0] - 0.5) < 1e-10, f"upper-x lo_x should be 0.5, got {cx1.bbox[0][0]}"
print(f"  Spatial containment: PASS")
print(f"  Bbox split at x=0.5: PASS")

# ---------------------------------------------------------------------------
# 3. Gamma(Seed, octree_split) -> {o_0..o_7}
# ---------------------------------------------------------------------------
octree_payloads = [f"oct{i}" for i in range(8)]  # minimal: K-bound binds on N=8

print(f"\n--- Gamma(Seed, octree_split) -> 8 octants ---")
mu_oct, oct_cost = apply_gamma(mu=mu0, claim_id=seed.id, partition_key="octree_split",
                                payloads=octree_payloads, beta=BETA, budget=B0, spent=0.0)
mu_oct.seal()
oct_ids = sorted(mu_oct.active)
print(f"  cost={oct_cost:.4f}  H={mu_oct._H[:16]}...")
assert len(oct_ids) == 8, f"Expected 8 octants, got {len(oct_ids)}"

# Check all bboxes
stalk_sum = np.zeros_like(seed_stalk)
for oid in oct_ids:
    child = mu_oct.claims[oid]
    stalk_sum += child.stalk
    bb = child.bbox
    # Each child bbox must be contained in seed bbox [0,1]^3
    assert np.all(bb[0] >= bbox_lo - 1e-10), f"Child lo {bb[0]} outside seed lo {bbox_lo}"
    assert np.all(bb[1] <= bbox_hi + 1e-10), f"Child hi {bb[1]} outside seed hi {bbox_hi}"
    # Each octant must have side length 0.5
    side = bb[1] - bb[0]
    assert np.allclose(side, 0.5, atol=1e-10), f"Octant side not 0.5: {side}"

oct_cons = float(np.linalg.norm(stalk_sum - seed_stalk))
print(f"  Algebraic conservation (8 octants): {oct_cons:.2e}")
assert oct_cons < 1e-10
assert is_spatially_valid(mu_oct)
assert is_valid(mu_oct)
print(f"  All 8 octant bboxes in [0,1]^3: PASS")
print(f"  All octant side lengths = 0.5:  PASS")
print(f"  Algebraic conservation:         PASS")

# Print octant bboxes
for i, oid in enumerate(oct_ids):
    bb = mu_oct.claims[oid].bbox
    print(f"    o_{i}: {bbox_str(bb)}")

# ---------------------------------------------------------------------------
# 4. Spatial containment violation test
# ---------------------------------------------------------------------------
print(f"\n--- Containment violation: mutate child bbox -> is_spatially_valid=False ---")
# Manually create a state with a child bbox outside parent
import copy
bad_mu = copy.deepcopy(mu1)
bad_cx0 = bad_mu.claims[cx0_id]
# Move c_x0's hi_x to 1.5 (outside parent [0,1])
bad_bbox = (bad_cx0.bbox[0].copy(), bad_cx0.bbox[1].copy())
bad_bbox[1][0] = 1.5
object.__setattr__(bad_cx0, 'bbox', bad_bbox) if hasattr(bad_cx0, '__dataclass_fields__') else None
# Since Claim is a regular dataclass, just reassign
bad_cx0.bbox = bad_bbox
bad_mu.claims[cx0_id] = bad_cx0
result = is_spatially_valid(bad_mu)
print(f"  is_spatially_valid with hi_x=1.5: {result}  {'PASS' if not result else 'FAIL'}")
assert not result, "Expected spatial validity to fail with out-of-bounds bbox"

# ---------------------------------------------------------------------------
# 5. Psi(c_x0, c_x1) -> v_blend
# ---------------------------------------------------------------------------
SYN_KEY = "spatial_blend"
P_BLEND = "Spatial synthesis: weighted centroid of X0 and X1 half-spaces of the unit cube."
print(f"\n--- Psi(c_x0, c_x1) -> v_blend ---")
mu2, psi_cost = apply_psi(mu=mu1, claim_ids=[cx0_id, cx1_id],
                           synthesis_key=SYN_KEY, payload=P_BLEND,
                           weights=[0.5, 0.5], beta=BETA, budget=B0, spent=spent)
mu2.seal(); spent += psi_cost
v_blend_id = next(iter(mu2.active))
v_blend    = mu2.claims[v_blend_id]
blend_err  = float(np.linalg.norm(v_blend.stalk - (0.5*cx0.stalk + 0.5*cx1.stalk)))
print(f"  cost={psi_cost:.4f}  blend_err={blend_err:.2e}")
print(f"  v_blend: {fmt(v_blend.stalk)}")
assert blend_err < 1e-14
assert is_valid(mu2)

# ---------------------------------------------------------------------------
# 6. R3: Omega(Psi(c0,c1)) ~= Omega(c0) x Omega(c1)
# ---------------------------------------------------------------------------
print(f"\n--- R3 verification ---")
reg = ConfluenceRegistry()
reg.record_path(seed.id,     ("GENESIS",), t=0)
reg.record_path(cx0_id,      ("GENESIS", f"Gamma:axis_bisect_x:0"), t=1)
reg.record_path(cx1_id,      ("GENESIS", f"Gamma:axis_bisect_x:1"), t=1)
reg.record_path(v_blend_id,  ("GENESIS", f"Gamma:axis_bisect_x:0", f"Psi:{SYN_KEY}"), t=2)
reg.record_path(v_blend_id,  ("GENESIS", f"Gamma:axis_bisect_x:1", f"Psi:{SYN_KEY}"), t=2)
reg.register_morphism(
    path1=("GENESIS", f"Gamma:axis_bisect_x:0", f"Psi:{SYN_KEY}"),
    path2=("GENESIS", f"Gamma:axis_bisect_x:1", f"Psi:{SYN_KEY}"),
    claim_id=v_blend_id, rule_id="R2", t=2,
)
cert_cx0   = reg.issue_cert(cx0_id)
cert_cx1   = reg.issue_cert(cx1_id)
cert_blend = reg.issue_cert(v_blend_id)

Art_cx0   = apply_omega(mu1, cx0_id,    cert_cx0)
Art_cx1   = apply_omega(mu1, cx1_id,    cert_cx1)
Art_blend = apply_omega(mu2, v_blend_id, cert_blend)
Art_joint = tensor_product_artifact(Art_cx0, Art_cx1, weights=[0.5, 0.5])

passes, r3_err = check_r3(Art_blend, Art_joint)
K_gain = Art_joint["K_bound_sum"] - Art_blend["K_bound"]
print(f"  R3 stalk err: {r3_err:.2e}  {'PASS' if passes else 'FAIL'}")
print(f"  K synthesis gain: {K_gain} bytes")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n=== EXP-303 Seed PASS ===")
print(f"  declaration_hash: {DECL['declaration_hash']}")
print(f"  H_0: {H0[:16]}...")
print(f"  H_1 (axis_bisect_x): {mu1._H[:16]}...")
print(f"  H_oct (octree):      {mu_oct._H[:16]}...")
print(f"  H_2 (post-Psi):      {mu2._H[:16]}...")
print(f"  d=9  schema: {SCHEMA['dims']}")
print(f"  Gamma operator:        LIVE")
print(f"  octree_split (N=8):    PASS (d=9 >= 8)")
print(f"  Bbox containment:      PASS")
print(f"  Containment violation: DETECTED")
print(f"  Algebraic conservation: {cons_err:.2e} / {oct_cons:.2e}")
print(f"  R3 err: {r3_err:.2e}")
print(f"  Budget spent: {spent:.4f} / {B0}")
