"""
run_p_invariance_exp605.py -- Fork B: EXP-605 stream P_yz invariance

Protocol: exp605-v1
Declaration hash: 7e682b51a229f7e68925f6e609d96354e17ec11c8386ebe41552584af1317c73
Tests [1-5]: see SEED_DECLARATION_exp605.json assertions_fork_B.
"""
import sys, os, json, hashlib, collections
os.environ.setdefault("PYTHONHASHSEED", "0")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "game"))
import numpy as np
from dentatus import api, core
from engine.validity import kappa_integral
from observability.stream import encode_reality_stream, frame_coarse

DECL_HASH = "7e682b51a229f7e68925f6e609d96354e17ec11c8386ebe41552584af1317c73"
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
          "studies/exp605_live_sse_stream/SEED_DECLARATION_exp605.json")) as f:
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
def stream_of(stalk):
    r = api.observe({"op": "observe", "declaration": dof(stalk), "steps": 8, "telemetry": True})
    states = [{"H_state": r["H_state"], "leaves": r["telemetry"]["leaves"]}]
    return encode_reality_stream(states), frame_coarse(r["telemetry"]["leaves"])
ef, ff = stream_of(sf); em, fm = stream_of(sm)

cf = collections.Counter(e for e, _ in ef); cm = collections.Counter(e for e, _ in em)
assert cf == cm
print(f"[2] PASS  event-type counts fwd == mir ({dict(cf)})")
mf = sorted(round(abs(x), 6) for x in ff["c"]); mm = sorted(round(abs(x), 6) for x in fm["c"])
assert mf == mm
print(f"[3] PASS  sorted |coarse anchor| multiset fwd == mir")
bf = sum(len(json.dumps(d, separators=(',',':'))) for _, d in ef)
bm = sum(len(json.dumps(d, separators=(',',':'))) for _, d in em)
assert bf == bm
print(f"[4] PASS  total encoded bytes fwd == mir ({bf})")
assert len(set(ff["section_sigs"])) == len(set(fm["section_sigs"]))
print(f"[5] PASS  section signature cardinality fwd == mir ({len(set(ff['section_sigs']))})")

print(f"\n=== EXP-605 Fork B: 5/5 PASS ===")
print(f"    reality stream P_yz-invariant: event counts, coarse multiset, bytes, section count")
