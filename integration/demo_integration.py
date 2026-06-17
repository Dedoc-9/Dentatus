"""
integration/demo_integration.py — the COUPLED full stack end to end.

   llm_toolkit (capture + ledger)  +  guard_server (PEP)  +  content-addressed replay court

Run:  PYTHONHASHSEED=0 python3 demo_integration.py

  A. AUTHORIZE + COMMIT   — each refund's output is authorized by the server-side PEP; the SIGNED verdict
                            is captured into the transition and committed to the ledger.
  B. REPLAY COURT         — replays every transition bit-for-bit AND re-verifies each embedded PEP verdict.
  C. DENY -> NO COMMIT    — a request the PEP denies (PII) is refused fail-closed; the ledger never grows.
  D. SEPARATION OF POWERS — an operator holding the legitimate RECORDER key forges a PEP 'allow' with a key
                            it controls. The chain signature is valid, yet the auditor still REJECTS it,
                            because the guard verifies verdicts against the PINNED server key. The recorder
                            can attest what happened; it cannot manufacture authorization.

Integrity is not truth: this proves what was recorded + which authorizations were genuinely granted — not
that any refund decision was correct.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "llm_toolkit"))
sys.path.insert(0, os.path.join(_ROOT, "guard_server"))

import agent_core as core
from agent_core import AgentStateMachine, audit_chain, print_verdict, source_hash, TransitionRefused
from agent_capture import LLMCapture, MockLLMClient
from agent_guard import Ed25519Signer, Ed25519Verifier

import policy as P
from policy_server import PolicyServer
import client as pep_client

import pep_agent
from pep_agent import refund_pep_transition, pep_guard, run_pep_step, POLICY_VERSION


if __name__ == "__main__":
    core.require_deterministic_hashing("integration")
    llm = MockLLMClient(flight_ms=10.0)
    pol = P.Policy(version=POLICY_VERSION, alignment_threshold=0.85)

    with PolicyServer(policy=pol) as srv:
        # pin the server's public key as the trust anchor the guard checks against
        pep_agent.configure_trusted_pep(srv.signer.public_material())
        # the LEDGER is attested by a SEPARATE recorder key (separation of powers)
        recorder = Ed25519Signer.generate()
        recorder_verifier = Ed25519Verifier(recorder.public_material())
        ruleset = source_hash(refund_pep_transition, pep_guard)
        machine = AgentStateMachine(recorder, ruleset)

        print("A) AUTHORIZE + COMMIT (PEP@%s  policy=%s)" % (srv.base_url, pol.policy_hash))
        ledger = []
        good = [
            ("STEP-001", {"prompt": "double-charged $40 on #A1", "system": "Refund policy v3.", "seed": 7, "amount": 40},
             "APPROVE refund of $40; duplicate charge confirmed.", 0.93),
            ("STEP-002", {"prompt": "refund 90 days late, policy 30", "system": "Refund policy v3.", "seed": 7, "amount": 25},
             "DENY refund; outside the 30-day window.", 0.91),
        ]
        for step_id, business, scripted, align in good:
            rec, _ = run_pep_step(machine, step_id, business, scripted, align, llm, srv.base_url)
            ledger.append(rec)
            o = rec["frame"]["outputs"]
            print("   %s -> approved=%s amount=%s pep=%s  +%s"
                  % (step_id, o["approved"], o["refund_amount"], o["pep_decision"], rec["committed_hash"][:10]))

        print("\nB) REPLAY COURT (chain + embedded PEP verdicts, no live model/PEP):")
        print_verdict(audit_chain(ledger, recorder_verifier, refund_pep_transition, pep_guard), len(ledger))

        print("\nC) DENY -> NO COMMIT: PEP refuses a PII-leaking output:")
        try:
            run_pep_step(machine, "STEP-PII", good[0][1], "APPROVE; mail to SSN 123-45-6789.", 0.93, llm, srv.base_url)
            print("   committed (should NOT happen)")
        except TransitionRefused as e:
            print("   refused fail-closed: %s" % e)
        print("   ledger length unchanged: %d" % len(ledger))

        print("\nD) SEPARATION OF POWERS: operator forges a PEP 'allow' with a key it controls,")
        print("   then signs the ledger with the LEGITIMATE recorder key:")
        rogue = Ed25519Signer.generate()
        bad_req = pep_client.make_request(
            "postflight", {"response_text": "APPROVE; SSN 123-45-6789", "alignment_score": 0.93}, POLICY_VERSION)
        vcore = {"request_hash": core.state_hash(bad_req), "policy_version": POLICY_VERSION,
                 "policy_hash": pol.policy_hash, "decision": "allow", "reasons": []}
        forged = {"verdict": vcore, "signature": rogue.sign(core.canonical_bytes(vcore)), "algo": "ed25519"}
        cap = LLMCapture(client=llm)
        cap.call("refund_reasoning", prompt=good[0][1]["prompt"], system=good[0][1]["system"],
                 seed=good[0][1]["seed"], scripted="APPROVE; SSN 123-45-6789")
        sealed = cap.sealed_inputs({**good[0][1], "alignment_score": 0.93})
        sealed["_pep"] = {"request": bad_req, "authorization": forged}
        # operator bypasses its own local guard at commit time, but uses the REAL recorder key:
        permissive = AgentStateMachine(recorder, ruleset, prev_hash=machine.prev, seq=machine.seq)
        mal = permissive.commit("STEP-FORGE", sealed, refund_pep_transition(sealed), lambda i, o: True)
        mal_ledger = ledger + [mal]
        print("   chain signature is valid (real recorder key); auditor still runs the pinned PEP guard:")
        print_verdict(audit_chain(mal_ledger, recorder_verifier, refund_pep_transition, pep_guard), len(mal_ledger))

        print("\n   NOTE: the recorder attests WHAT happened; it cannot manufacture authorization.")
        print("   Honest scope: loopback PEP, no TLS/authn/isolation. Integrity != truth.")
