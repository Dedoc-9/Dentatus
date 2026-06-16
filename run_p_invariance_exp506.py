"""
run_p_invariance_exp506.py -- Fork B: EXP-506 stitched Fiedler P_yz invariance

Protocol: exp506-v1
Declaration hash: d69b59b3ad635e16a0194e5087fa0aaa6773f378565570d3bedb46cac8d397ed

The realized world is geometry-driven; under a seed x-stalk flip the telemetry is identical, so
the stitched fault structure (|field| multiset, section agreement, seams, counts) is P_yz-invariant.

Tests [1-5]: see SEED_DECLARATION_exp506.json assertions_fork_B.
"""
import sys, os, json, hashlib
os.environ.setdefault("PYTHONHASHSEED", "0")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "game"))
import numpy as np
from dentatus import api, core
from engine.validity import kappa_integral
from observability.sectioned_fiedler import stitched_fiedler, stitch_diagnostics

DECL_HASH = "d69b59b3ad635e16a0194e5087fa0aaa6773f378565570d3bedb46cac8d397ed"
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
          "studies/exp506_stitched_fiedler/SEED_DECLARATION_exp506.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DECL_HASH
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

ks = kappa_integral((np.zeros(3), np.ones(3)))
sf = [1.,1.,1.,1., 0.5,0.5,0.5,1., 0.6,0.,0.8,float(ks), 0.,0.,0.,0.,0.,0.]
sm = list(sf); sm[4] = -sf[4]
B = [1.0, 0.5, 0.3]; nB = float(np.linalg.norm(B)); B = [x/nB for x in B]
def dof(stalk):
    d = {"protocol": "dentatus-intent-v1", "engine_protocol": core.ENGINE_PROTOCOL, "title": "pyz",
         "seed_stalk": [round(float(x), 12) for x in stalk], "bbox": [[0.,0.,0.],[1.,1.,1.]],
         "B": [round(x, 12) for x in B], "K_budget": 2048}
    d["declaration_hash"] = hashlib.sha256(json.dumps(d, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return d
tf = api.observe({"op": "observe", "declaration": dof(sf), "steps": 8, "telemetry": True})["telemetry"]
tm = api.observe({"op": "observe", "declaration": dof(sm), "steps": 8, "telemetry": True})["telemetry"]
af = stitched_fiedler(tf["leaves"]); am = stitched_fiedler(tm["leaves"])
df = stitch_diagnostics(tf["leaves"]); dm = stitch_diagnostics(tm["leaves"])

mf = sorted(round(abs(x), 9) for x in af["field"]); mm = sorted(round(abs(x), 9) for x in am["field"])
assert mf == mm
print(f"[2] PASS  sorted |stitched field| multiset fwd == mir (fault structure P_yz-invariant)")
assert df["section_agreement"] == dm["section_agreement"]
print(f"[3] PASS  section_agreement fwd == mir ({df['section_agreement']*100:.0f}%)")
assert df["spurious_seams"] == dm["spurious_seams"]
print(f"[4] PASS  spurious_seams fwd == mir ({df['spurious_seams']})")
assert af["n_sections"] == am["n_sections"] and af["n_leaves"] == am["n_leaves"]
print(f"[5] PASS  n_sections ({af['n_sections']}) and n_leaves ({af['n_leaves']}) fwd == mir")

print(f"\n=== EXP-506 Fork B: 5/5 PASS ===")
print(f"    stitched fault structure P_yz-invariant: |field| multiset, agreement, seams, counts")
