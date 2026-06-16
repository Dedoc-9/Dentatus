"""
run_p_invariance_exp606.py -- Fork B: EXP-606 LRU cache P_yz invariance

Protocol: exp606-v1
Declaration hash: 1bbbccefaec5ec174f95407e7f0abdcabd3e31d489b2b9327e4616fe9149a3d4
Tests [1-5]: see SEED_DECLARATION_exp606.json assertions_fork_B.
"""
import sys, os, json, hashlib, collections
os.environ.setdefault("PYTHONHASHSEED", "0")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "game"))
import numpy as np
from dentatus import api, core
from engine.validity import kappa_integral
from observability.stream import encode_reality_stream, decode_reality_stream

DECL_HASH = "1bbbccefaec5ec174f95407e7f0abdcabd3e31d489b2b9327e4616fe9149a3d4"
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
          "studies/exp606_lru_coarse_cache/SEED_DECLARATION_exp606.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DECL_HASH
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

ks = kappa_integral((np.zeros(3), np.ones(3)))
sf = [1.,1.,1.,1., 0.5,0.5,0.5,1., 0.6,0.,0.8,float(ks), 0.,0.,0.,0.,0.,0.]
sm = list(sf); sm[4] = -sf[4]
B = [1.0, 0.5, 0.3]; nB = float(np.linalg.norm(B)); B = [x/nB for x in B]
def dof(stalk, kb):
    d = {"protocol": "dentatus-intent-v1", "engine_protocol": core.ENGINE_PROTOCOL, "title": "pyz",
         "seed_stalk": [round(float(x), 12) for x in stalk], "bbox": [[0.,0.,0.],[1.,1.,1.]],
         "B": [round(x, 12) for x in B], "K_budget": kb}
    d["declaration_hash"] = hashlib.sha256(json.dumps(d, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return d
def loopstream(stalk):
    wa = api.observe({"op": "observe", "declaration": dof(stalk, 2048), "steps": 8, "telemetry": True})
    wb = api.observe({"op": "observe", "declaration": dof(stalk, 128), "steps": 8, "telemetry": True})
    A = {"H_state": wa["H_state"], "leaves": wa["telemetry"]["leaves"]}
    Bv = {"H_state": wb["H_state"], "leaves": wb["telemetry"]["leaves"]}
    return encode_reality_stream([A, Bv, A, Bv, A, Bv])
ef, em = loopstream(sf), loopstream(sm)
sz = lambda o: len(json.dumps(o, separators=(",", ":")))

cf = collections.Counter(e for e, _ in ef); cm = collections.Counter(e for e, _ in em)
assert cf == cm
print(f"[2] PASS  event-type counts fwd == mir ({dict(cf)})")
assert cf["coarse_ref"] == cm["coarse_ref"]
print(f"[3] PASS  coarse_ref count fwd == mir ({cf['coarse_ref']})")
bf = sum(sz(d) for e, d in ef if e.startswith("coarse")); bm = sum(sz(d) for e, d in em if e.startswith("coarse"))
assert bf == bm
print(f"[4] PASS  coarse bytes fwd == mir ({bf})")
df = decode_reality_stream(ef); dm = decode_reality_stream(em)
mf = sorted(round(abs(x), 6) for fr in df for x in (fr["coarse"] or []))
mm = sorted(round(abs(x), 6) for fr in dm for x in (fr["coarse"] or []))
assert mf == mm
print(f"[5] PASS  reconstructed |coarse| multiset fwd == mir")

print(f"\n=== EXP-606 Fork B: 5/5 PASS ===")
print(f"    LRU coarse stream P_yz-invariant: event counts, refs, bytes, reconstruction")
