"""
run_seed_exp506.py -- Fork A: EXP-506 Stitched Local Fiedler

Protocol: exp506-v1
Declaration hash: d69b59b3ad635e16a0194e5087fa0aaa6773f378565570d3bedb46cac8d397ed

Galerkin coarse Fiedler + partition-of-unity stitch with a DYNAMIC spectral-diameter halo
(1-leaf floor). Reproduces the global fault line at section resolution with zero spurious
section seams, at O(S^3 + sum n_s^3) << O(N^3). Requires PYTHONHASHSEED=0.

Tests [1-10]: see SEED_DECLARATION_exp506.json assertions_fork_A.
"""
import sys, os, json, hashlib, subprocess
os.environ.setdefault("PYTHONHASHSEED", "0")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "game"))
from dentatus import api
from observability.sectioned_fiedler import stitch_diagnostics, stitched_fiedler

ROOT = os.path.dirname(os.path.abspath(__file__))
DECL_HASH = "d69b59b3ad635e16a0194e5087fa0aaa6773f378565570d3bedb46cac8d397ed"
with open(os.path.join(ROOT, "studies/exp506_stitched_fiedler/SEED_DECLARATION_exp506.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DECL_HASH
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

INTENT = {"title": "docking_bay",
          "seed": {"density": 1.0, "material": [0.55, 0.57, 0.62], "normal": [0, 0, 1],
                   "curvature": 2.0, "stress": {"axes": [3.0, 2.0, 0.4], "plane": "xy", "tilt_deg": 35}},
          "bbox": [[0, 0, 0], [1, 1, 1]], "zeeman": {"focus": [0.5, 0.5, 0.0], "budget": 2048}}
tel = api.observe({"op": "observe", "intent": INTENT, "steps": 8, "telemetry": True})["telemetry"]
d = stitch_diagnostics(tel["leaves"])

assert d["section_agreement"] == 1.0
print(f"[2] PASS  Galerkin coarse: {d['section_agreement']*100:.0f}% section-sign agreement with global")

st = stitched_fiedler(tel["leaves"])
floor = st["leaf_size"]
assert all(s >= floor - 1e-9 for s in st["halo_sigma"]) and len(st["spectral_diameter"]) == st["n_sections"]
print(f"[3] PASS  dynamic spectral-diameter halo, 1-leaf floor={floor:.3f}: sigma={[round(x,3) for x in st['halo_sigma']]}")

assert d["leaf_agreement"] >= 0.95
print(f"[4] PASS  stitched leaf agreement with global = {d['leaf_agreement']*100:.0f}% (>= 95%)")

assert d["spurious_seams"] == 0
print(f"[5] PASS  spurious section seams = {d['spurious_seams']} (naive independent ~21)")

assert d["stitched_fault_edges"] == d["global_fault_edges"]
print(f"[6] PASS  fault line reproduced: stitched {d['stitched_fault_edges']} == global {d['global_fault_edges']} fault edges")

d_fixed = stitch_diagnostics(tel["leaves"], fixed_sigma=0.3)
assert d["spurious_seams"] <= d_fixed["spurious_seams"]
print(f"[7] PASS  dynamic <= fixed halo: seams dynamic {d['spurious_seams']} <= fixed(sigma=0.3) {d_fixed['spurious_seams']}")

ratio = d["cost_global"] / d["cost_two_level"]
assert ratio >= 5
print(f"[8] PASS  cost: two-level {d['cost_two_level']:,} vs global {d['cost_global']:,} ({ratio:.0f}x cheaper)")

d2 = stitch_diagnostics(tel["leaves"])
assert d2["leaf_agreement"] == d["leaf_agreement"] and d2["spurious_seams"] == d["spurious_seams"]
print(f"[9] PASS  determinism: diagnostics bit-stable across runs")

guard = subprocess.run([sys.executable, os.path.join(ROOT, "game/tests/test_clean_room.py")], capture_output=True, text=True)
assert guard.returncode == 0
print(f"[10] PASS  decoupled: clean-room guard passes (game/ imports no engine.*)")

print(f"\n=== EXP-506 Fork A: 10/10 PASS ===")
print(f"    stitched fault == global ({d['global_fault_edges']} edges), 0 seams, {d['leaf_agreement']*100:.0f}% leaf agree, {ratio:.0f}x cheaper")
print(f"    dynamic spectral-diameter halo (1-leaf floor); Galerkin coarse 100% section agreement")
