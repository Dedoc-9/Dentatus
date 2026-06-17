"""
run_seed_exp604.py -- Fork A: EXP-604 MCL Observability Dashboard

Protocol: exp604-v1
Declaration hash: f1f9c1a4438c3c23aa6cfa6850837615a9c1de9958780098ca6f53aef934e707

Verifies the content-addressed telemetry layer: L1 telemetry block (Fiedler vector + per-leaf
geometry), bundle determinism, content-address dedup, witness purity, firewall-numeric, and the
self-contained dashboard. Requires PYTHONHASHSEED=0.

Tests [1-10]: see SEED_DECLARATION_exp604.json assertions_fork_A.
"""
import sys, os, json, hashlib
os.environ.setdefault("PYTHONHASHSEED", "0")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "game"))
from dentatus import api
from agency.loop import run_reality_search
from observability.telemetry import export_bundle

ROOT = os.path.dirname(os.path.abspath(__file__))
DECL_HASH = "f1f9c1a4438c3c23aa6cfa6850837615a9c1de9958780098ca6f53aef934e707"
with open(os.path.join(ROOT, "studies/exp604_mcl_dashboard/SEED_DECLARATION_exp604.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DECL_HASH
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

INTENT = {"title": "imperial_docking_bay",
          "seed": {"density": 1.0, "material": [0.55, 0.57, 0.62], "normal": [0, 0, 1],
                   "curvature": 2.0, "stress": {"axes": [3.0, 2.0, 0.4], "plane": "xy", "tilt_deg": 35}},
          "bbox": [[0, 0, 0], [1, 1, 1]], "zeeman": {"focus": [0.5, 0.5, 0.0]}}
LADDER = [1024, 2048, 512, 256, 128, 64]

r = api.observe({"op": "observe", "intent": {**INTENT, "zeeman": {**INTENT["zeeman"], "budget": 2048}}, "steps": 8, "telemetry": True})
t = r["telemetry"]
assert "leaves" in t and all(set(l) >= {"center", "size", "fiedler", "g_ent"} for l in t["leaves"]) and "fiedler_lambda" in t
print(f"[2] PASS  telemetry block: {t['n_leaves']} leaves with center/size/fiedler/g_ent + fiedler_lambda={t['fiedler_lambda']:.4f}")

fv = [l["fiedler"] for l in t["leaves"]]
pos = sum(1 for x in fv if x > 0); neg = sum(1 for x in fv if x < 0)
assert pos >= 1 and neg >= 1
print(f"[3] PASS  Fiedler bisection: {pos} positive / {neg} negative (the fault line)")

t2 = api.observe({"op": "observe", "intent": {**INTENT, "zeeman": {**INTENT["zeeman"], "budget": 2048}}, "steps": 8, "telemetry": True})["telemetry"]
assert t == t2 and t["H_state"] == t2["H_state"]
print(f"[4] PASS  content-addressed: identical world -> identical telemetry (key {t['H_state'][:12]})")

b = export_bundle(INTENT, LADDER); b2 = export_bundle(INTENT, LADDER)
assert json.dumps(b, sort_keys=True) == json.dumps(b2, sort_keys=True)
print(f"[5] PASS  bundle determinism: export_bundle bit-stable across runs")

assert b["unique_states"] <= b["frames_total"] and b["cache_hits"] >= 1
print(f"[6] PASS  content-address dedup: {b['unique_states']} unique / {b['frames_total']} frames, {b['cache_hits']} cache hit(s)")

_VERDICT = {"verdict", "valid", "passed", "healthy", "anomaly", "correct", "legal", "safe", "approved"}
def scan(n):
    if isinstance(n, dict):
        for k, v in n.items():
            assert str(k).lower() not in _VERDICT, f"verdict {k}"; scan(v)
    elif isinstance(n, list):
        for v in n: scan(v)
scan(b)
print(f"[7] PASS  witness purity: bundle/telemetry carry no verdict-shaped field")

fr = b["frames"][0]
admissible = (fr["worst_ratio"] <= fr["epsilon"])
assert isinstance(fr["worst_ratio"], (int, float)) and isinstance(fr["epsilon"], (int, float))
print(f"[8] PASS  firewall numeric: admissibility = (worst_ratio {fr['worst_ratio']:.4f} <= eps {fr['epsilon']}) = {admissible} (no boolean verdict in telemetry)")

rs = run_reality_search(INTENT, LADDER, k_stable=3)
assert b["committed_H_verified"] == rs["H_verified"]
print(f"[9] PASS  committed reality matches agency loop: H_verified={b['committed_H_verified'][:16]}...")

html = open(os.path.join(ROOT, "game/observability/mcl_dashboard.html"), encoding="utf-8").read()
assert "const BUNDLE = {" in html and "__BUNDLE__" not in html
import re
exts = re.findall(r'src="(https?://[^"]+)"', html)
assert all("cdnjs.cloudflare.com" in u for u in exts), f"non-cdnjs ext: {exts}"
print(f"[10] PASS  dashboard self-contained: bundle embedded; external src only cdnjs ({len(exts)} ref)")

print(f"\n=== EXP-604 Fork A: 10/10 PASS ===")
print(f"    content-addressed telemetry; Fiedler fault {pos}/{neg}; firewall numeric; witness-pure")
print(f"    bundle: {b['frames_total']} frames, {b['unique_states']} unique, {b['cache_hits']} cache-hit; dashboard self-contained")
