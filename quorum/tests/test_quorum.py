"""quorum/tests/test_quorum.py — unit tests for integer consensus + the 2D lattice. Stdlib unittest."""
import os, sys, unittest
_Q = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _Q)
import tally as Q
import lattice as L

WS = ["w1", "w2", "w3", "w4"]


def setup():
    signers = {w: Q.make_witness(w) for w in WS}
    return signers, Q.build_registry(signers)


def votes(signers, rid, states):
    return [Q.witness_vote(w, rid, s, signers[w]) for w, s in states.items()]


class Tally(unittest.TestCase):
    def setUp(self):
        self.s, self.reg = setup()

    def test_unanimous_certifies(self):
        c = Q.tally(votes(self.s, 0, {w: {"x": 1} for w in WS}), 3, self.reg, 0)
        self.assertTrue(c["certified"]); self.assertEqual(c["agreed"], 4)
        self.assertEqual(c["observables"]["agreement_ratio"], 1.0)
        self.assertEqual(c["observables"]["ess_opinions"], 1.0)         # one opinion-bloc

    def test_ess_is_n_on_total_fork(self):
        c = Q.tally(votes(self.s, 0, {"w1": {"x": 1}, "w2": {"x": 2}, "w3": {"x": 3}, "w4": {"x": 4}}), 3, self.reg, 0)
        self.assertEqual(c["observables"]["ess_opinions"], 4.0)         # n distinct opinions
        self.assertFalse(c["certified"])

    def test_honest_dissent_certifies_and_ghost_named(self):
        c = Q.tally(votes(self.s, 1, {"w1": {"x": 1}, "w2": {"x": 1}, "w3": {"x": 1}, "w4": {"x": 9}}), 3, self.reg, 1)
        self.assertTrue(c["certified"]); self.assertEqual(list(c["ghost"]), ["w4"])

    def test_threshold_is_a_cut(self):
        v = votes(self.s, 1, {"w1": {"x": 1}, "w2": {"x": 1}, "w3": {"x": 1}, "w4": {"x": 9}})
        self.assertTrue(Q.tally(v, 3, self.reg, 1)["certified"])
        self.assertFalse(Q.tally(v, 4, self.reg, 1)["certified"])       # same votes, raised k -> no quorum

    def test_equivocation_excluded(self):
        v = votes(self.s, 2, {"w1": {"x": 1}, "w3": {"x": 1}, "w4": {"x": 1}})
        v += [Q.witness_vote("w2", 2, {"x": 1}, self.s["w2"]), Q.witness_vote("w2", 2, {"x": 5}, self.s["w2"])]
        c = Q.tally(v, 3, self.reg, 2)
        self.assertEqual(c["equivocators"], ["w2"]); self.assertNotIn("w2", c["ghost"]); self.assertEqual(c["n"], 3)

    def test_intruder_rejected(self):
        intr = Q.make_witness("evil")
        v = votes(self.s, 3, {"w1": {"x": 1}, "w2": {"x": 1}, "w3": {"x": 1}})
        v.append(Q.witness_vote("w_evil", 3, {"x": 1}, intr))
        c = Q.tally(v, 3, self.reg, 3)
        self.assertEqual([r["witness"] for r in c["rejected"]], ["w_evil"]); self.assertEqual(c["n"], 3)

    def test_tampered_vote_rejected(self):
        v = votes(self.s, 4, {"w1": {"x": 1}, "w2": {"x": 1}, "w3": {"x": 1}})
        v[0]["state_hash"] = "0" * 64                                   # flip the signed hash
        c = Q.tally(v, 3, self.reg, 4)
        self.assertIn("w1", [r["witness"] for r in c["rejected"]])

    def test_cert_hash_changes_with_votes(self):
        a = Q.tally(votes(self.s, 0, {w: {"x": 1} for w in WS}), 3, self.reg, 0)
        b = Q.tally(votes(self.s, 0, {w: {"x": 2} for w in WS}), 3, self.reg, 0)
        self.assertNotEqual(a["cert_hash"], b["cert_hash"])

    def test_k_must_be_positive(self):
        with self.assertRaises(Q.QuorumError):
            Q.tally(votes(self.s, 0, {w: {"x": 1} for w in WS}), 0, self.reg, 0)


def monotonic(prev, new):
    return new["round"] > prev["round"]


class Lattice(unittest.TestCase):
    def setUp(self):
        self.s, self.reg = setup()
        self.notary = Q.make_witness("notary")
        self.preg = {"notary": Q.verifier_for(self.notary)}

    def rnd(self, rid, states):
        return (rid, votes(self.s, rid, states))

    def test_happy_lattice_binds(self):
        rounds = [self.rnd(0, {w: {"a": 10} for w in WS}), self.rnd(1, {w: {"a": 15} for w in WS}),
                  self.rnd(2, {w: {"a": 22} for w in WS})]
        r = L.evaluate(rounds, 3, self.reg, "notary", self.notary, self.preg, monotonic)
        self.assertTrue(r["ok"]); self.assertIsNotNone(r["lattice_hash"]); self.assertEqual(len(r["spine"]), 3)

    def test_lateral_fault_localized(self):
        rounds = [self.rnd(0, {w: {"a": 10} for w in WS}),
                  ("1", votes(self.s, "1", {"w1": {"a": 1}, "w2": {"a": 1}, "w3": {"a": 2}, "w4": {"a": 2}}))]
        r = L.evaluate(rounds, 3, self.reg, "notary", self.notary, self.preg, monotonic)
        self.assertFalse(r["ok"]); self.assertEqual(r["fault"]["axis"], "lateral"); self.assertEqual(r["fault"]["round"], "1")

    def test_temporal_fault_localized(self):
        rounds = [self.rnd(2, {w: {"a": 10} for w in WS}), self.rnd(1, {w: {"a": 15} for w in WS})]
        r = L.evaluate(rounds, 3, self.reg, "notary", self.notary, self.preg, monotonic)
        self.assertFalse(r["ok"]); self.assertEqual(r["fault"]["axis"], "temporal")

    def test_uncertified_round_cannot_bind(self):
        rounds = [self.rnd(0, {w: {"a": 10} for w in WS}),
                  ("1", votes(self.s, "1", {"w1": {"a": 1}, "w2": {"a": 2}, "w3": {"a": 3}, "w4": {"a": 4}}))]
        r = L.evaluate(rounds, 3, self.reg, "notary", self.notary, self.preg, monotonic)
        self.assertFalse(r["ok"]); self.assertEqual(r["fault"]["axis"], "lateral")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("set PYTHONHASHSEED=0\n"); raise SystemExit(2)
    unittest.main(verbosity=2)
