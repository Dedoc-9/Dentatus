"""
run_seed_exp603.py -- Fork A: EXP-603 Agency Loop & Autonomous Reality Search

Protocol: exp603-v1
Declaration hash: fdb106028f99333e4673e4a134d841ddca3261be234094925e62483ca5489da2

Verifies the decoupled game-layer agency loop: iterate-to-stable over resolution budget,
Agency Hysteresis Latch (monotone tectonic-stress + firewall), witnessed audit trail (incl.
failed probes), bit-perfect committed H_verified (the teeth of truth). Requires PYTHONHASHSEED=0.

Tests [1-10]: see SEED_DECLARATION_exp603.json assertions_fork_A.
"""
import sys, os, json, hashlib, subprocess
os.environ.setdefault("PYTHONHASHSEED", "0")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "game"))

from agency.loop import run_reality_search, _WITNESS

DECL_HASH = "fdb106028f99333e4673e4a134d841ddca3261be234094925e62483ca5489da2"
DECL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "studies/exp603_agency_loop/SEED_DECLARATION_exp603.json")
with open(DECL_PATH) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DECL_HASH
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

BASE = {"title": "docking_bay",
        "seed": {"density": 1.0, "material": [0.55, 0.57, 0.62], "normal": [0, 0, 1],
                 "curvature": 2.0, "stress": {"axes": [3.0, 2.0, 0.4], "plane": "xy", "tilt_deg": 35}},
        "bbox": [[0, 0, 0], [1, 1, 1]], "zeeman": {"focus": [0.5, 0.5, 0.0]}}
LADDER = [1024, 2048, 512, 256, 128, 64]

r = run_reality_search(BASE, budget_ladder=LADDER, k_stable=3, max_iter=12)

traj = r["stress_trajectory"]
assert all(traj[i + 1] <= traj[i] + 1e-9 for i in range(len(traj) - 1)), f"[2] FAIL {traj}"
print(f"[2] PASS  tectonic-stress trajectory monotone non-increasing: {traj}")

red = traj[0] - traj[-1]
assert red > 0, f"[3] FAIL reduction {red}"
print(f"[3] PASS  stress_reduction = {red:.4f} > 0 (manifold deformation reduced)")

assert r["latched"] and r["success"]
print(f"[4] PASS  agency latch engaged (success=True)")

assert r["H_verified"] is not None
print(f"[5] PASS  teeth of truth: H_verified non-null in latched state = {r['H_verified'][:16]}...")

r2 = run_reality_search(BASE, budget_ladder=LADDER, k_stable=3, max_iter=12)
assert r2["H_verified"] == r["H_verified"]
print(f"[6] PASS  bit-stable in-process (2 runs -> identical committed H_verified)")

ONE = ("import sys; sys.path.insert(0,%r); from agency.loop import run_reality_search; "
       "print(run_reality_search({'title':'docking_bay','seed':{'density':1.0,'material':[0.55,0.57,0.62],"
       "'normal':[0,0,1],'curvature':2.0,'stress':{'axes':[3.0,2.0,0.4],'plane':'xy','tilt_deg':35}},"
       "'bbox':[[0,0,0],[1,1,1]],'zeeman':{'focus':[0.5,0.5,0.0]}}, [1024,2048,512,256,128,64], k_stable=3)['H_verified'])"
       % os.path.join(os.path.dirname(os.path.abspath(__file__)), "game"))
env = dict(os.environ); env["PYTHONHASHSEED"] = "0"
outs = {subprocess.run([sys.executable, "-c", ONE], capture_output=True, text=True, env=env).stdout.strip() for _ in range(3)}
assert len(outs) == 1 and r["H_verified"] in outs, f"[7] FAIL cross-proc {outs}"
print(f"[7] PASS  bit-perfect cross-process (3 subprocesses -> identical H_verified)")

trail = r["audit_trail"]
def _d(a): return a["data"] if "data" in a else a
rejects = [a for a in trail if _d(a).get("delta_B_ent_vs_best", -1) >= 0 and _d(a).get("claim_class", "") != "agency_commit"]
rejects = [a for a in trail if (_d(a).get("iteration") and _d(a).get("H_verified") is None and _d(a).get("delta_B_ent_vs_best", -1) >= 0)]
assert len(rejects) >= 1
print(f"[8] PASS  audit trail includes {len(rejects)} witnessed failed probe(s) of {len(trail)} artifacts")

# [9] witness purity: artifacts carry no verdict field; H_verified only in commit artifact
_VERDICT = {"verdict", "valid", "passed", "healthy", "anomaly", "correct", "legal", "safe", "approved"}
def scan(node):
    if isinstance(node, dict):
        for k, v in node.items():
            assert str(k).lower() not in _VERDICT, f"verdict field {k}"
            scan(v)
    elif isinstance(node, list):
        for v in node: scan(v)
commit_arts = 0
for a in trail:
    scan(_d(a))
    if (a.get("claim_class") if hasattr(a, "get") else None) == "agency_commit" or _d(a).get("H_verified"):
        commit_arts += 1
assert commit_arts == 1, f"[9] FAIL commit artifacts {commit_arts}"
print(f"[9] PASS  witness purity: no verdict fields; H_verified only in the single commit artifact (witness_core={_WITNESS})")

guard = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "game/tests/test_clean_room.py")],
                       capture_output=True, text=True)
assert guard.returncode == 0, f"[10] FAIL clean-room: {guard.stdout}{guard.stderr}"
print(f"[10] PASS  decoupled: clean-room guard passes (game/ imports no engine.*)")

print(f"\n=== EXP-603 Fork A: 10/10 PASS ===")
print(f"    autonomous reality search: stress {traj[0]:.4f} -> {traj[-1]:.4f} ({red:.4f} reduction); latched")
print(f"    committed reality address H_verified = {r['H_verified'][:24]}... (bit-perfect, cross-process)")
print(f"    {len(trail)} witnessed artifacts (incl. failed probes); decoupled in game/agency")
