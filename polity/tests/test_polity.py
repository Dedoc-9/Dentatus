"""polity/tests/test_polity.py — deterministic ruleset governance: ratify, reject, lineage."""
import os, sys, unittest
_P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WB = os.path.dirname(_P)
sys.path.insert(0, _P)
sys.path.insert(0, os.path.join(_WB, "quorum"))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
import constitution as P
import tally as Q
import core

GOVS = ["g1", "g2", "g3", "g4"]


def rh(tag):
    return core.state_hash({"ruleset": tag})


class Governance(unittest.TestCase):
    def setUp(self):
        self.signers = {g: Q.make_witness(g) for g in GOVS}
        self.reg = P.governor_registry(self.signers)
        self.c0 = P.genesis_constitution(rh("v1"))

    def _ballots(self, prop, yeas):
        out = []
        for g in GOVS:
            out.append(P.cast(g, self.signers[g], prop, "yea" if g in yeas else "nay"))
        return out

    def test_genesis_is_version_zero(self):
        self.assertEqual(self.c0["version"], 0); self.assertEqual(self.c0["prev"], P.GENESIS)

    def test_ratify_passes_at_quorum(self):
        prop = P.propose(self.c0, rh("v2"), "g1")
        res = P.ratify(self.c0, prop, self._ballots(prop, {"g1", "g2", "g3"}), k=3, registry=self.reg)
        self.assertTrue(res["ratified"]); self.assertEqual(res["constitution"]["version"], 1)
        self.assertEqual(res["constitution"]["ruleset_hash"], rh("v2"))

    def test_reject_below_quorum(self):
        prop = P.propose(self.c0, rh("v2"), "g1")
        res = P.ratify(self.c0, prop, self._ballots(prop, {"g1", "g2"}), k=3, registry=self.reg)
        self.assertFalse(res["ratified"])

    def test_nay_does_not_count_as_yea(self):
        # all four authenticate, but only 2 say yea -> below k=3
        prop = P.propose(self.c0, rh("v2"), "g1")
        res = P.ratify(self.c0, prop, self._ballots(prop, {"g1", "g4"}), k=3, registry=self.reg)
        self.assertFalse(res["ratified"]); self.assertEqual(res["certificate"]["n"], 4)

    def test_outsider_ballot_rejected(self):
        prop = P.propose(self.c0, rh("v2"), "g1")
        intruder = Q.make_witness("evil")
        ballots = self._ballots(prop, {"g1", "g2"}) + [P.cast("g_evil", intruder, prop, "yea")]
        res = P.ratify(self.c0, prop, ballots, k=3, registry=self.reg)
        self.assertFalse(res["ratified"])                      # the forged yea is not counted

    def test_lineage_verifies(self):
        prop = P.propose(self.c0, rh("v2"), "g1")
        c1 = P.ratify(self.c0, prop, self._ballots(prop, {"g1", "g2", "g3"}), 3, self.reg)["constitution"]
        self.assertEqual(P.verify_lineage([self.c0, c1]), (True, None))
        self.assertEqual(P.active_ruleset([self.c0, c1]), rh("v2"))

    def test_tampered_constitution_caught(self):
        prop = P.propose(self.c0, rh("v2"), "g1")
        c1 = P.ratify(self.c0, prop, self._ballots(prop, {"g1", "g2", "g3"}), 3, self.reg)["constitution"]
        ok, fault = P.verify_lineage([self.c0, dict(c1, ruleset_hash=rh("evil"))])
        self.assertFalse(ok); self.assertIn("tampered", fault["reason"])

    def test_broken_lineage_located(self):
        prop = P.propose(self.c0, rh("v2"), "g1")
        c1 = P.ratify(self.c0, prop, self._ballots(prop, {"g1", "g2", "g3"}), 3, self.reg)["constitution"]
        forged = dict(c1, prev="0" * 64)
        forged["constitution_hash"] = core.state_hash({k: forged[k] for k in forged if k != "constitution_hash"})
        ok, fault = P.verify_lineage([self.c0, forged])
        self.assertFalse(ok); self.assertIn("lineage broken", fault["reason"])


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("set PYTHONHASHSEED=0\n"); raise SystemExit(2)
    unittest.main(verbosity=2)
