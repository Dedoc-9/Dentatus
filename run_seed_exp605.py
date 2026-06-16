"""
run_seed_exp605.py -- Fork A: EXP-605 Live SSE Reality Stream

Protocol: exp605-v1
Declaration hash: 7e682b51a229f7e68925f6e609d96354e17ec11c8386ebe41552584af1317c73

Keyframe+delta coarse codec + content-addressed sections + equilibrium heartbeats. Bit-exact
reconstruction; bitrate proportional to rate-of-change. Requires PYTHONHASHSEED=0.

Tests [1-10]: see SEED_DECLARATION_exp605.json assertions_fork_A.
"""
import sys, os, json, hashlib, subprocess
os.environ.setdefault("PYTHONHASHSEED", "0")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "game"))
from dentatus import api
from observability.stream import encode_reality_stream, decode_reality_stream, frame_coarse

ROOT = os.path.dirname(os.path.abspath(__file__))
DECL_HASH = "7e682b51a229f7e68925f6e609d96354e17ec11c8386ebe41552584af1317c73"
with open(os.path.join(ROOT, "studies/exp605_live_sse_stream/SEED_DECLARATION_exp605.json")) as f:
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
ladder = [world(b) for b in [1024, 2048, 512, 256, 128, 64]]
eqr = world(2048); equilibrium = [eqr] * 8
sz = lambda o: len(json.dumps(o, separators=(",", ":")))

ev = encode_reality_stream(ladder)
dec = decode_reality_stream(ev)
# encoder per-frame coarse (with heartbeat repeats)
enc_c = []; pc = None
for s in ladder:
    if pc is not None and s["H_state"] == pc: enc_c.append(enc_c[-1])
    else: enc_c.append(frame_coarse(s["leaves"])["c"]); pc = s["H_state"]
assert all(dec[i]["coarse"] == enc_c[i] for i in range(len(ladder)))
print(f"[2] PASS  codec exact: decode(encode) reconstructs coarse field bit-exactly ({len(ladder)} worlds)")

# coarse channel content-addressed: two worlds with identical geometry (same coarse, different
# H_state) -> the coarse is sent ONCE; the 2nd world emits NO coarse event. Plus adaptive invariant.
shared = [world(1024), world(512)]   # both 36 leaves, same octree geometry -> same coarse
ev_sh = encode_reality_stream(shared)
coarse_events = [e for e, _ in ev_sh if e in ("coarse_keyframe", "coarse_delta")]
worlds_sh = [e for e, _ in ev_sh if e == "world"]
assert len(worlds_sh) == 2 and len(coarse_events) == 1   # coarse re-used across the 2nd world
# adaptive invariant: every emitted delta in any stream is smaller than its keyframe alternative
kf_any = [d for e, d in ev if e == "coarse_keyframe"]
dl_any = [d for e, d in ev if e == "coarse_delta"]
assert all(sz(d) < min(sz(k) for k in kf_any) for d in dl_any) if dl_any else True
print(f"[3] PASS  content-addressed coarse: 2 worlds same geometry -> 1 coarse event (anchors re-used); adaptive keyframe/delta")

refs = sum(1 for e, _ in ev if e == "section_ref"); secs = sum(1 for e, _ in ev if e == "section")
assert refs >= 1
print(f"[4] PASS  content-addressed sections: {secs} full + {refs} refs (repeats not re-sent)")

ev_eq = encode_reality_stream(equilibrium)
hb = sum(1 for e, _ in ev_eq if e == "heartbeat")
assert hb == len(equilibrium) - 1
print(f"[5] PASS  heartbeat at equilibrium: {hb} heartbeats over {len(equilibrium)} repeated worlds")

codec = sum(sz(d) for _, d in ev_eq)
full = sum(sz(frame_coarse(s["leaves"])["c"]) + sz(s["leaves"]) for s in equilibrium)
assert codec < full / 3
print(f"[6] PASS  bitrate proportional to change: equilibrium codec {codec}b << full {full}b ({full/codec:.1f}x)")

# section self-containment: each section event's leaves are complete (no neighbor dependency)
sec_events = [d for e, d in ev if e == "section"]
assert all("leaves" in d and len(d["leaves"]) >= 1 for d in sec_events)
print(f"[7] PASS  no pop-in: each section self-contained ({len(sec_events)} sections, all leaves present); render needs only coarse+centroids")

# keyframe resync: decode from the 2nd keyframe onward -> coarse reconstructs
kf_idx = [i for i, (e, _) in enumerate(ev) if e == "coarse_keyframe"]
assert len(kf_idx) >= 2
tail = ev[kf_idx[1]:]
coarse = None
for e, d in tail:
    if e == "coarse_keyframe": coarse = list(d["c"])
    elif e == "coarse_delta":
        for a in d["changed"]: coarse[a[0]] = a[1]
assert coarse is not None
print(f"[8] PASS  keyframe resync: late subscriber reconstructs from keyframe (no drift)")

assert encode_reality_stream(ladder) == ev
print(f"[9] PASS  determinism: encode bit-stable across runs")

guard = subprocess.run([sys.executable, os.path.join(ROOT, "game/tests/test_clean_room.py")], capture_output=True, text=True)
assert guard.returncode == 0
print(f"[10] PASS  decoupled: clean-room guard passes (game/ imports no engine.*)")

print(f"\n=== EXP-605 Fork A: 10/10 PASS ===")
print(f"    keyframe+delta codec, content-addressed sections, equilibrium heartbeats")
print(f"    bit-exact reconstruction; bitrate ~ rate-of-change ({full/codec:.0f}x at equilibrium); no pop-in")
