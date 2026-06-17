"""
pact/demo_pact.py — a three-agent covenant, then forensic isolation of a breach.

Run:  PYTHONHASHSEED=0 python3 demo_pact.py

  A. COVENANT     — Agent A -> B -> C each cross-attest, binding their new state hash to the prior agent's.
  B. AUDIT OK     — an external auditor replays the multi-agent chain on pinned public keys: VERIFIED.
  C. FORGERY      — a rogue key impersonates A; the covenant rejects it (A is pinned, the sig fails).
  D. INJECTION    — an operator (holding B's real key) injects a state that breaks B's invariant; the
                    multi-chain audit isolates the EXACT agent + link where the trail deviated.

Honest bound: non-repudiation UNDER the pinned-key assumption; a breach is self-evident to anyone verifying
with the pinned keys — no broadcast, no consensus, not a blockchain. Integrity != truth.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant as P
import core
from agent_guard import Ed25519Signer, Ed25519Verifier, ed25519_available, make_guard_signer

# each agent enforces: the running accumulator never decreases (a monotonic covenant rule)
def monotonic(prev_state, new_state):
    return new_state["acc"] >= prev_state["acc"]

INVARIANTS = {"A": None, "B": monotonic, "C": monotonic}


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("[pact] run with PYTHONHASHSEED=0\n"); raise SystemExit(2)
    if not ed25519_available():
        print("[pact] cryptography unavailable — pact needs Ed25519 for third-party-verifiable covenants."); raise SystemExit(0)

    A, B, C = Ed25519Signer.generate(), Ed25519Signer.generate(), Ed25519Signer.generate()
    REGISTRY = {"A": Ed25519Verifier(A.public_material()), "B": Ed25519Verifier(B.public_material()),
                "C": Ed25519Verifier(C.public_material())}

    print("A) COVENANT (A -> B -> C, each binding to the prior hash):")
    rA = P.state_receipt("A", {"acc": 10}, A)
    lA = {"verdict": None, "verdict_sig": None, "receipt": rA}
    lB = P.cross_attest(rA, "B", {"acc": 15}, B, monotonic, REGISTRY)
    lC = P.cross_attest(lB["receipt"], "C", {"acc": 22}, C, monotonic, REGISTRY)
    chain = [lA, lB, lC]
    for l in chain:
        print("   %s acc=%s  hash=%s" % (l["receipt"]["agent"], l["receipt"]["state"]["acc"], l["receipt"]["state_hash"][:10]))

    print("\nB) AUDIT (external auditor, pinned public keys):")
    ok, fault = P.audit_covenant(chain, REGISTRY, INVARIANTS)
    print("   verdict: %s" % ("VERIFIED — covenant intact" if ok else "REJECTED %s" % fault))

    print("\nC) FORGERY (rogue key impersonates A):")
    rogue = Ed25519Signer.generate()
    forged = P.state_receipt("A", {"acc": 999}, rogue)
    ok, why = P.verify_receipt(forged, REGISTRY)
    print("   accepted=%s (%s)" % (ok, why))

    print("\nD) INJECTION (operator holds B's REAL key but injects acc that drops 15 -> 9):")
    # operator can sign as B, but the covenant rule (monotonic) is checked on replay
    badB = P.state_receipt("B", {"acc": 9}, B, prev_hash=rA["state_hash"])
    vcore = {"from": "A", "from_hash": rA["state_hash"], "to": "B", "to_hash": badB["state_hash"]}
    bad_link = {"verdict": vcore, "verdict_sig": B.sign(core.canonical_bytes(vcore)), "receipt": badB}
    mal_chain = [lA, bad_link]
    ok, fault = P.audit_covenant(mal_chain, REGISTRY, INVARIANTS)
    print("   multi-chain audit -> %s" % ("VERIFIED (should NOT happen)" if ok else "REJECTED %s" % fault))
    print("\n   NOTE: B's signature is valid, but the covenant rule isolates the exact link/agent that broke it.")
    print("   Non-repudiation under the pinned-key assumption; not a blockchain. Integrity != truth.")
