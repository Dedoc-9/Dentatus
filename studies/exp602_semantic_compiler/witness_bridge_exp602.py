"""
witness_bridge_exp602.py — cross-project epistemic test of EXP-602.

Wraps the dentatus L1 `observe()` output as an executable-epistemics witness Artifact and runs it
through the witness interpretive firewall. This is a BRIDGE, not a merge: neither project imports
the other internally. dentatus lives in Reality_Engine (AGPL-3.0); witness_core lives in the
sibling MCL_OBS2 (executable-epistemics, AGPL-3.0, same author). Both reached via sibling paths.

Demonstrates:
  * EXP-602 observables are pure numerics/structural indices -> pass the witness firewall.
  * The firewall verdict (is_manifold_501) is an INTERPRETATION, kept out of witness `data`;
    admissibility is carried as the numeric bound worst_ratio <= epsilon_manifold.
  * The witness firewall catches a naive verdict leak (`valid: True`) -> WitnessViolation.
"""
import os, sys
os.environ.setdefault("SOURCE_DATE_EPOCH", "0")
HERE = os.path.dirname(os.path.abspath(__file__))
REALITY = os.path.dirname(os.path.dirname(HERE))           # Reality_Engine/
MCL = os.path.join(os.path.dirname(REALITY), "MCL_OBS2")   # sibling toolkit
sys.path.insert(0, REALITY)
sys.path.insert(0, MCL)

from dentatus import api, core                              # noqa: E402
from witness_core import Artifact, WitnessViolation         # noqa: E402

INTENT = {"title": "docking_bay",
          "seed": {"density": 1.0, "material": [0.55, 0.57, 0.62], "normal": [0, 0, 1],
                   "curvature": 2.0, "stress": {"axes": [3.0, 2.0, 0.4], "plane": "xy", "tilt_deg": 35}},
          "bbox": [[0, 0, 0], [1, 1, 1]], "zeeman": {"focus": [0.5, 0.5, 0.0], "budget": 2048}}

resp = api.observe({"op": "observe", "intent": INTENT, "steps": 8})
obs = resp["observables"]

# PURE-OBSERVABLE data: numerics + structural addresses only. NO firewall verdict here.
data = {
    "B_A": obs["B_A"], "B_D": obs["B_D"], "B_ent": obs["B_ent"],
    "B_ent_spectral": obs["B_ent_spectral"], "lambda_2": obs["lambda_2"],
    "n_leaves": obs["n_leaves"], "n_edges": obs["n_edges"], "beta_Z_eff": obs["beta_Z_eff"],
    "worst_ratio": resp["firewall"]["worst_ratio"],
    "epsilon_manifold": resp["firewall"]["epsilon"],
    "H_state": resp["H_state"], "H_decl": resp["H_decl"], "H_verified": resp["H_verified"],
}
provenance = {
    "engine_protocol": core.ENGINE_PROTOCOL,
    "declaration_hash": resp["H_decl"],
    "source_date_epoch": os.environ["SOURCE_DATE_EPOCH"],
    "operator": "dentatus.api.observe (EXP-602)",
}
art = Artifact(
    data=data, provenance=provenance, claim_class="manifold_observation",
    validity_scope={
        "certifies": ("bit-stable realized-state content address under deterministic seeding "
                      "(EXP-601) and degree-normalized manifold observation; admissibility is the "
                      "numeric bound worst_ratio <= epsilon_manifold"),
        "domain": "single-seed octree", "epsilon_manifold": resp["firewall"]["epsilon"],
    },
    forbidden_interpretations=[
        "B_ent / B_ent_spectral are structural deformation ratios, not quality/health/correctness scores",
        "H_verified is a content address (structural index), not a semantic label or endorsement",
        "worst_ratio <= epsilon_manifold is a manifold-continuity elastic bound, not safety or correctness",
        "lambda_2 is algebraic connectivity, not a measure of world 'goodness'",
    ],
)
assert art.verify_chain(), "[A] FAIL: witness chain hash mismatch"
print(f"[A] PASS  EXP-602 observables pass the witness interpretive firewall")
print(f"          claim_class={art['claim_class']}  chain={art['chain_hash']}  verify_chain={art.verify_chain()}")
print(f"          reality id H_verified={data['H_verified'][:16]}...  B_ent={data['B_ent']} worst_ratio={data['worst_ratio']}")

# NEGATIVE: a naive verdict field is rejected by the firewall.
try:
    Artifact(data={**data, "valid": True}, provenance=provenance, claim_class="x",
             validity_scope={"certifies": "y"}, forbidden_interpretations=["z"])
    raise SystemExit("[B] FAIL: witness firewall did not catch the verdict field")
except WitnessViolation as e:
    print(f"[B] PASS  witness firewall caught verdict leak -> WitnessViolation({e})")

# bit-stability survives the witness wrapper (re-realize -> identical reality id)
resp2 = api.observe({"op": "observe", "intent": INTENT, "steps": 8})
assert resp2["H_verified"] == data["H_verified"]
print(f"[C] PASS  reality id bit-stable through the witness bridge (idempotent content address)")

print(f"\n=== EXP-602 witness bridge: 3/3 PASS ===")
print(f"    dentatus observables are epistemically pure (no verdict leak); firewall verdict held")
print(f"    in validity_scope, not data; Clean Room preserved (cross-project bridge, no merge)")
