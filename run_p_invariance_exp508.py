"""
run_p_invariance_exp508.py -- Fork B: EXP-508 Citadel P_yz invariance

Protocol: exp508-v1
Declaration hash: 8a511d4360b4c0402b9e97152d39111e0b0872d00fa2f4fda6f338600e115698

N_f, N_gamma, K_budget are counts -> P_yz-invariant -> dS_cit and the citadel decision are
P_yz-invariant exactly.

Tests [1-5]: see SEED_DECLARATION_exp508.json assertions_fork_B.
"""
import sys, os, json, hashlib
os.environ.setdefault("PYTHONHASHSEED", "0")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dentatus import api, core
from engine.validity import kappa_integral
import numpy as np

DECL_HASH = "8a511d4360b4c0402b9e97152d39111e0b0872d00fa2f4fda6f338600e115698"
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
          "studies/exp508_citadel_firewall/SEED_DECLARATION_exp508.json")) as f:
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
f = api.observe({"op": "observe", "declaration": dof(sf), "steps": 8})["citadel"]
m = api.observe({"op": "observe", "declaration": dof(sm), "steps": 8})["citadel"]

assert f["N_f"] == m["N_f"]
print(f"[2] PASS  N_f fwd == mir ({f['N_f']})")
assert f["N_gamma"] == m["N_gamma"]
print(f"[3] PASS  N_gamma fwd == mir ({f['N_gamma']})")
assert f["dS_cit"] == m["dS_cit"]
print(f"[4] PASS  dS_cit fwd == mir ({f['dS_cit']})")
assert f["is_citadel"] == m["is_citadel"]
print(f"[5] PASS  is_citadel decision fwd == mir ({f['is_citadel']})")

print(f"\n=== EXP-508 Fork B: 5/5 PASS ===")
print(f"    citadel score P_yz-invariant: N_f, N_gamma, dS_cit, decision all match")
