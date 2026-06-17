"""Stdlib unittest suite — the four core guarantees plus the three hardening features."""
import sys, os, copy, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core
from court import verify_chain
from signing import HmacSigner, Ed25519Signer, Ed25519Verifier, ed25519_available, make_signer
from capture import Capture, verify_determinism, CaptureError
from store import MemoryStore, JsonlStore


def logic(inp):     return {"y": round(inp["a"] / inp["b"], 4)}
def inv(inp, out):  return out["y"] < 100.0
RH = core.ruleset_hash(logic, inv)
ROWS = [("R1", {"a": 1, "b": 2}), ("R2", {"a": 3, "b": 4}), ("R3", {"a": 5, "b": 8})]


def cap_logic(inp):
    c = Capture.replay(inp)
    t = c.clock("ts", lambda: 0); r = c.external("ext", lambda: 0)
    return {"sum": inp["a"] + t + r}


def cap_inv(inp, out):
    return True


def cap_sealed():
    cap = Capture(); cap.clock("ts", lambda: 100); cap.external("ext", lambda: 7)
    return cap.sealed_inputs({"a": 1})


def build(signer=None):
    rec = core.Recorder(signer or HmacSigner(b"k"), RH)
    return [rec.record(d, i, logic(i), inv) for d, i in ROWS]


class TestCore(unittest.TestCase):
    def test_verify_clean(self):
        self.assertTrue(verify_chain(build(), b"k", logic, inv).ok)

    def test_tamper_output(self):
        led = build(); led[1]["frame"]["outputs"]["y"] = 999.0
        v = verify_chain(led, b"k", logic, inv)
        self.assertFalse(v.ok); self.assertEqual(v.at, 1)

    def test_reorder_breaks_chain(self):
        led = build(); led[0], led[1] = led[1], led[0]
        self.assertFalse(verify_chain(led, b"k", logic, inv).ok)

    def test_delete_breaks_chain(self):
        led = build(); del led[1]
        self.assertFalse(verify_chain(led, b"k", logic, inv).ok)

    def test_rule_swap_caught(self):
        def loose(inp): return {"y": round(inp["a"] / inp["b"], 4)}  # different source text
        self.assertFalse(verify_chain(build(), b"k", loose, inv).ok)

    def test_wrong_key_caught(self):
        self.assertFalse(verify_chain(build(), b"WRONG", logic, inv).ok)

    def test_invariant_refused_at_record(self):
        rec = core.Recorder(b"k", RH)
        with self.assertRaises(core.InvariantViolation):
            rec.record("BAD", {"a": 1000, "b": 1}, {"y": 1000.0}, inv)

    def test_float_canon_recurses(self):
        a = core.canonical_bytes({"x": {"y": [1.0/3.0]}})
        b = core.canonical_bytes({"x": {"y": [0.333333333333]}})
        self.assertEqual(a, b)


@unittest.skipUnless(ed25519_available(), "cryptography not installed")
class TestEd25519(unittest.TestCase):
    def test_public_key_verifies(self):
        s = Ed25519Signer.generate()
        led = build(s)
        self.assertTrue(verify_chain(led, Ed25519Verifier(s.public_material()), logic, inv).ok)

    def test_wrong_public_key_fails(self):
        s = Ed25519Signer.generate(); led = build(s)
        other = Ed25519Signer.generate()
        self.assertFalse(verify_chain(led, Ed25519Verifier(other.public_material()), logic, inv).ok)

    def test_verifier_cannot_sign(self):
        s = Ed25519Signer.generate()
        v = Ed25519Verifier(s.public_material())
        self.assertFalse(hasattr(v, "sign") and callable(getattr(v, "_sk", None)))

    def test_key_roundtrip(self):
        s = Ed25519Signer.generate(); hexk = s.private_key_hex()
        s2 = Ed25519Signer(hexk)
        self.assertEqual(s.public_material(), s2.public_material())

    def test_factory(self):
        s = make_signer({"algo": "ed25519"})
        self.assertEqual(s.algo, "ed25519")


class TestCapture(unittest.TestCase):
    def test_capture_replays_exactly(self):
        sealed = cap_sealed()
        out = cap_logic(sealed)
        self.assertEqual(out["sum"], 108)
        ok, _ = verify_determinism(cap_logic, sealed)
        self.assertTrue(ok)
        # full chain round-trips; recorder and court hash the SAME (logic, invariant) pair
        rh = core.ruleset_hash(cap_logic, cap_inv)
        rec = core.Recorder(b"k", rh)
        led = [rec.record("C", sealed, out, cap_inv)]
        self.assertTrue(verify_chain(led, b"k", cap_logic, cap_inv).ok)

    def test_leak_detected(self):
        import random
        def leaky(inp): return {"r": random.random()}
        ok, detail = verify_determinism(leaky, {"a": 1})
        self.assertFalse(ok)

    def test_missing_capture_on_replay(self):
        c = Capture.replay({"_captured": {}})
        with self.assertRaises(CaptureError):
            c.clock("ts", lambda: 0)


class TestStore(unittest.TestCase):
    def test_memory_store_roundtrip(self):
        st = MemoryStore()
        rec = core.Recorder(b"k", RH, store=st)
        for d, i in ROWS: rec.record(d, i, logic(i), inv)
        self.assertEqual(st.seq(), 3)
        self.assertTrue(verify_chain(list(st), b"k", logic, inv).ok)

    def test_jsonl_persist_and_resume(self):
        import tempfile
        p = tempfile.mktemp(suffix=".jsonl")
        st = JsonlStore(p)
        rec = core.Recorder(b"k", RH, store=st)
        rec.record(*ROWS[0][:1], ROWS[0][1], logic(ROWS[0][1]), inv) if False else \
            rec.record("R1", ROWS[0][1], logic(ROWS[0][1]), inv)
        # resume: new recorder reads head/seq from the store
        st2 = JsonlStore(p)
        rec2 = core.Recorder(b"k", RH, store=st2)
        self.assertEqual(rec2.seq, 1)
        rec2.record("R2", ROWS[1][1], logic(ROWS[1][1]), inv)
        self.assertTrue(verify_chain(list(JsonlStore(p)), b"k", logic, inv).ok)
        os.remove(p)



class TestFallback(unittest.TestCase):
    def test_ed25519_missing_falls_back_to_hmac(self):
        import signing
        orig = signing.ed25519_available
        signing.ed25519_available = lambda: False
        try:
            s = signing.make_signer({"algo": "ed25519", "secret": b"k"})
            self.assertEqual(s.algo, "hmac-sha256")
            with self.assertRaises(RuntimeError):
                signing.make_signer({"algo": "ed25519"})            # no secret -> fail closed, clean error
            with self.assertRaises(RuntimeError):
                signing.make_signer({"algo": "ed25519", "secret": b"k"}, allow_fallback=False)
        finally:
            signing.ed25519_available = orig

if __name__ == "__main__":
    unittest.main(verbosity=2)
