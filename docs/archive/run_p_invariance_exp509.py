"""
run_p_invariance_exp509.py -- Fork B: EXP-509 Bethe Citadel P_yz invariance

Protocol: exp509-v1
Declaration hash: 58f3f306a8f48cbe7defa35291a8374a8a94ba7e37d02849c3807fa344c5eea2
Tests [1-5]: see SEED_DECLARATION_exp509.json assertions_fork_B.
"""
import sys, os, json, hashlib
os.environ.setdefault("PYTHONHASHSEED", "0")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dentatus import api, core
from engine.validity import kappa_integral
import numpy as np

DECL_HASH = "58f3f306a8f48cbe7defa35291a8374a8a94ba7e37d02849c3807fa344c5eea2"
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
          "studies/exp509_zeeman_bethe_citadel/SEED_DECLARATION_exp509.json")) as f:
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
f = api.observe({"op": "observe", "declaration": dof(sf), "steps": 8})["bethe_citadel"]
m = api.observe({"op": "observe", "declaration": dof(sm), "steps": 8})["bethe_citadel"]

assert f["E_star"] == m["E_star"]
print(f"[2] PASS  E_star (beta_Z) fwd == mir ({f['E_star']})")
assert f["dS_cit"] == m["dS_cit"]
print(f"[3] PASS  dS_cit_bethe fwd == mir ({f['dS_cit']})")
assert f["is_bethe_citadel"] == m["is_bethe_citadel"]
print(f"[4] PASS  is_bethe_citadel fwd == mir ({f['is_bethe_citadel']})")
assert f["H_out"] == m["H_out"]
print(f"[5] PASS  H_out (N_f+N_gamma) fwd == mir ({f['H_out']})")

print(f"\n=== EXP-509 Fork B: 5/5 PASS ===")
print(f"    Bethe Citadel P_yz-invariant: E_star, dS_cit, decision, H_out")
