"""
run_p_invariance_exp603.py -- Fork B: EXP-603 P_yz (agency outcome invariance)

Protocol: exp603-v1
Declaration hash: fdb106028f99333e4673e4a134d841ddca3261be234094925e62483ca5489da2

The realized worlds are geometry-driven; the seed Sector-B x-stalk does not propagate. A P_yz
reflection of the seed (x-stalk flip) therefore yields an identical search trajectory and an
identical committed reality address. The agency outcome is P_yz-invariant.

Tests [1-5]: see SEED_DECLARATION_exp603.json assertions_fork_B.
"""
import sys, os, json, hashlib
os.environ.setdefault("PYTHONHASHSEED", "0")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "game"))
import numpy as np
from agency.loop import run_reality_search

DECL_HASH = "fdb106028f99333e4673e4a134d841ddca3261be234094925e62483ca5489da2"
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
          "studies/exp603_agency_loop/SEED_DECLARATION_exp603.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DECL_HASH
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

LADDER = [1024, 2048, 512, 256, 128, 64]
# fwd and mir intents: mir flips the seed surface-normal x-component (P_yz on Sector C nx).
fwd = {"title": "pyz", "seed": {"density": 1.0, "normal": [0.6, 0.0, 0.8], "curvature": 2.0,
       "stress": {"axes": [3.0, 2.0, 0.4], "plane": "xy", "tilt_deg": 35}},
       "bbox": [[0, 0, 0], [1, 1, 1]], "zeeman": {"focus": [0.5, 0.5, 0.0]}}
mir = {**fwd, "seed": {**fwd["seed"], "normal": [-0.6, 0.0, 0.8]}}

rf = run_reality_search(fwd, LADDER, k_stable=3, max_iter=12)
rm = run_reality_search(mir, LADDER, k_stable=3, max_iter=12)

assert rf["stress_trajectory"] == rm["stress_trajectory"]
print(f"[2] PASS  search stress trajectory fwd == mir: {rf['stress_trajectory']}")

assert rf["H_verified"] == rm["H_verified"] and rf["H_verified"] is not None
print(f"[3] PASS  committed H_verified fwd == mir = {rf['H_verified'][:16]}... (realized world P_yz-invariant)")

assert rf["latched"] and rm["latched"]
print(f"[4] PASS  agency latch engages for both fwd and mir")

redf = rf["stress_trajectory"][0] - rf["stress_trajectory"][-1]
redm = rm["stress_trajectory"][0] - rm["stress_trajectory"][-1]
assert abs(redf - redm) < 1e-12
print(f"[5] PASS  stress_reduction fwd == mir ({redf:.4f})")

print(f"\n=== EXP-603 Fork B: 5/5 PASS ===")
print(f"    agency outcome P_yz-invariant: trajectory, committed address, latch, reduction all match")
