"""
run_seed_exp606.py -- Fork A: EXP-606 LRU Coarse Cache (zero-cost state returns)

Protocol: exp606-v1
Declaration hash: 1bbbccefaec5ec174f95407e7f0abdcabd3e31d489b2b9327e4616fe9149a3d4

A session LRU of H_coarse -> anchors makes returns to ANY recently-seen coarse a one-line
coarse_ref (zero anchor payload), resolving Ghost #41. Requires PYTHONHASHSEED=0.

Tests [1-10]: see SEED_DECLARATION_exp606.json assertions_fork_A.
"""
import sys, os, json, hashlib, subprocess
os.environ.setdefault("PYTHONHASHSEED", "0")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "game"))
from dentatus import api
from observability.stream import encode_reality_stream, decode_reality_stream, frame_coarse

ROOT = os.path.dirname(os.path.abspath(__file__))
DECL_HASH = "1bbbccefaec5ec174f95407e7f0abdcabd3e31d489b2b9327e4616fe9149a3d4"
with open(os.path.join(ROOT, "studies/exp606_lru_coarse_cache/SEED_DECLARATION_exp606.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DECL_HASH
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

INTENT = {"title": "docking_bay",
          "seed": {"density": 1.0, "material": [0.55, 0.57, 0.62], "normal": [0, 0, 1],
                   "curvature": 2.0, "stress": {"axes": [3.0, 2.0, 0.4], "plane": "xy", "tilt_deg": 35}},
          "bbox": [[0, 0, 0], [1, 1, 1]], "zeeman": {"focus": [0.5, 0.5, 0.0]}}
def world(b):
    r = api.observe({"op": "observe", "intent": {**INTENT, "zeeman": {"focus": [0.5,0.5,0.0], "budget": b}}, "steps": 8, "telemetry": True})
    return {"H_state": r["H_state"], "leaves": r["telemetry"]["leaves"]}
A, Bv = world(2048), world(128)          # two distinct coarse worlds (148-leaf vs 8-leaf)
loop = [A, Bv, A, Bv, A, Bv]             # flicker / loop
sz = lambda o: len(json.dumps(o, separators=(",", ":")))
cb = lambda ev: sum(sz(d) for e, d in ev if e in ("coarse_keyframe", "coarse_delta", "coarse_ref"))

ev = encode_reality_stream(loop, lru_size=16)
dec = decode_reality_stream(ev)
enc = [frame_coarse(w["leaves"])["c"] for w in loop]
assert all(dec[i]["coarse"] == enc[i] for i in range(len(loop)))
print(f"[2] PASS  codec exact with LRU: decode(encode) reconstructs coarse bit-exactly")

refs = sum(1 for e, _ in ev if e == "coarse_ref"); kfs = sum(1 for e, _ in ev if e == "coarse_keyframe")
assert kfs == 2 and refs == 4
print(f"[3] PASS  zero-cost returns: loop A B A B A B -> {kfs} keyframes + {refs} coarse_refs")

kf = next(d for e, d in ev if e == "coarse_keyframe"); ref = next(d for e, d in ev if e == "coarse_ref")
assert sz(ref) < sz(kf)
print(f"[4] PASS  coarse_ref payload minimal: ref {sz(ref)}b < keyframe {sz(kf)}b")

ev_no = encode_reality_stream(loop, lru_size=0)
assert cb(ev) < cb(ev_no)
print(f"[5] PASS  bitrate: LRU coarse {cb(ev)}b < no-LRU {cb(ev_no)}b ({cb(ev_no)/cb(ev):.1f}x less)")

dec_no = decode_reality_stream(ev_no)
assert all(dec[i]["coarse"] == dec_no[i]["coarse"] for i in range(len(loop)))
print(f"[6] PASS  reconstruction parity: LRU field == no-LRU field (same result, fewer bytes)")

ev_small = encode_reality_stream(loop, lru_size=1)   # window too small to hold both A and B
refs_small = sum(1 for e, _ in ev_small if e == "coarse_ref")
assert refs_small < refs
print(f"[7] PASS  LRU eviction bounded: lru_size=1 -> {refs_small} refs (< {refs}); evicted returns re-send")

ladder = [world(b) for b in [1024, 2048, 128]]       # non-looping (distinct coarse)
ev_ladder = encode_reality_stream(ladder)
assert sum(1 for e, _ in ev_ladder if e == "coarse_ref") == 0
print(f"[8] PASS  backward-compat: non-looping stream emits 0 coarse_refs (EXP-605 preserved)")

assert encode_reality_stream(loop, lru_size=16) == ev
print(f"[9] PASS  determinism: encode bit-stable across runs")

guard = subprocess.run([sys.executable, os.path.join(ROOT, "game/tests/test_clean_room.py")], capture_output=True, text=True)
assert guard.returncode == 0
print(f"[10] PASS  decoupled: clean-room guard passes (game/ imports no engine.*)")

print(f"\n=== EXP-606 Fork A: 10/10 PASS ===")
print(f"    session LRU -> zero-cost returns: loop coarse {cb(ev_no)}b -> {cb(ev)}b; Ghost #41 resolved")
print(f"    bit-exact, bounded eviction, backward-compatible with EXP-605")
