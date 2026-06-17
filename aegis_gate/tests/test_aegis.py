"""
aegis_gate/tests/test_aegis.py — unit tests for the verifiable transfer app. Stdlib unittest only.

Run:  PYTHONHASHSEED=0 python3 tests/test_aegis.py
"""
import os, sys, json, copy, unittest

def _load(path):
    with open(path) as fh:
        return [json.loads(l) for l in fh if l.strip()]

_HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(_HERE)
sys.path.insert(0, APP)

from _workbench import verify_chain, Capture, ruleset_hash, Recorder, HmacSigner, InvariantViolation
from app import bank_engine as be
from app import policy
from app import agent
import run_pipeline as R


def _bank():
    return {"A": {"balance_cents": 1_000_000, "verified": True, "routing": "US100"},
            "B": {"balance_cents": 0, "verified": True, "routing": "US200"},
            "R": {"balance_cents": 0, "verified": True, "routing": "DE777"}}


class BankEngine(unittest.TestCase):
    def test_transfer_is_pure_and_conserves(self):
        pre = _bank(); post = be.apply_transfer(pre, "A", "B", 250000)
        self.assertEqual(pre["A"]["balance_cents"], 1_000_000)            # input untouched
        self.assertEqual(post["A"]["balance_cents"], 750000)
        self.assertEqual(post["B"]["balance_cents"], 250000)
        self.assertEqual(be.total_cents(pre), be.total_cents(post))       # conservation

    def test_overdraft_refused(self):
        with self.assertRaises(InvariantViolation):
            be.apply_transfer(_bank(), "A", "B", 1_000_001)

    def test_float_amount_refused(self):
        with self.assertRaises(InvariantViolation):
            be.apply_transfer(_bank(), "A", "B", 100.5)

    def test_world_hash_changes_on_one_cent(self):
        pre = _bank(); p1 = be.apply_transfer(pre, "A", "B", 100); p2 = be.apply_transfer(pre, "A", "B", 101)
        self.assertNotEqual(be.world_hash(p1), be.world_hash(p2))


def _inputs(amount, src, dst, accounts, verified, restricted, supervisor):
    return {"amount_cents": amount, "src": src, "dst": dst, "src_verified": verified,
            "dst_restricted": restricted, "supervisor_authorized": supervisor,
            "accounts_pre": accounts, "_captured": {}}


class PolicyGates(unittest.TestCase):
    def test_unverified_over_ceiling_denied(self):
        acc = _bank(); acc["A"]["verified"] = False
        o = policy.decide(_inputs(policy.UNVERIFIED_SINGLE_CEILING_CENTS, "A", "B", acc, False, False, False))
        self.assertFalse(o["approved"])

    def test_restricted_needs_supervisor(self):
        acc = _bank()
        denied = policy.decide(_inputs(50000, "A", "R", acc, True, True, False))
        appr = policy.decide(_inputs(50000, "A", "R", acc, True, True, True))
        self.assertFalse(denied["approved"]); self.assertTrue(appr["approved"])

    def test_denied_leaves_state_unchanged(self):
        acc = _bank()
        o = policy.decide(_inputs(50000, "A", "R", acc, True, True, False))
        self.assertEqual(be.world_hash(o["accounts_post"]), be.world_hash(acc))

    def test_invariant_rejects_lie(self):
        # approved=True on an unverified over-ceiling transfer must fail the invariant
        acc = _bank(); acc["A"]["verified"] = False; acc["A"]["balance_cents"] = 5_000_000
        inp = _inputs(2_000_000, "A", "B", acc, False, False, False)
        forged = be.apply_transfer(acc, "A", "B", 2_000_000)
        out = {"approved": True, "reasons": [], "accounts_post": forged, "world_H": be.world_hash(forged)}
        self.assertFalse(policy.aml_invariant(inp, out))


class ObservableSplit(unittest.TestCase):
    def test_logprobs_do_not_change_decision(self):
        acc = _bank()
        base = _inputs(50000, "A", "B", acc, True, False, False)
        a = dict(base, _captured={"token_logprobs": [-0.1, -0.2], "parse_confidence": 0.9})
        b = dict(base, _captured={"token_logprobs": [-9.9, -9.9], "parse_confidence": 0.01})
        self.assertEqual(policy.decide(a)["approved"], policy.decide(b)["approved"])
        self.assertEqual(policy.decide(a)["world_H"], policy.decide(b)["world_H"])


class ReplayCourt(unittest.TestCase):
    def test_pipeline_ledger_verifies(self):
        summary, _ = R.run(verbose=False)
        ledger = _load(R.LEDGER_PATH)
        v = verify_chain(ledger, R.INSTITUTION_SECRET, policy.decide, policy.aml_invariant)
        self.assertTrue(v.ok, v.reason)
        self.assertEqual(len(ledger), 4)

    def test_tamper_is_caught(self):
        R.run(verbose=False)
        ledger = _load(R.LEDGER_PATH)
        bad = copy.deepcopy(ledger); bad[0]["frame"]["inputs"]["amount_cents"] += 1
        v = verify_chain(bad, R.INSTITUTION_SECRET, policy.decide, policy.aml_invariant)
        self.assertFalse(v.ok); self.assertEqual(v.at, 0)

    def test_failclosed_refuses_unsafe_write(self):
        ok, _ = R.demonstrate_failclosed()
        self.assertTrue(ok)

    def test_expected_verdicts(self):
        summary, final = R.run(verbose=False)
        verdicts = {label: verdict for label, verdict, _ in summary}
        self.assertEqual(verdicts["legit_supplier"], "APPROVED")
        self.assertEqual(verdicts["legit_landlord"], "APPROVED")
        self.assertEqual(verdicts["over_ceiling"], "DENIED")
        self.assertEqual(verdicts["injection_drain"], "DENIED")
        # the offshore drain never moved money
        self.assertEqual(final["Z_OFFSHORE"]["balance_cents"], 0)


class SupervisorToken(unittest.TestCase):
    def test_token_bound_to_transfer(self):
        s = R._supervisor_signer(); v = R._supervisor_verifier(s)
        tok = R.mint_supervisor_token(s, "A", "R", 50000)
        self.assertTrue(R.verify_supervisor_token(v, tok, "A", "R", 50000))
        self.assertFalse(R.verify_supervisor_token(v, tok, "A", "R", 50001))   # cannot replay onto other amount
        self.assertFalse(R.verify_supervisor_token(v, None, "A", "R", 50000))  # missing -> fail-closed


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("set PYTHONHASHSEED=0 to run these tests (replay determinism)\n")
        raise SystemExit(2)
    unittest.main(verbosity=2)
