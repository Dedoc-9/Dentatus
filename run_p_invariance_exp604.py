"""
run_p_invariance_exp604.py -- Fork B: EXP-604 telemetry P_yz invariance

Protocol: exp604-v1
Declaration hash: f1f9c1a4438c3c23aa6cfa6850837615a9c1de9958780098ca6f53aef934e707

Telemetry observables are P_yz-invariant: lambda_2, the |fiedler| multiset (fault structure up to
eigenvector sign), leaf count, and the realized H_state all match under a seed x-stalk flip.

Tests [1-5]: see SEED_DECLARATION_exp604.json assertions_fork_B.
"""
import sys, os, json, hashlib
os.environ.setdefault("PYTHONHASHSEED", "0")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dentatus import api, core
from engine.validity import kappa_integral
import numpy as np

DECL_HASH = "f1f9c1a4438c3c23aa6cfa6850837615a9c1de9958780098ca6f53aef934e707"
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
          "studies/exp604_mcl_dashboard/SEED_DECLARATION_exp604.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DECL_HASH
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

ks = kappa_integral((np.zeros(3), np.ones(3)))
sf = [1.,1.,1.,1., 0.5,0.5,0.5,1., 0.6,0.,0.8,float(ks), 0.,0.,0.,0.,0.,0.]
sm = list(sf); sm[4] = -sf[4]
B = [1.0, 0.5, 0.3]; nB = float(np.linalg.norm(B)); B = [x/nB for x in B]
def declf(stalk):
    d = {"protocol": "dentatus-intent-v1", "engine_protocol": core.ENGINE_PROTOCOL, "title": "pyz",
         "seed_stalk": [round(float(x), 12) for x in stalk], "bbox": [[0.,0.,0.],[1.,1.,1.]],
         "B": [round(x, 12) for x in B], "K_budget": 2048}
    d["declaration_hash"] = hashlib.sha256(json.dumps(d, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return d
tf = api.observe({"op": "observe", "declaration": declf(sf), "steps": 8, "telemetry": True})["telemetry"]
tm = api.observe({"op": "observe", "declaration": declf(sm), "steps": 8, "telemetry": True})["telemetry"]

assert abs(tf["fiedler_lambda"] - tm["fiedler_lambda"]) <= 1e-9
print(f"[2] PASS  telemetry lambda_2 fwd == mir ({tf['fiedler_lambda']:.6f})")

af = sorted(round(abs(l["fiedler"]), 6) for l in tf["leaves"])
am = sorted(round(abs(l["fiedler"]), 6) for l in tm["leaves"])
assert af == am
print(f"[3] PASS  sorted |fiedler| multiset fwd == mir (fault structure P_yz-invariant)")

assert tf["n_leaves"] == tm["n_leaves"]
print(f"[4] PASS  n_leaves fwd == mir ({tf['n_leaves']})")

assert tf["H_state"] == tm["H_state"]
print(f"[5] PASS  telemetry H_state fwd == mir ({tf['H_state'][:16]}...)")

print(f"\n=== EXP-604 Fork B: 5/5 PASS ===")
print(f"    telemetry observables P_yz-invariant: lambda_2, |fiedler| multiset, n_leaves, H_state")
