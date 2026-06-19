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


if __name__ == "__main__":
    unittest.main(verbosity=2)
