"""
run_p_invariance_exp507.py -- Fork B: EXP-507 streaming P_yz invariance

Protocol: exp507-v1
Declaration hash: 2889884aa163e4964f0ebb0754848fb2f7066a4974cd9ca91dcf629e8c4dd7ec

Tests [1-5]: see SEED_DECLARATION_exp507.json assertions_fork_B.
"""
import sys, os, json, hashlib
os.environ.setdefault("PYTHONHASHSEED", "0")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "game"))
import numpy as np
from dentatus import api, core
from engine.validity import kappa_integral
from observability.sectioned_fiedler import stream_stitched_fiedler

DECL_HASH = "2889884aa163e4964f0ebb0754848fb2f7066a4974cd9ca91dcf629e8c4dd7ec"
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
          "studies/exp507_streaming_sections/SEED_DECLARATION_exp507.json")) as f:
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
f = stream_stitched_fiedler(tf["leaves"]); m = stream_stitched_fiedler(tm["leaves"])

mf = sorted(round(abs(x), 9) for x in f["field"]); mm = sorted(round(abs(x), 9) for x in m["field"])
assert mf == mm
print(f"[2] PASS  sorted |streaming field| multiset fwd == mir (P_yz-invariant)")
assert f["peak_resident_leaves"] == m["peak_resident_leaves"]
print(f"[3] PASS  peak_resident_leaves fwd == mir ({f['peak_resident_leaves']})")
assert f["cache_hits"] == m["cache_hits"]
print(f"[4] PASS  cache_hits fwd == mir ({f['cache_hits']})")
assert f["n_sections"] == m["n_sections"] and f["n_leaves"] == m["n_leaves"]
print(f"[5] PASS  n_sections ({f['n_sections']}) and n_leaves ({f['n_leaves']}) fwd == mir")

print(f"\n=== EXP-507 Fork B: 5/5 PASS ===")
print(f"    streaming stitch P_yz-invariant: |field| multiset, peak resident, cache, counts")
