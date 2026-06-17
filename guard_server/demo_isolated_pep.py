"""
guard_server/demo_isolated_pep.py — the privilege-separated PEP with a filesystem clamp.

Run:  PYTHONHASHSEED=0 python3 demo_isolated_pep.py

  A. SETUP       — print the one-time separate-user setup; start the PEP on loopback.
  B. ALLOW       — a write inside the allow-listed design dir is authorized (signed + action-bound).
  C. ESCAPE      — a path that climbs out via `..` is denied and logged.
  D. SYMLINK     — a symlink whose target is outside the allow-list is denied (resolved before check).
  E. TAMPER      — the agent flips a DENY verdict to ALLOW; verification fails (bad signature).
  F. NO-FORGE    — the agent signs its own ALLOW with a rogue key; the server verifier rejects it.
"""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "llm_toolkit"))
import agent_core as core
from agent_core import require_deterministic_hashing
from agent_guard import Ed25519Signer
from isolated_pep import IsolatedPEP, verify_action_verdict
import urllib.request, json


def _authorize(url, action):
    req = urllib.request.Request(url + "/authorize", data=json.dumps(action).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


if __name__ == "__main__":
    require_deterministic_hashing("guard_server")
    work = tempfile.mkdtemp()
    design = os.path.join(work, "projects", "design"); os.makedirs(design)
    secrets = os.path.join(work, "secrets"); os.makedirs(secrets)
    open(os.path.join(secrets, "id_rsa"), "w").write("k")

    print("A) SETUP (separate-user guidance printed to stderr); allow-list = %s" % design)
    with IsolatedPEP([design], violation_log=os.path.join(work, "viol.jsonl")) as pep:
        url = pep.base_url
        verifier = pep.public_verifier()

        print("\nB) ALLOW: write inside the design dir:")
        good = {"op": "write", "paths": [os.path.join(design, "logo.svg")]}
        r = _authorize(url, good)
        ok, why = verify_action_verdict(r, verifier, good)
        print("   decision=%s  verify=%s (%s)" % (r["verdict"]["decision"], ok, why))

        print("\nC) ESCAPE: write via .. outside the allow-list:")
        esc = {"op": "write", "paths": [os.path.join(design, "..", "..", "secrets", "id_rsa")]}
        r = _authorize(url, esc)
        print("   decision=%s  reasons=%s" % (r["verdict"]["decision"], r["verdict"]["reasons"]))

        print("\nD) SYMLINK: a link inside design pointing at secrets/ is resolved then denied:")
        link = os.path.join(design, "sneaky")
        try:
            os.symlink(secrets, link)
            sym = {"op": "write", "paths": [os.path.join(link, "id_rsa")]}
            r = _authorize(url, sym)
            print("   decision=%s  reasons=%s" % (r["verdict"]["decision"], r["verdict"]["reasons"]))
        except OSError as e:
            print("   (symlink unsupported here: %s)" % e)

        print("\nE) TAMPER: agent flips a DENY to ALLOW on its own stored verdict:")
        denied = _authorize(url, esc)                         # fresh DENY bound to esc
        forged = {"verdict": dict(denied["verdict"]), "signature": denied["signature"], "algo": denied["algo"]}
        forged["verdict"]["decision"] = "allow"               # binding still matches; only the body changed
        ok, why = verify_action_verdict(forged, verifier, esc)
        print("   accepted=%s (%s)" % (ok, why))

        print("\nF) NO-FORGE: agent signs its own ALLOW with a rogue key:")
        rogue = Ed25519Signer.generate()
        vcore = {"request_hash": core.state_hash(esc), "policy_hash": pep.policy.policy_hash,
                 "decision": "allow", "reasons": []}
        fake = {"verdict": vcore, "signature": rogue.sign(core.canonical_bytes(vcore)), "algo": "ed25519"}
        ok, why = verify_action_verdict(fake, verifier, esc)
        print("   accepted=%s (%s)" % (ok, why))

        print("\n   violations logged (append-only): %d" %
              sum(1 for _ in open(os.path.join(work, "viol.jsonl"))))
        print("   NOTE: bounded authority + tamper-evidence, NOT host tamper-proofness. Integrity != truth.")
