"""
conformance_suite/runner.py — the cross-application conformance regression harness.

The workbench preflight (`integration/preflight_check.py`) covers the 26 *sibling* suites. This harness
covers what is downstream of them: the five standalone **applications**' content-addressed conformance
hashes. Its job is to protect the thing everything is downstream of — if a change to a frozen core, a
sibling, or the canonical hashing format silently alters a downstream application's output, this catches it
and names the exact app.

Each application is probed in an ISOLATED SUBPROCESS (they reuse module names like `conformance`, `kernel`,
`world`, `runner` that would collide in one interpreter), under PYTHONHASHSEED=0. Each probe regenerates the
app's deterministic golden artifact and prints a single `golden` hash + details. The harness diffs the
goldens against a pinned `conformance_baseline.json`.

HONEST BOUND: this detects **drift** — any change that alters a downstream conformance hash — not
*correctness*. A drift may be a deliberate improvement; in that case you re-pin the baseline on purpose
(`run.py --update`), exactly as a ruleset version bump is a noted, intentional act. Drift that you did NOT
intend is the bug.
"""
import os
import sys
import json
import subprocess
import hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conformance_baseline.json")

# Each probe runs with cwd=ROOT and prints {"golden": hex, "details": {...}} as its last stdout line.
PROBES = {
    "AetherPulse": r'''
import sys, os, json, glob, hashlib
sys.path.insert(0, "AetherPulse"); sys.path.insert(0, "chronicle")
import export_vectors as X
X.export()
items = {}
for f in sorted(glob.glob(os.path.join("AetherPulse", "fixtures", "*.json"))):
    d = json.load(open(f)); items[d["name"]] = {"final_hash": d["final_hash"], "merkle_root": d["merkle_root"]}
print(json.dumps({"golden": hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest(), "details": items}))
''',
    "AetherManifold": r'''
import sys, os, json, glob, hashlib
sys.path.insert(0, "AetherManifold"); sys.path.insert(0, "chronicle")
import conformance as C
C.export_fixtures()
items = {}
for f in sorted(glob.glob(os.path.join("AetherManifold", "fixtures", "*.json"))):
    d = json.load(open(f)); items[d["problem"]] = {"final_hash": d["final_hash"], "merkle_root": d["merkle_root"]}
print(json.dumps({"golden": hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest(), "details": items}))
''',
    "VeriSim": r'''
import sys, os, json, hashlib
sys.path.insert(0, "VeriSim"); sys.path.insert(0, "chronicle")
import scenarios as SC, runner as RN
sh = RN.run_simulation("brake_1d", SC.brake_seed(30, 8, 10), input_data={"m": "regress"})  # unsigned -> deterministic
g = {"scenario": sh["scenario"], "steps": sh["steps"], "merkle_root": sh["merkle_root"], "path_hash": sh["tessera"]["path_hash"]}
print(json.dumps({"golden": hashlib.sha256(json.dumps(g, sort_keys=True).encode()).hexdigest(), "details": g}))
''',
    "VeriVerse": r'''
import sys, os, json, hashlib
sys.path.insert(0, "VeriVerse"); sys.path.insert(0, "chronicle")
import shards as S, world as W
coords = [(cx, cz) for cx in range(2) for cz in range(2)]
ws, _ = S.world_shard(98247, coords)
g = {"world_root": ws["root"], "chunk00": W.chunk_hash(W.generate_chunk(98247, 0, 0))}
print(json.dumps({"golden": hashlib.sha256(json.dumps(g, sort_keys=True).encode()).hexdigest(), "details": g}))
''',
    "aegis_gate": r'''
import sys, os, json, hashlib
sys.path.insert(0, "aegis_gate"); sys.path.insert(0, "chronicle")
import run_pipeline as RP
summary, accounts = RP.run(verbose=False)
ledger = [json.loads(l) for l in open(RP.LEDGER_PATH) if l.strip()]
g = {"verdicts": [[l, v] for l, v, _ in summary], "chain": [r["committed_hash"] for r in ledger]}
print(json.dumps({"golden": hashlib.sha256(json.dumps(g, sort_keys=True).encode()).hexdigest(),
                  "details": {"n_decisions": len(g["chain"]), "verdicts": g["verdicts"]}}))
''',
}


def _run_probe(name, code):
    env = dict(os.environ, PYTHONHASHSEED="0", CHRONICLE_SIGNER_PASSPHRASE="regress")
    p = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=180)
    if p.returncode != 0:
        return None, "probe failed: %s" % (p.stderr.strip().splitlines()[-1] if p.stderr.strip() else "rc=%d" % p.returncode)
    line = p.stdout.strip().splitlines()[-1]
    try:
        return json.loads(line), None
    except Exception as e:
        return None, "bad probe output (%s)" % e


def collect():
    """Run every application probe; return {app: {golden, details} | {error}}."""
    out = {}
    for name, code in PROBES.items():
        res, err = _run_probe(name, code)
        out[name] = res if res is not None else {"error": err}
    return out


def load_baseline():
    return json.load(open(BASELINE)) if os.path.exists(BASELINE) else {}


def compare(current, baseline):
    """Return (ok, faults). fault names the exact app + reason (MISSING / DRIFT / ERROR)."""
    faults = []
    for app in sorted(set(list(current) + list(baseline))):
        cur = current.get(app, {})
        if "error" in cur:
            faults.append({"app": app, "reason": "ERROR", "detail": cur["error"]})
        elif app not in baseline:
            faults.append({"app": app, "reason": "UNPINNED (new app; run --update)"})
        elif app not in current:
            faults.append({"app": app, "reason": "MISSING (probe absent)"})
        elif cur.get("golden") != baseline[app].get("golden"):
            faults.append({"app": app, "reason": "DRIFT", "baseline": baseline[app].get("golden", "")[:16],
                           "current": cur.get("golden", "")[:16]})
    return (not faults), faults


def write_baseline(current):
    pinned = {app: {"golden": v["golden"], "details": v["details"]} for app, v in current.items() if "golden" in v}
    with open(BASELINE, "w") as fh:
        json.dump(pinned, fh, indent=2, sort_keys=True)
    return pinned
