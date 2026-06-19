"""
verify_all.py — the single top-level "verify everything" entrypoint for the whole repo.

Two gates, one verdict:
  1. the WORKBENCH preflight  — 26 sibling suites + the coupled/uncoupled parity proof
     (integration/preflight_check.py)
  2. the APPLICATION conformance — the 5 standalone products reproduce their pinned content hashes
     (conformance_suite/run.py)

Exit 0 only if BOTH pass. This is the canonical green/red for the repo — workbench *and* the products
downstream of it — that a CI gate or a contributor runs once. It does NOT re-implement either gate; it runs
each as a real subprocess (earned output, not a banner) under PYTHONHASHSEED=0.

  python3 verify_all.py
"""
import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
GATES = [
    ("workbench preflight  (35 suites + parity)", "integration/preflight_check.py"),
    ("application conformance (5 goldens)", "conformance_suite/run.py"),
]


def _run(rel):
    env = dict(os.environ, PYTHONHASHSEED="0")
    env.setdefault("CHRONICLE_SIGNER_PASSPHRASE", "verify_all")
    return subprocess.run([sys.executable, os.path.join(ROOT, rel)], cwd=ROOT, env=env).returncode == 0


def main():
    results = []
    for label, rel in GATES:
        print("\n" + "=" * 78 + "\n== %s\n" % label + "=" * 78)
        results.append((label, _run(rel)))
    print("\n" + "#" * 78)
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    all_ok = all(ok for _, ok in results)
    print("#" * 78)
    if all_ok:
        print("[ALL VERIFIED]  workbench + applications reproduce their pinned state. Proceed.")
        return 0
    print("[BLOCKED]  a gate failed above. Fix the change, not the gate (AGENTS.md S6). For an *intended*")
    print("           application change, re-pin with: PYTHONHASHSEED=0 python3 conformance_suite/run.py --update")
    return 1


if __name__ == "__main__":
    sys.exit(main())
