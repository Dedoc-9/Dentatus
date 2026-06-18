"""
integration/preflight_check.py — an HONEST session preflight for the Chronicle workbench.

Per AGENTS.md it does NOT relabel a determinism guard as a security verdict and it does NOT print
"ready" without evidence. It actually RUNS the verification contract (all suites + the parity proof)
as subprocesses under PYTHONHASHSEED=0 and reports true results. Exit 0 only if everything actually
passed; exit 1 otherwise. Stdlib-only.

What a green result means:  no regressions, and coupled==uncoupled primitive parity holds.
What it does NOT mean:      that the host is uncompromised, the inputs are honest, or any decision is
                            correct/fair/wise. Integrity != truth. (AGENTS.md §3)
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SUITES = [
    "chronicle/tests/test_chronicle.py",
    "chronicle/tests/test_hardware_signing.py",
    "llm_toolkit/tests/test_llm_toolkit.py",
    "guard_server/tests/test_guard_server.py",
    "guard_server/tests/test_isolated_pep.py",
    "integration/tests/test_integration.py",
    "assay/tests/test_assay.py",
    "manifold/tests/test_manifold.py",
    "anti_cheat/tests/test_anti_cheat.py",
    "glitch/tests/test_glitch.py",
    "dini/tests/test_dini.py",
    "selfaudit/tests/test_selfaudit.py",
    "wobble/tests/test_wobble.py",
    "ration/tests/test_ration.py",
    "stride/tests/test_stride.py",
    "pact/tests/test_pact.py",
    "quorum/tests/test_quorum.py",
    "lockstep/tests/test_lockstep.py",
    "syracuse/tests/test_syracuse.py",
    "tessera/tests/test_tessera.py",
    "crucible/tests/test_crucible.py",
    "fuel/tests/test_fuel.py",
]
PARITY = "integration/parity_proof.py"


def _run(relpath, expect_substr=None):
    """Run a script under PYTHONHASHSEED=0; return (ok, detail). We SET the seed for the child rather
    than demanding the caller's env be 0 (that would be the cargo-cult check AGENTS.md S5 forbids)."""
    env = dict(os.environ, PYTHONHASHSEED="0")
    env.setdefault("CHRONICLE_SIGNER_PASSPHRASE", "preflight")
    try:
        p = subprocess.run([sys.executable, os.path.join(ROOT, relpath)],
                           capture_output=True, text=True, env=env, cwd=ROOT, timeout=180)
    except Exception as e:
        return False, "could not run (%s)" % e
    out = p.stdout + p.stderr
    if expect_substr is not None:
        return (expect_substr in out), ("found" if expect_substr in out else "missing %r" % expect_substr)
    return (p.returncode == 0), ("rc=%d" % p.returncode)


def preflight():
    print("Chronicle workbench preflight - running the verification contract (not just env checks).\n")
    if os.environ.get("PYTHONHASHSEED") != "0":
        print("  note: caller PYTHONHASHSEED != 0; setting it for the child runs.\n")

    results = []
    for s in SUITES:
        ok, detail = _run(s)
        results.append(ok)
        print("  [%s] %-44s %s" % ("PASS" if ok else "FAIL", s, "" if ok else "(%s)" % detail))

    parity_ok, _ = _run(PARITY, expect_substr="PARITY HOLDS")
    results.append(parity_ok)
    print("  [%s] %-44s %s" % ("PASS" if parity_ok else "FAIL", PARITY, "PARITY HOLDS" if parity_ok else "(parity broken)"))

    all_ok = all(results)
    print()
    if all_ok:
        print("[FOUNDRY VERIFIED]")
        print("  - %d/%d suites green; primitive parity holds (parity_proof.py)" % (len(SUITES), len(SUITES)))
        print("  - Out-of-process policy clamps + tiered hardware signer present and tested")
        print("  - Cognitive modesty acknowledged: integrity != truth (this verifies regressions, not")
        print("    host integrity, input honesty, or decision correctness)")
        print("\nProceed with refactoring bounds secured.")
    else:
        print("[FOUNDRY BLOCKED] one or more checks failed above. Fix the change, not the test (AGENTS.md S6).")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(preflight())
