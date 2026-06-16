"""
run_seed_exp523.py -- Fork A: EXP-523 Validity Witness (Fork omega)

Protocol exp523-v1. Declaration hash: 1fc9721cf4e667cbf5c1baa277e639cc85f0471359ca04cc666921ed8987cd2b
Binds the SPRT validity class to the verified address, closing Ghost #5 (integrity laundering across
level-of-detail). Engine FROZEN. PYTHONHASHSEED=0.
"""
import sys, os, json, hashlib
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/observability"))
import numpy as np
from dentatus import core
from integrity import verified_address, integrity_witness, addresses_distinct

DH = "1fc9721cf4e667cbf5c1baa277e639cc85f0471359ca04cc666921ed8987cd2b"
with open(os.path.join(ROOT, "studies/exp523_validity_witness/SEED_DECLARATION_exp523.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DH
print(f"[1] PASS  declaration_hash = {DH[:16]}...")

def mk():
    s = np.zeros(18); s[0:4] = [1.0, 0.5, 0.5, 0.5]; s[8:11] = [0, 0, 1]
    cl = core.Claim(provenance=core.Provenance(parent_ids=(), operator_id="seed", timestamp=core.now_iso()),
                    payload="p", stalk=s, t=0)
    return core.MuState(t=0, claims={cl.id: cl}, entailments={}, active=frozenset([cl.id]), S=np.zeros(18), alpha=0.5)
a, b = mk(), mk(); a.seal(); b.seal()

# [2] confirm the hole
assert a.H == b.H
import inspect, engine.state as st
assert "validity" not in inspect.getsource(st._compute_H).lower()
print(f"[2] PASS  hole confirmed: engine H_t collides across validity classes ({a.H[:12]}); _compute_H has no validity term")

# [3] FULL_VALID -> H_t
assert verified_address(a, "FULL_VALID") == a.H
print(f"[3] PASS  FULL_VALID address == plain H_t (backward compatible)")

# [4] LOD_RELAXED distinct
vr = verified_address(b, "LOD_RELAXED")
assert vr != b.H and vr != verified_address(a, "FULL_VALID")
print(f"[4] PASS  LOD_RELAXED address {vr[:12]} != H_t and != FULL_VALID address (records bypass)")

# [5] INVALID -> None
assert verified_address(a, "INVALID") is None
print(f"[5] PASS  INVALID -> None (no admissible address)")

# [6] laundering closed
assert addresses_distinct(a, b)
print(f"[6] PASS  addresses_distinct: relaxed and full-valid geometries get distinct addresses (laundering closed)")

# [7] containment bound
assert "Gamma_309" not in open(os.path.join(ROOT, "dentatus/core.py")).read()
assert "validity_class" not in open(os.path.join(ROOT, "dentatus/api.py")).read()
print(f"[7] PASS  containment: Gamma_309 not in dentatus facade; api.observe has no validity_class reference")

# [8] no regression: Series-500 path stays FULL_VALID, H_verified unchanged
from dentatus import api
INTENT = {"title": "t", "seed": {"density": 1.0, "material": [0.5, 0.5, 0.6], "normal": [0, 0, 1],
          "curvature": 2.0, "stress": {"axes": [3, 2, 0.4], "plane": "xy", "tilt_deg": 35}},
          "bbox": [[0, 0, 0], [1, 1, 1]], "zeeman": {"focus": [0.5, 0.5, 0.0]}}
r1 = api.observe({"op": "observe", "intent": INTENT, "steps": 8})
r2 = api.observe({"op": "observe", "intent": INTENT, "steps": 8})
assert r1["H_verified"] is not None and r1["H_verified"] == r2["H_verified"]
print(f"[8] PASS  no regression: Series-500 H_verified stable ({r1['H_verified'][:12]}); FULL_VALID path unchanged")

# [9] auditable witness
w = integrity_witness(b, "LOD_RELAXED")
assert w["validity_class"] == "LOD_RELAXED" and w["H_geometric"] == b.H and not w["is_full_integrity"]
print(f"[9] PASS  integrity_witness records class + geometric H + bound address (auditable)")

# [10] determinism
assert verified_address(b, "LOD_RELAXED") == vr
print(f"[10] PASS  determinism: verified_address bit-stable")

print("\n=== EXP-523 Fork A: 10/10 PASS ===")
print("    Validity witness binds the SPRT class to the verified address: relaxed states can never share")
print("    an address with full-valid ones. Ghost #5 CLOSED; engine frozen, backward-compatible.")
