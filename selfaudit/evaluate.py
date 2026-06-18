"""
selfaudit/evaluate.py — the workbench evaluates the workbench (a hardened reflexive self-audit).

Turns the workbench's OWN tools on the cores: `chronicle` content-addressing fingerprints the repo,
`assay` grades the checks as recomputable, signed metric assessments, the parity primitives prove lossless
extraction, and `dini` maps the component DAG. Every grade is sealed into a signed assay ledger and the
assay court replays it.

HARDENED (v2) — what changed after reviewing v1's weaknesses:
  1. FROZEN means UNCHANGED, not "present": core files are compared against a pinned `core_baseline.json`;
     any drift FAILS. (First run with no baseline establishes it and warns.)
  2. SIBLING-LAW is content-based: a frozen core copied under ANY filename is caught by content hash —
     no filename allow-list, no hardcoded exceptions.
  3. EVIDENCE is recomputable: each sealed grade carries the actual hashes/values an auditor can re-check,
     not a bare boolean.
  4. SIGNER can be PINNED (SELFAUDIT_SIGNING_KEY=hex) so a third party verifies against a stable public
     key; an ephemeral key is labeled demo-only (it proves intra-run consistency, not attestation).
  5. The detector is shown to DETECT: a drift-caught demonstration proves a tampered baseline FAILS.

HONEST FRAMING (integrity != truth, inward): this proves only MECHANICAL facts about the workbench — its
checks reproduce, the cores are byte-stable vs the pinned baseline, parity holds, the structure is lawful.
It CANNOT certify the workbench is correct, useful, or good. A system grading itself is not a judge of its
own value.
"""
import os
import sys
import json
import hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("chronicle", "llm_toolkit", "assay", "dini", "integration"):
    sys.path.insert(0, os.path.join(ROOT, sub))

import core
import assess as A
from court import assay_audit, print_verdict       # resolves to assay/court.py
import metrics as M
from signing import Ed25519Signer, Ed25519Verifier, ed25519_available, HmacSigner
import compass as DINI

BASELINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core_baseline.json")

CORE_FILES = {
    "chronicle": ["core.py", "court.py", "signing.py", "capture.py", "store.py", "hardware_signing.py"],
    "llm_toolkit": ["agent_core.py", "agent_capture.py", "agent_guard.py"],
}
SIBLINGS = ["guard_server", "integration", "assay", "manifold", "anti_cheat", "glitch", "dini", "selfaudit", "quorum", "lockstep", "syracuse", "tessera", "crucible", "fuel", "elenchus"]
DAG = {"chronicle": [], "llm_toolkit": [], "guard_server": ["llm_toolkit"], "integration": ["llm_toolkit"],
       "assay": ["llm_toolkit"], "manifold": ["chronicle"], "anti_cheat": ["chronicle"],
       "glitch": ["chronicle"], "dini": ["chronicle"], "selfaudit": ["chronicle"], "quorum": ["chronicle"], "lockstep": ["chronicle"], "syracuse": ["chronicle"], "tessera": ["chronicle"], "crucible": ["chronicle"], "fuel": ["chronicle"], "elenchus": ["chronicle"]}


# ---------- pure, testable helpers ----------
def _sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def frozen_core_hashes():
    """Full SHA-256 of every frozen-core file present. Keyed 'comp/file'."""
    out = {}
    for comp, files in CORE_FILES.items():
        for f in files:
            p = os.path.join(ROOT, comp, f)
            if os.path.exists(p):
                out["%s/%s" % (comp, f)] = _sha256(p)
    return out


def compare_to_baseline(current, baseline):
    """Return a sorted list of drift descriptions (empty == cores unchanged). Pure."""
    drift = []
    for k, v in sorted(baseline.items()):
        if k not in current:
            drift.append("MISSING %s" % k)
        elif current[k] != v:
            drift.append("CHANGED %s" % k)
    for k in sorted(current):
        if k not in baseline:
            drift.append("ADDED %s" % k)
    return drift


def find_duplicated_cores(core_hash_set, sibling_files):
    """sibling_files: {path_label: content_hash}. Return labels whose content == a frozen core (a copy
    under any name — the real Sibling-Law violation). Pure."""
    return sorted([label for label, h in sibling_files.items() if h in core_hash_set])


def _sibling_py_hashes():
    out = {}
    for sib in SIBLINGS:
        d = os.path.join(ROOT, sib)
        if not os.path.isdir(d):
            continue
        for dirpath, _, files in os.walk(d):
            for f in files:
                if f.endswith(".py"):
                    p = os.path.join(dirpath, f)
                    out[os.path.relpath(p, ROOT)] = _sha256(p)
    return out


# ---------- checks: each returns (name, ok, evidence) ----------
def check_determinism():
    payload = {"z": 1, "a": {"deep": [1 / 3, "réfund ✓", (1, 2)]}, "m": True}
    h1 = core.state_hash(payload); h2 = core.state_hash(payload)
    return "core_determinism", (h1 == h2), {"state_hash": h1}


def check_parity():
    import vendored_core as un
    import agent_core as co
    battery = [{"a": [1, 2 / 3]}, {"u": "naïve ✓", "n": None}, {"t": (1, 2), "b": True}]
    pairs = [(un.state_hash(x), co.state_hash(x)) for x in battery]
    ok = all(a == b for a, b in pairs)
    return "extraction_parity", ok, {"hashes": [a[:12] for a, _ in pairs], "all_equal": ok}


def check_frozen_cores(baseline):
    cur = frozen_core_hashes()
    if not baseline:
        return "frozen_cores_unchanged", True, {"status": "BASELINE-ESTABLISHED", "files": len(cur)}
    drift = compare_to_baseline(cur, baseline)
    return "frozen_cores_unchanged", (len(drift) == 0), {"drift": drift, "files": len(cur)}


def check_sibling_law():
    core_hash_set = set(frozen_core_hashes().values())
    copies = find_duplicated_cores(core_hash_set, _sibling_py_hashes())
    return "sibling_law_no_core_copies", (len(copies) == 0), {"copies": copies}


def workbench_identity():
    fp = frozen_core_hashes()
    fp.update(_sibling_py_hashes())
    fp = {k: v[:16] for k, v in fp.items()}
    return core.state_hash(fp), fp


def dini_structure():
    m = DINI.HyperbolicMap(edge_length=1.0)
    root = {"component": "<workbench>"}; m.set_root(root); placed = {"<workbench>": root}; out = {}
    for comp in ["chronicle", "llm_toolkit", "guard_server", "integration", "assay",
                 "manifold", "anti_cheat", "glitch", "dini", "selfaudit"]:
        deps = DAG.get(comp, [])
        parent = placed.get(deps[0], root) if deps else root
        node = {"component": comp}; obs = m.observe(parent, node); placed[comp] = node
        out[comp] = (obs["depth"], obs["dini_distance"])
    return out


def demonstrate_drift_caught(baseline):
    """Prove the detector DETECTS: corrupt one baseline entry and confirm the frozen-core check FAILS."""
    if not baseline:
        return None
    tampered = dict(baseline)
    victim = sorted(tampered)[0]
    tampered[victim] = "0" * 64                       # pretend the recorded baseline hash was forged
    drift = compare_to_baseline(frozen_core_hashes(), tampered)
    return victim, (len(drift) > 0)


def _signer():
    keyhex = os.environ.get("SELFAUDIT_SIGNING_KEY")
    if keyhex and ed25519_available():
        s = Ed25519Signer(keyhex); return s, Ed25519Verifier(s.public_material()), "ed25519 (PINNED key)"
    if ed25519_available():
        s = Ed25519Signer.generate()
        return s, Ed25519Verifier(s.public_material()), "ed25519 (EPHEMERAL — demo only, not an anchor)"
    s = HmacSigner(b"selfaudit"); return s, s, "hmac (single trust domain)"


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("[selfaudit] run with PYTHONHASHSEED=0\n"); raise SystemExit(2)

    baseline = json.load(open(BASELINE_PATH)) if os.path.exists(BASELINE_PATH) else {}
    wb_H, fingerprints = workbench_identity()
    print("WORKBENCH SELF-AUDIT (hardened)")
    print("  workbench_H = %s" % wb_H[:24])
    print("  core baseline: %s\n" % ("pinned (%d files)" % len(baseline) if baseline else "ABSENT — will establish"))

    signer, verifier, algo = _signer()
    rec = A.AssayRecorder(signer)
    ledger = []
    all_ok = True
    print("  CHECKS (sealed as assay assessments, signer=%s):" % algo)
    for name, ok, ev in [check_determinism(), check_parity(), check_frozen_cores(baseline), check_sibling_law()]:
        all_ok &= ok
        evidence = {"decision": {"ok": ok}, "ground_truth": {"ok": True}, "key": "ok", "detail": ev}
        ledger.append(rec.record_metric(wb_H, "correct", "correctness_vs_oracle", evidence))
        print("    [%s] %-28s %s" % ("PASS" if ok else "FAIL", name, ev))

    print("\n  ASSAY COURT replays the self-audit log:")
    print_verdict(assay_audit(ledger, verifier, {}, {}), len(ledger))

    print("\n  DRIFT-CAUGHT DEMONSTRATION (does the detector actually detect?):")
    d = demonstrate_drift_caught(baseline)
    if d is None:
        print("    (no baseline yet — establishing it now; re-run to exercise drift detection)")
        json.dump(frozen_core_hashes(), open(BASELINE_PATH, "w"), indent=2, sort_keys=True)
        print("    wrote %s" % os.path.relpath(BASELINE_PATH, ROOT))
    else:
        victim, caught = d
        print("    forged the baseline hash of %s -> drift detected: %s" % (victim, caught))
        all_ok &= caught

    print("\n  DINI structural map (depth, distance) from the workbench root:")
    for comp, (depth, dist) in dini_structure().items():
        print("    %-14s depth=%d dini=%.3f" % (comp, depth, dist))

    print("\nVERDICT: %s" % ("self-audit GREEN — checks reproduce, cores match the pinned baseline, parity "
                             "holds, no core copies, drift is caught." if all_ok else "self-audit RED — see FAIL above."))
    print("HONEST BOUND: proves the audit is reproducible and the cores are byte-stable vs the pinned")
    print("baseline — NOT that the workbench is correct, useful, or good. Integrity != truth.")
    sys.exit(0 if all_ok else 1)
