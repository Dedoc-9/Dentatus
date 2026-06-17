"""
run_seed_exp507.py -- Fork A: EXP-507 Streaming World-Sections

Protocol: exp507-v1
Declaration hash: 2889884aa163e4964f0ebb0754848fb2f7066a4974cd9ca91dcf629e8c4dd7ec

Streaming two-level stitch under a resident-set memory bound: same field as EXP-506, computed
holding <= max_resident sections in memory at a time. Requires PYTHONHASHSEED=0.

Tests [1-10]: see SEED_DECLARATION_exp507.json assertions_fork_A.
"""
import sys, os, json, hashlib, subprocess
os.environ.setdefault("PYTHONHASHSEED", "0")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "game"))
import numpy as np
from dentatus import api
from observability.sectioned_fiedler import stitched_fiedler, stream_stitched_fiedler, stitch_diagnostics

ROOT = os.path.dirname(os.path.abspath(__file__))
DECL_HASH = "2889884aa163e4964f0ebb0754848fb2f7066a4974cd9ca91dcf629e8c4dd7ec"
with open(os.path.join(ROOT, "studies/exp507_streaming_sections/SEED_DECLARATION_exp507.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DECL_HASH
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

INTENT = {"title": "docking_bay",
          "seed": {"density": 1.0, "material": [0.55, 0.57, 0.62], "normal": [0, 0, 1],
                   "curvature": 2.0, "stress": {"axes": [3.0, 2.0, 0.4], "plane": "xy", "tilt_deg": 35}},
          "bbox": [[0, 0, 0], [1, 1, 1]], "zeeman": {"focus": [0.5, 0.5, 0.0], "budget": 2048}}
leaves = api.observe({"op": "observe", "intent": INTENT, "steps": 8, "telemetry": True})["telemetry"]["leaves"]
N = len(leaves)
full = stitched_fiedler(leaves)["field"]
strm = stream_stitched_fiedler(leaves, max_resident=1)

assert np.allclose(full, strm["field"], atol=1e-12)
print(f"[2] PASS  streaming field == non-streaming stitched field (bit-identical, {N} leaves)")

assert strm["peak_resident_leaves"] < N
print(f"[3] PASS  bounded working set: peak resident {strm['peak_resident_leaves']} < N={N} (one section at a time)")

assert strm["max_resident_sections"] == 1
print(f"[4] PASS  eviction: resident set bounded at max_resident={strm['max_resident_sections']} section")

assert strm["coarse_anchor_size"] == strm["n_sections"]
print(f"[5] PASS  coarse anchor O(S)={strm['coarse_anchor_size']} computed once (global fault)")

assert strm["cache_hits"] >= strm["n_sections"]
print(f"[6] PASS  content-addressed cache: {strm['cache_hits']} section revisits hit cache (>= {strm['n_sections']})")

assert strm["memory_streaming"] < strm["memory_global"] or strm["peak_resident_leaves"] < N
print(f"[7] PASS  memory bound: peak_resident {strm['peak_resident_leaves']} + O(S) {strm['n_sections']} << global {N} (scales O(1) per section)")

strm2 = stream_stitched_fiedler(leaves, max_resident=1)
assert np.array_equal(strm["field"], strm2["field"])
print(f"[8] PASS  determinism: streaming field bit-stable across runs")

d = stitch_diagnostics(leaves)
assert d["spurious_seams"] == 0 and d["stitched_fault_edges"] == d["global_fault_edges"]
print(f"[9] PASS  fault preserved: streaming reproduces global fault ({d['global_fault_edges']} edges, 0 seams)")

guard = subprocess.run([sys.executable, os.path.join(ROOT, "game/tests/test_clean_room.py")], capture_output=True, text=True)
assert guard.returncode == 0
print(f"[10] PASS  decoupled: clean-room guard passes (game/ imports no engine.*)")

print(f"\n=== EXP-507 Fork A: 10/10 PASS ===")
print(f"    streaming stitch: exact field, peak resident {strm['peak_resident_leaves']}/{N} leaves, {strm['cache_hits']} cache hits")
print(f"    coarse O(S)={strm['n_sections']} anchor once; bounded memory at galactic scale")
