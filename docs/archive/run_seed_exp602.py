"""
run_seed_exp602.py -- Fork A: EXP-602 Bit-Stable Semantic Compiler

Protocol: exp602-v1
Declaration hash: 7753731c596ef389d92449092d15f94f38a1ba3f66cba237ba980a32190b6abd

H_verified is now the realized-state content address (W,Z,S), bit-stable via EXP-601, and is
issued only when the manifold firewall (is_manifold_501, eps=0.8) passes. An LLM that "prompts"
a world receives a permanent, unique address for that verified reality.

Tests [1-10]: see SEED_DECLARATION_exp602.json assertions_fork_A.
"""
import sys, os, json, hashlib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dentatus import api, semantic, core

DECL_HASH = "7753731c596ef389d92449092d15f94f38a1ba3f66cba237ba980a32190b6abd"
DECL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "studies/exp602_semantic_compiler/SEED_DECLARATION_exp602.json")
with open(DECL_PATH) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DECL_HASH
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

INTENT = {"title": "docking_bay",
          "seed": {"density": 1.0, "material": [0.55, 0.57, 0.62], "normal": [0, 0, 1],
                   "curvature": 2.0, "stress": {"axes": [3.0, 2.0, 0.4], "plane": "xy", "tilt_deg": 35}},
          "bbox": [[0, 0, 0], [1, 1, 1]], "zeeman": {"focus": [0.5, 0.5, 0.0], "budget": 2048}}

r1 = api.observe({"op": "observe", "intent": INTENT, "steps": 8})
r2 = api.observe({"op": "observe", "intent": INTENT, "steps": 8})
r3 = api.observe({"op": "observe", "intent": INTENT, "steps": 8})

assert r1["H_verified"] == r2["H_verified"] == r3["H_verified"] and r1["H_verified"] is not None
print(f"[2] PASS  H_verified bit-stable 3x = {r1['H_verified'][:16]}...")

assert r1["H_verified"] == r1["H_state"]
print(f"[3] PASS  admissible -> H_verified == H_state (realized-state address)")

assert r1["H_decl"] != r1["H_state"]
print(f"[4] PASS  H_decl (recipe {r1['H_decl'][:10]}) != H_state (reality {r1['H_state'][:10]})")

# [5] firewall-gating contract
gated_ok = (r1["H_verified"] is None) == (not r1["firewall"]["is_manifold_501"])
assert gated_ok and r1["firewall"]["is_manifold_501"]
print(f"[5] PASS  firewall-gating contract: (H_verified is None) iff (not is_manifold_501)")

# [6] sensitivity
i2 = dict(INTENT, seed=dict(INTENT["seed"], density=2.0))
r4 = api.observe({"op": "observe", "intent": i2, "steps": 8})
assert r4["H_verified"] != r1["H_verified"]
print(f"[6] PASS  different intent -> different H_verified ({r4['H_verified'][:10]})")

# [7] idempotent content address
assert r1["H_verified"] == api.observe({"op": "observe", "intent": INTENT, "steps": 8})["H_verified"]
print(f"[7] PASS  idempotent content address (same intent -> same reality id; dedup key)")

# [8] end-to-end determinism
d_a = semantic.compile_intent(INTENT)["declaration_hash"]
d_b = semantic.compile_intent(INTENT)["declaration_hash"]
assert d_a == d_b and r1["H_state"] == r2["H_state"]
print(f"[8] PASS  end-to-end determinism: H_decl stable AND H_state stable")

# [9] L2 invertible log-Cholesky round-trip
Sigma = semantic.sigma_from_semantics([3.0, 2.0, 0.4], "xy", 35)
sD = semantic.stalk_D_from_sigma(Sigma)
stalk = np.concatenate([np.zeros(12), sD])
L_eng, Sigma_eng = core.cholesky_from_stalk_401(stalk)
err = float(np.max(np.abs(Sigma_eng - Sigma)))
assert err < 1e-12 and core.is_valid_covariance_401(stalk)
print(f"[9] PASS  invertible log-Cholesky: Sigma->stalk->Sigma round-trip err={err:.1e} (PD valid)")

# [10] realized-state dependence on geometry-altering parameter
i3 = dict(INTENT, zeeman={"focus": [0.5, 0.5, 0.0], "budget": 256})  # lower budget -> different octree
r5 = api.observe({"op": "observe", "intent": i3, "steps": 8})
assert r5["observables"]["n_leaves"] != r1["observables"]["n_leaves"] or r5["H_state"] != r1["H_state"]
print(f"[10] PASS  realized-state depends on geometry (budget {2048}->{256}: leaves {r1['observables']['n_leaves']}->{r5['observables']['n_leaves']}, distinct H_state)")

print(f"\n=== EXP-602 Fork A: 10/10 PASS ===")
print(f"    H_verified = firewall-gated realized-state address; bit-stable; idempotent dedup key")
print(f"    docking_bay reality id = {r1['H_verified'][:16]}...  (B_ent={r1['observables']['B_ent']} < 0.8)")
