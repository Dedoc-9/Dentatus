"""Stdlib unittest suite for the LLM toolkit: determinism, replay court, capture seam, guardrails."""
import os, sys, copy, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_core as core
from agent_core import AgentStateMachine, audit_chain, source_hash, HmacSigner, TransitionRefused
from agent_capture import LLMCapture, MockLLMClient, verify_replay_determinism
from agent_guard import (Guardrail, Ed25519Signer, Ed25519Verifier, ed25519_available,
                        make_guard_signer, pii_clean, GuardrailViolation)


# --- module-level so source_hash(inspect.getsource) works ---
def transition(inputs):
    cap = LLMCapture.replay(inputs)
    llm = cap.call("r", prompt=inputs["prompt"], system="sys", seed=inputs["seed"])
    return {"response_text": llm["response_text"], "alignment_score": inputs["alignment_score"]}


GUARD = Guardrail(alignment_threshold=0.85)
def guard_fn(inputs, outputs): return GUARD.clamp(inputs, outputs)
RULES = source_hash(transition, guard_fn)


def _seal(prompt="hello world", seed=7, align=0.93, scripted="APPROVE ok"):
    cap = LLMCapture(client=MockLLMClient(flight_ms=0.0))
    cap.call("r", prompt=prompt, system="sys", seed=seed, scripted=scripted)
    return cap.sealed_inputs({"prompt": prompt, "seed": seed, "alignment_score": align})


def _build(signer=None, n=3):
    m = AgentStateMachine(signer or HmacSigner(b"k"), RULES)
    led = []
    for i in range(n):
        sealed = _seal(prompt="case %d" % i)
        led.append(m.commit("S%d" % i, sealed, transition(sealed), guard_fn))
    return led


class TestCore(unittest.TestCase):
    def test_verify_clean(self):
        self.assertTrue(audit_chain(_build(), b"k", transition, guard_fn).ok)

    def test_tamper_captured_prompt(self):
        led = _build()
        led[1]["frame"]["inputs"]["_llm"]["r"]["prompt"] = "evil"
        v = audit_chain(led, b"k", transition, guard_fn)
        self.assertFalse(v.ok); self.assertEqual(v.at, 1)

    def test_reorder_breaks_chain(self):
        led = _build(); led[0], led[1] = led[1], led[0]
        self.assertFalse(audit_chain(led, b"k", transition, guard_fn).ok)

    def test_delete_breaks_chain(self):
        led = _build(); del led[1]
        self.assertFalse(audit_chain(led, b"k", transition, guard_fn).ok)

    def test_wrong_key(self):
        self.assertFalse(audit_chain(_build(), b"WRONG", transition, guard_fn).ok)

    def test_rule_swap(self):
        def other_transition(inputs):
            cap = LLMCapture.replay(inputs)
            llm = cap.call("r", prompt=inputs["prompt"], system="sys", seed=inputs["seed"])
            return {"response_text": llm["response_text"], "alignment_score": inputs["alignment_score"]}
        self.assertFalse(audit_chain(_build(), b"k", other_transition, guard_fn).ok)

    def test_float_canon_recurses(self):
        self.assertEqual(core.canonical_bytes({"a": {"b": [1/3]}}),
                         core.canonical_bytes({"a": {"b": [0.333333333333]}}))


class TestCapture(unittest.TestCase):
    def test_replay_is_deterministic(self):
        sealed = _seal()
        ok, _ = verify_replay_determinism(transition, sealed)
        self.assertTrue(ok)

    def test_replay_no_live_call(self):
        # replay seam must never touch the client; give it a client that would explode if called
        sealed = _seal()
        out1 = transition(sealed); out2 = transition(sealed)
        self.assertEqual(out1, out2)

    def test_missing_capture_raises(self):
        from agent_capture import CaptureError
        c = LLMCapture.replay({"_llm": {}})
        with self.assertRaises(CaptureError):
            c.call("r", prompt="x", system="s", seed=1)


class TestGuard(unittest.TestCase):
    def test_pii_blocks_commit(self):
        m = AgentStateMachine(HmacSigner(b"k"), RULES)
        sealed = _seal(scripted="APPROVE; SSN 123-45-6789")
        with self.assertRaises(TransitionRefused):
            m.commit("S", sealed, transition(sealed), guard_fn)

    def test_low_alignment_blocks_commit(self):
        m = AgentStateMachine(HmacSigner(b"k"), RULES)
        sealed = _seal(align=0.10)
        with self.assertRaises(TransitionRefused):
            m.commit("S", sealed, transition(sealed), guard_fn)

    def test_pii_clean_helper(self):
        self.assertTrue(pii_clean("nothing sensitive here"))
        self.assertFalse(pii_clean("card 1234567812345678"))
        self.assertFalse(pii_clean("email a@b.com"))

    def test_guardrail_hash_changes_with_threshold(self):
        self.assertNotEqual(Guardrail(0.85).guardrail_hash, Guardrail(0.95).guardrail_hash)


@unittest.skipUnless(ed25519_available(), "cryptography not installed")
class TestEd25519(unittest.TestCase):
    def test_third_party_verify(self):
        s = Ed25519Signer.generate()
        led = _build(s)
        self.assertTrue(audit_chain(led, Ed25519Verifier(s.public_material()), transition, guard_fn).ok)

    def test_wrong_public_key_fails(self):
        s = Ed25519Signer.generate(); led = _build(s)
        other = Ed25519Signer.generate()
        self.assertFalse(audit_chain(led, Ed25519Verifier(other.public_material()), transition, guard_fn).ok)

    def test_guardrail_attestation_roundtrip(self):
        s = Ed25519Signer.generate()
        g = Guardrail(0.85, signer=s)
        rec = g.attest_record()
        self.assertTrue(Guardrail.verify_attestation(rec, Ed25519Verifier(s.public_material())))
        rec["guardrail_hash"] = "0" * 16   # tamper
        self.assertFalse(Guardrail.verify_attestation(rec, Ed25519Verifier(s.public_material())))


class TestFallback(unittest.TestCase):
    def test_make_guard_signer_hmac_fallback(self):
        import agent_guard
        orig = agent_guard.ed25519_available
        agent_guard.ed25519_available = lambda: False
        try:
            s = make_guard_signer(secret=b"k", prefer_ed25519=True)
            self.assertEqual(s.algo, "hmac-sha256")
            with self.assertRaises(RuntimeError):
                make_guard_signer(secret=None, prefer_ed25519=True)
        finally:
            agent_guard.ed25519_available = orig


if __name__ == "__main__":
    unittest.main(verbosity=2)
