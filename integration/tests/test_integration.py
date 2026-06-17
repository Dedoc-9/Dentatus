"""Stdlib unittest suite for the coupled full stack + the coupled/uncoupled parity guard."""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))                       # integration/
sys.path.insert(0, os.path.join(ROOT, "llm_toolkit"))
sys.path.insert(0, os.path.join(ROOT, "guard_server"))

import agent_core as core
from agent_core import AgentStateMachine, audit_chain, source_hash, TransitionRefused
from agent_capture import LLMCapture, MockLLMClient
from agent_guard import Ed25519Signer, Ed25519Verifier
import policy as P
from policy_server import PolicyServer
import client as pep_client
import pep_agent
from pep_agent import refund_pep_transition, pep_guard, run_pep_step, POLICY_VERSION
import agent_core as coupled
import vendored_core as uncoupled


BUSINESS = {"prompt": "double charge $40", "system": "Refund policy v3.", "seed": 7, "amount": 40}


def _fresh_machine_and_server():
    pol = P.Policy(version=POLICY_VERSION, alignment_threshold=0.85)
    srv = PolicyServer(policy=pol).start()
    pep_agent.configure_trusted_pep(srv.signer.public_material())
    recorder = Ed25519Signer.generate()
    machine = AgentStateMachine(recorder, source_hash(refund_pep_transition, pep_guard))
    return pol, srv, recorder, machine


class TestCoupledStack(unittest.TestCase):
    def test_allow_commit_and_replay(self):
        pol, srv, recorder, machine = _fresh_machine_and_server()
        try:
            llm = MockLLMClient(flight_ms=0.0)
            rec, _ = run_pep_step(machine, "S1", BUSINESS, "APPROVE refund $40", 0.93, llm, srv.base_url)
            v = audit_chain([rec], Ed25519Verifier(recorder.public_material()), refund_pep_transition, pep_guard)
            self.assertTrue(v.ok)
        finally:
            srv.stop()

    def test_pep_denies_pii_no_commit(self):
        pol, srv, recorder, machine = _fresh_machine_and_server()
        try:
            llm = MockLLMClient(flight_ms=0.0)
            with self.assertRaises(TransitionRefused):
                run_pep_step(machine, "S1", BUSINESS, "APPROVE; SSN 123-45-6789", 0.93, llm, srv.base_url)
            self.assertEqual(machine.seq, 0)                     # nothing committed
        finally:
            srv.stop()

    def test_forged_authorization_rejected_despite_valid_chain(self):
        pol, srv, recorder, machine = _fresh_machine_and_server()
        try:
            llm = MockLLMClient(flight_ms=0.0)
            rogue = Ed25519Signer.generate()
            bad_req = pep_client.make_request(
                "postflight", {"response_text": "APPROVE; SSN 123-45-6789", "alignment_score": 0.93}, POLICY_VERSION)
            vcore = {"request_hash": core.state_hash(bad_req), "policy_version": POLICY_VERSION,
                     "policy_hash": pol.policy_hash, "decision": "allow", "reasons": []}
            forged = {"verdict": vcore, "signature": rogue.sign(core.canonical_bytes(vcore)), "algo": "ed25519"}
            cap = LLMCapture(client=llm)
            cap.call("refund_reasoning", prompt=BUSINESS["prompt"], system=BUSINESS["system"],
                     seed=BUSINESS["seed"], scripted="APPROVE; SSN 123-45-6789")
            sealed = cap.sealed_inputs({**BUSINESS, "alignment_score": 0.93})
            sealed["_pep"] = {"request": bad_req, "authorization": forged}
            mal = AgentStateMachine(recorder, source_hash(refund_pep_transition, pep_guard)).commit(
                "S1", sealed, refund_pep_transition(sealed), lambda i, o: True)
            v = audit_chain([mal], Ed25519Verifier(recorder.public_material()), refund_pep_transition, pep_guard)
            self.assertFalse(v.ok)                               # chain ok, but guard catches forged allow
            self.assertIn("GUARDRAIL", v.reason)
        finally:
            srv.stop()


class TestParity(unittest.TestCase):
    def test_canonical_and_hash_parity(self):
        for payload in [{"a": [1, 2.0/3.0], "b": {"x": True}}, {"u": "naïve ✓", "n": None}, {"t": (1, 2)}]:
            self.assertEqual(coupled.canonical_bytes(payload), uncoupled.canonical_bytes(payload))
            self.assertEqual(coupled.state_hash(payload), uncoupled.state_hash(payload))

    def test_source_hash_parity(self):
        self.assertEqual(coupled.source_hash(refund_pep_transition), uncoupled.source_hash(refund_pep_transition))


if __name__ == "__main__":
    unittest.main(verbosity=2)
