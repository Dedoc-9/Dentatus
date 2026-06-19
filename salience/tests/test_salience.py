"""
salience/tests/test_salience.py — the possibility-aware allocation field.

Exact-integer apportionment (sums to budget), monotone in density (doorway > valley), floors honored,
deterministic + key-ordered ties, graceful on zero/degenerate weights. The LAW (possibility → allocation,
never possibility → physics) is architectural: this module only emits a compute budget; it has no path to
any kernel/state.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import field as SAL
import predictor as PR
import atlas as ATL
import bench as BN
import ccr as CCR


class TestAllocate(unittest.TestCase):
    def test_sums_exactly_to_budget(self):
        for B in (0, 1, 7, 100, 1000, 99991):
            a = SAL.allocate({"a": 2, "b": 40, "c": 300, "d": 120}, B, floor=0)
            self.assertEqual(sum(a.values()), B)

    def test_monotone_doorway_beats_valley(self):
        a = SAL.allocate(SAL.density({"valley": 2, "doorway": 300}), 1000)
        self.assertGreater(a["doorway"], a["valley"])

    def test_floor_respected(self):
        a = SAL.allocate({"x": 1000, "y": 1, "z": 1}, 100, floor=10)
        self.assertGreaterEqual(a["y"], 10)
        self.assertGreaterEqual(a["z"], 10)
        self.assertEqual(sum(a.values()), 100)

    def test_floors_exceeding_budget_fall_back(self):
        a = SAL.allocate({"x": 3, "y": 1}, 4, floor=10)     # 2*10 > 4 → drop floors, apportion by weight
        self.assertEqual(sum(a.values()), 4)
        self.assertGreater(a["x"], a["y"])

    def test_zero_weights_even(self):
        a = SAL.allocate({"a": 0, "b": 0, "c": 0}, 9)
        self.assertEqual(sum(a.values()), 9)
        self.assertLessEqual(max(a.values()) - min(a.values()), 1)   # as even as integers allow

    def test_deterministic_and_tie_ordered(self):
        w = {"b": 5, "a": 5, "c": 5}
        a1 = SAL.allocate(w, 10); a2 = SAL.allocate(w, 10)
        self.assertEqual(a1, a2)
        # leftover after 3·3=9 is 1; equal remainders → goes to the first key ('a')
        self.assertEqual(a1["a"], 4)

    def test_empty(self):
        self.assertEqual(SAL.allocate({}, 100), {})

    def test_concentration(self):
        peaked = SAL.allocate(SAL.density({"v": 1, "door": 999}), 1000)
        spread = SAL.allocate(SAL.density({"a": 1, "b": 1, "c": 1}), 1000)
        self.assertGreater(SAL.concentration(peaked), SAL.concentration(spread))




class TestPredictorAtlas(unittest.TestCase):
    def test_calibrate_predict_ranks_correctly(self):
        rows = [[3, 6, 3, 2], [1, 2, 0, 120], [4, 6, 4, 1], [1, 2, 0, 80]]   # doorways high, valleys low
        truth = [90.0, 1.0, 110.0, 2.0]
        w = PR.calibrate(rows, truth)
        self.assertGreater(PR.predict(w, rows[2]), PR.predict(w, rows[1]))    # doorway > valley
        self.assertGreater(PR.predict(w, rows[0]), PR.predict(w, rows[3]))

    def test_atlas_sample_and_budgeted_refresh(self):
        a = ATL.PossibilityAtlas().build(["r0", "r1", "r2"], lambda r: {"r0": 5., "r1": 9., "r2": 1.}[r])
        self.assertEqual(a.sample("r1"), 9.)
        a.tick(); a.tick()
        done = a.refresh(["r0", "r1", "r2"], lambda r: 0., budget=2)         # only 2 refreshed (budget)
        self.assertEqual(len(done), 2)


class TestFalsificationMetrics(unittest.TestCase):
    def test_spearman_and_topk(self):
        self.assertAlmostEqual(BN.spearman([1, 2, 3, 4], [1, 2, 3, 4]), 1.0)
        self.assertAlmostEqual(BN.spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
        self.assertEqual(BN.top_k_overlap([9, 1, 8, 2], [9, 1, 8, 2], 2), 1.0)   # same top-2

    def test_impactful_quality(self):
        truth = [10, 0, 0, 0]
        on_truth = BN.impactful_captured([1, 0, 0, 0], truth)
        off_truth = BN.impactful_captured([0, 1, 1, 1], truth)
        self.assertGreater(on_truth, off_truth)               # compute on possibility scores higher

    def test_freshness_cheap_beats_expensive(self):
        cheap = BN.frames_to_refresh_all(0.5, 30, 50.0)
        true = BN.frames_to_refresh_all(600.0, 30, 50.0)
        self.assertEqual(cheap, 1)
        self.assertGreater(true, cheap)

    def test_verdict_cheap_wins_when_high_quality_and_cheap(self):
        # cheap matches true quality, beats distance, costs <10% of true, stays fresh
        true = [9, 1, 8, 2, 0]; cheap = [8, 1, 9, 2, 0]; dist = [1, 1, 1, 1, 1]
        rep = BN.evaluate(true, cheap, dist, {"distance": 0.1, "cheap": 0.5, "true": 600.0}, 5, 50.0)
        self.assertEqual(rep["verdict"], "cheap-wins")

    def test_verdict_inconclusive_when_cheap_is_expensive(self):
        true = [9, 1, 8, 2, 0]; cheap = [8, 1, 9, 2, 0]; dist = [1, 1, 1, 1, 1]
        rep = BN.evaluate(true, cheap, dist, {"distance": 0.1, "cheap": 100.0, "true": 600.0}, 5, 50.0)
        self.assertEqual(rep["verdict"], "inconclusive")      # cheap not cheap enough → no win




class TestConsequenceCapture(unittest.TestCase):
    """CCR pure metrics: does a signal's top-budget capture the truly-consequential regions?"""
    def test_ccr_perfect_vs_anti(self):
        cons = [10, 8, 1, 1, 0]
        perfect = [10, 8, 1, 1, 0]      # ranks exactly by consequence
        anti = [0, 1, 1, 8, 10]         # reversed
        self.assertGreater(CCR.ccr(perfect, cons, 0.4), CCR.ccr(anti, cons, 0.4))
        self.assertAlmostEqual(CCR.ccr(perfect, cons, 0.4), (10 + 8) / 20)

    def test_spearman(self):
        self.assertAlmostEqual(CCR.spearman([1, 2, 3], [1, 2, 3]), 1.0)
        self.assertAlmostEqual(CCR.spearman([1, 2, 3], [3, 2, 1]), -1.0)

    def test_verdict_possibility_wins(self):
        cons = [9, 8, 1, 1, 0]
        sig = {"distance": [0, 0, 1, 1, 9], "visibility": [0, 1, 1, 1, 9],
               "importance": [9, 8, 1, 1, 0], "possibility": [9, 7, 1, 2, 0]}
        rep = CCR.compare(sig, cons)
        self.assertEqual(rep["verdict"], "possibility-wins-attention")

    def test_verdict_inconclusive_when_proximity_wins(self):
        cons = [9, 8, 1, 1, 0]
        sig = {"distance": [9, 8, 1, 1, 0], "visibility": [9, 8, 1, 1, 0],
               "importance": [9, 8, 1, 1, 0], "possibility": [0, 0, 1, 1, 9]}
        rep = CCR.compare(sig, cons)
        self.assertEqual(rep["verdict"], "inconclusive")


if __name__ == "__main__":
    unittest.main(verbosity=2)
