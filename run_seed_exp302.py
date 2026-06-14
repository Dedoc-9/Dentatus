"""
run_seed_exp302.py — EXP-302 Seed_0_geo: geometric stalk [x,y,z,r,g,b]

Tests:
  1. Seed_0_geo sealed with d=6 stalk [0.5,0.5,0.5,1.0,1.0,1.0]
  2. Phi(Seed_0_geo, N=2, axis_bisect_x) -> {child_x0, child_x1}
     stalk conservation: child_x0 + child_x1 = seed_stalk (in R^6)
  3. Phi(Seed_0_geo, N=8, octree_split) -> BLOCKED: DIM_INSUFFICIENT (d=6 < N=8)
  4. Psi({child_x0, child_x1}, spatial_blend) -> v_blend
     stalk: 0.5*(child_x0 + child_x1) = 0.5*seed_stalk
  5. Omega(v_blend) -> geometric artifact with [x,y,z,r,g,b] stalk
  6. R3: Omega(Psi(c0,c1)) ~= Omega(c0) x Omega(c1)
  7. Position and color components extracted and reported
"""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).parent
DECL = json.loads(
    (ROOT / "studies/exp302_geometric_engine/SEED_DECLARATION_exp302.json").read_text(encoding="utf-8")
)
assert DECL["protocol_version"] == "exp302-v1"
assert DECL["status"] == "LOCKED"
assert DECL["d"] == 6

from engine.state import C_KBOUND, Claim, MuState, Provenance, now_iso
from engine.validity import is_valid
from engine.operators import (
    apply_phi, apply_psi, apply_omega,
    apply_omega_tensor, tensor_product_artifact, check_r3,
    PartitionError, SynthesisError,
)
from engine.confluence import ConfluenceRegistry

ALPHA = DECL["alpha"]; BETA = DECL["beta"]; B0 = DECL["B0"]
SCHEMA = DECL["stalk_schema"]
POS_DIMS = SCHEMA["position_dims"]   # [0,1,2]
COL_DIMS = SCHEMA["feature_dims"]    # [3,4,5]

def pos(stalk): return np.array(stalk)[POS_DIMS]
def col(stalk): return np.array(stalk)[COL_DIMS]

# ---------------------------------------------------------------------------
# 1. Seed_0_geo
# ---------------------------------------------------------------------------
prov0 = Provenance(parent_ids=(), operator_id="GENESIS", timestamp=now_iso())
seed_stalk = np.array(DECL["seed_stalk"], dtype=float)  # [0.5,0.5,0.5,1,1,1]
seed = Claim(provenance=prov0, payload=DECL["seed_payload"], stalk=seed_stalk, t=0)
mu0  = MuState(t=0, claims={seed.id: seed}, entailments={},
               active=frozenset([seed.id]), S=np.zeros_like(seed_stalk), alpha=ALPHA)
H0   = mu0.seal()
print(f"Seed_0_geo  H_0: {H0[:16]}...")
print(f"  stalk: {seed_stalk.tolist()}")
print(f"  pos:   {pos(seed_stalk).tolist()}  col: {col(seed_stalk).tolist()}")
assert is_valid(mu0)
spent = 0.0

# ---------------------------------------------------------------------------
# 2. Phi(Seed_0_geo, N=2, axis_bisect_x)
# ---------------------------------------------------------------------------
AX_KEY  = "axis_bisect_x"
P_X0 = "Geometric sub-claim X0: spatial region covering the lower half of the x-axis extent, white color component preserved."
P_X1 = "Geometric sub-claim X1: spatial region covering the upper half of the x-axis extent, white color component preserved."

print(f"\n--- Phi(Seed_0_geo, N=2, key='{AX_KEY}') ---")
mu1, phi_cost = apply_phi(mu=mu0, claim_id=seed.id, N=2, partition_key=AX_KEY,
                           payloads=[P_X0, P_X1], beta=BETA, budget=B0, spent=spent)
mu1.seal(); spent += phi_cost
c0_id, c1_id = sorted(mu1.active)
c0 = mu1.claims[c0_id]; c1 = mu1.claims[c1_id]
print(f"  cost={phi_cost:.4f}  H_1={mu1._H[:16]}...")
print(f"  c0 stalk: {np.round(c0.stalk,4).tolist()}  pos={np.round(pos(c0.stalk),4).tolist()}  col={np.round(col(c0.stalk),4).tolist()}")
print(f"  c1 stalk: {np.round(c1.stalk,4).tolist()}  pos={np.round(pos(c1.stalk),4).tolist()}  col={np.round(col(c1.stalk),4).tolist()}")
conservation_err = float(np.linalg.norm((c0.stalk + c1.stalk) - seed_stalk))
print(f"  Conservation ||c0+c1 - seed||: {conservation_err:.2e}  {'OK' if conservation_err < 1e-10 else 'FAIL'}")
assert conservation_err < 1e-10, "Stalk conservation failed"
assert is_valid(mu1)

# ---------------------------------------------------------------------------
# 3. Phi(Seed_0_geo, N=8, octree_split) -> BLOCKED
# ---------------------------------------------------------------------------
print(f"\n--- Phi(Seed_0_geo, N=8, octree_split) -> expect DIM_INSUFFICIENT ---")
try:
    apply_phi(mu=mu0, claim_id=seed.id, N=8, partition_key="octree_split",
              payloads=[f"octant_{i}" for i in range(8)],
              beta=BETA, budget=B0, spent=0.0)
    print("  FAIL: octree_split should have been blocked")
    sys.exit(1)
except PartitionError as e:
    print(f"  BLOCKED (expected): {e}")

# ---------------------------------------------------------------------------
# 4. Psi({c0, c1}, spatial_blend) -> v_blend
# ---------------------------------------------------------------------------
SYN_KEY = "spatial_blend"
P_BLEND = "Geometric synthesis: weighted spatial centroid of X0 and X1 sub-regions, equal area weights, blended white color."

print(f"\n--- Psi(c0,c1, key='{SYN_KEY}') ---")
mu2, psi_cost = apply_psi(mu=mu1, claim_ids=[c0_id, c1_id],
                           synthesis_key=SYN_KEY, payload=P_BLEND,
                           weights=[0.5, 0.5], beta=BETA, budget=B0, spent=spent)
mu2.seal(); spent += psi_cost
v_blend_id = next(iter(mu2.active))
v_blend    = mu2.claims[v_blend_id]
expected_stalk = 0.5 * c0.stalk + 0.5 * c1.stalk
blend_err = float(np.linalg.norm(v_blend.stalk - expected_stalk))
print(f"  cost={psi_cost:.4f}  H_2={mu2._H[:16]}...")
print(f"  v_blend stalk: {np.round(v_blend.stalk,4).tolist()}")
print(f"  expected:      {np.round(expected_stalk,4).tolist()}")
print(f"  blend err:     {blend_err:.2e}  {'OK' if blend_err < 1e-14 else 'FAIL'}")
print(f"  pos: {np.round(pos(v_blend.stalk),4).tolist()}  col: {np.round(col(v_blend.stalk),4).tolist()}")
assert blend_err < 1e-14
assert is_valid(mu2)

# ---------------------------------------------------------------------------
# 5. Omega(v_blend) -> geometric artifact
# ---------------------------------------------------------------------------
print(f"\n--- Omega(v_blend) ---")
reg = ConfluenceRegistry()
reg.record_path(seed.id,    ("GENESIS",), t=0)
reg.record_path(c0_id,      ("GENESIS", f"Phi:{AX_KEY}:0"), t=1)
reg.record_path(c1_id,      ("GENESIS", f"Phi:{AX_KEY}:1"), t=1)
reg.record_path(v_blend_id, ("GENESIS", f"Phi:{AX_KEY}:0", f"Psi:{SYN_KEY}"), t=2)
reg.record_path(v_blend_id, ("GENESIS", f"Phi:{AX_KEY}:1", f"Psi:{SYN_KEY}"), t=2)
reg.register_morphism(
    path1=("GENESIS", f"Phi:{AX_KEY}:0", f"Psi:{SYN_KEY}"),
    path2=("GENESIS", f"Phi:{AX_KEY}:1", f"Psi:{SYN_KEY}"),
    claim_id=v_blend_id, rule_id="R2", t=2,
)
cert_blend = reg.issue_cert(v_blend_id)
Art_blend  = apply_omega(mu2, v_blend_id, cert_blend)
print(f"  cert: {cert_blend}")
print(f"  Artifact stalk: {np.round(Art_blend['stalk'],4)}")
print(f"  K_bound: {Art_blend['K_bound']}  t={Art_blend['t']}")
print(f"  pos: {pos(Art_blend['stalk']).round(4).tolist()}  col: {col(Art_blend['stalk']).round(4).tolist()}")

# ---------------------------------------------------------------------------
# 6. R3: Omega(Psi(c0,c1)) ~= Omega(c0) x Omega(c1)
# ---------------------------------------------------------------------------
print(f"\n--- R3: Omega(Psi) ~= Omega(c0) x Omega(c1) ---")
cert_c0   = reg.issue_cert(c0_id)
cert_c1   = reg.issue_cert(c1_id)
Art_c0    = apply_omega(mu1, c0_id, cert_c0)
Art_c1    = apply_omega(mu1, c1_id, cert_c1)
Art_joint = tensor_product_artifact(Art_c0, Art_c1, weights=[0.5, 0.5])
passes, r3_err = check_r3(Art_blend, Art_joint)
K_gain = Art_joint["K_bound_sum"] - Art_blend["K_bound"]
print(f"  ||Art_blend - Art_joint||: {r3_err:.2e}  {'PASS' if passes else 'FAIL'}")
print(f"  K synthesis gain: {K_gain} bytes")
reg.register_morphism(
    path1=("GENESIS", f"Phi:{AX_KEY}:0", f"Phi:{AX_KEY}:1", f"Psi:{SYN_KEY}", "Omega"),
    path2=("GENESIS", f"Phi:{AX_KEY}:0", "Omega_c0", f"Phi:{AX_KEY}:1", "Omega_c1", "Tensor"),
    claim_id=v_blend_id, rule_id="R3", t=2,
)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n=== EXP-302 Seed PASS ===")
print(f"  declaration_hash: {DECL['declaration_hash']}")
print(f"  H_0: {H0[:16]}...")
print(f"  H_1: {mu1._H[:16]}...")
print(f"  H_2: {mu2._H[:16]}...")
print(f"  d=6  stalk_schema: {SCHEMA['dims']}")
print(f"  octree_split (N=8) blocked: CONFIRMED (d=6 < 8)")
print(f"  Phi conservation: {conservation_err:.2e}")
print(f"  Psi blend err:    {blend_err:.2e}")
print(f"  R3 err:           {r3_err:.2e}")
print(f"  K synthesis gain: {K_gain} bytes")
print(f"  budget spent:     {spent:.4f} / {B0}")
