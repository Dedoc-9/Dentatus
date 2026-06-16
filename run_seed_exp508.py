"""
run_seed_exp508.py -- Fork A: EXP-508 Citadel Entropy Firewall

Protocol: exp508-v1
Declaration hash: 8a511d4360b4c0402b9e97152d39111e0b0872d00fa2f4fda6f338600e115698

Law of the Citadel: dS_cit = log2(K_budget) - log2(N_f + N_gamma) >= 0
  <=> N_f + N_gamma <= K_budget  (no structure fabricated beyond what E* licenses).
Dual firewall: H_verified iff is_manifold_501 AND is_citadel_508. Requires PYTHONHASHSEED=0.

Tests [1-10]: see SEED_DECLARATION_exp508.json assertions_fork_A.
"""
import sys, os, json, hashlib, math
os.environ.setdefault("PYTHONHASHSEED", "0")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dentatus import api
from engine.validity import citadel_entropy_508, is_citadel_508, CITADEL_FLOOR_508

DECL_HASH = "8a511d4360b4c0402b9e97152d39111e0b0872d00fa2f4fda6f338600e115698"
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
          "studies/exp508_citadel_firewall/SEED_DECLARATION_exp508.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DECL_HASH
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

c = citadel_entropy_508(2048, 148, 396)
assert abs(c["H_in"] - math.log2(2048)) < 1e-9 and abs(c["H_out"] - math.log2(544)) < 1e-9
assert abs(c["dS_cit"] - (c["H_in"] - c["H_out"])) < 1e-9
print(f"[2] PASS  citadel math: H_in={c['H_in']} H_out={c['H_out']} dS_cit={c['dS_cit']}")

INTENT = {"title": "docking_bay",
          "seed": {"density": 1.0, "material": [0.55, 0.57, 0.62], "normal": [0, 0, 1],
                   "curvature": 2.0, "stress": {"axes": [3.0, 2.0, 0.4], "plane": "xy", "tilt_deg": 35}},
          "bbox": [[0, 0, 0], [1, 1, 1]], "zeeman": {"focus": [0.5, 0.5, 0.0]}}
ds = []
for b in [2048, 1024, 512, 256, 128]:
    r = api.observe({"op": "observe", "intent": {**INTENT, "zeeman": {"focus": [0.5,0.5,0.0], "budget": b}}, "steps": 8})
    ds.append((b, r["citadel"]["dS_cit"], r["citadel"]["is_citadel"], r["citadel"]["N_f"], r["citadel"]["N_gamma"]))
assert all(d[2] for d in ds) and all(d[1] >= 0 for d in ds)
print(f"[3] PASS  valid worlds admitted across budget ladder (dS_cit>=0): {[(b,round(d,2)) for b,d,_,_,_ in ds]}")

over = citadel_entropy_508(256, 148, 396)
assert not is_citadel_508(over["dS_cit"]) and over["dS_cit"] < 0
print(f"[4] PASS  over-budget veto: N_f+N_gamma=544 > K_budget=256 -> dS_cit={over['dS_cit']} -> is_citadel False")

neutral = citadel_entropy_508(512, 512, 0)
assert abs(neutral["dS_cit"]) < 1e-9 and is_citadel_508(neutral["dS_cit"])
print(f"[5] PASS  entropy-neutral boundary: N_f+N_gamma==K_budget -> dS_cit={neutral['dS_cit']} -> admitted")

r = api.observe({"op": "observe", "intent": {**INTENT, "zeeman": {"focus": [0.5,0.5,0.0], "budget": 2048}}, "steps": 8})
contract = (r["admissible"] == (r["firewall"]["is_manifold_501"] and r["citadel"]["is_citadel"]))
hv = (r["H_verified"] is not None) == r["admissible"]
assert contract and hv
print(f"[6] PASS  dual-gate contract: admissible == (manifold {r['firewall']['is_manifold_501']} AND citadel {r['citadel']['is_citadel']}); H_verified iff admissible")

assert all((nf + ng) <= b for b, _, _, nf, ng in ds)
print(f"[7] PASS  conservation invariant: engine self-limits, N_f+N_gamma <= K_budget for all realizations")

los = citadel_entropy_508(2048, 1, 0)
assert abs(los["dS_cit"] - math.log2(2048)) < 1e-9
print(f"[8] PASS  lossless single (N_f=1,N_gamma=0) -> dS_cit={los['dS_cit']} (maximal slack)")

r2 = api.observe({"op": "observe", "intent": {**INTENT, "zeeman": {"focus": [0.5,0.5,0.0], "budget": 2048}}, "steps": 8})
assert r2["citadel"]["dS_cit"] == r["citadel"]["dS_cit"]
print(f"[9] PASS  determinism: dS_cit bit-stable ({r['citadel']['dS_cit']})")

assert r["H_verified"] is not None and r["firewall"]["is_manifold_501"]
print(f"[10] PASS  no regression: admissible world keeps H_verified ({r['H_verified'][:16]}...)")

print(f"\n=== EXP-508 Fork A: 10/10 PASS ===")
print(f"    Law of the Citadel dS_cit>=0 (dual gate w/ is_manifold_501); docking bay dS_cit={c['dS_cit']}")
print(f"    over-budget vetoed; engine self-limits (conservation invariant); H_in=log2(K_budget)")
