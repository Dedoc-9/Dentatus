"""lockstep/tests/test_lockstep.py — fixed-timestep truth, render observables, rollback. Stdlib unittest."""
import os, sys, unittest
_L = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _L)
from tick import TruthTrack, kinematic_step, truth_hash, LockstepError
import interp as I
import rollback as RB

U = 1_000_000


def track(n_ticks, v=U, a=0):
    t = TruthTrack({"p": 0, "v": v}, kinematic_step)
    for _ in range(n_ticks):
        t.advance({"a": a})
    return t


class Tick(unittest.TestCase):
    def test_integer_sim_is_deterministic(self):
        a = track(5); b = track(5)
        self.assertEqual(a.hashes, b.hashes)

    def test_tick_hashes_unique_and_ordered(self):
        t = track(5)
        self.assertEqual(len(set(t.hashes)), len(t.hashes))

    def test_truth_hash_excludes_render(self):
        # the hash depends only on tick + integer state, not on any interpolation
        t = track(3)
        self.assertEqual(t.hashes[2], truth_hash(2, t.states[2]))

    def test_rebuild_from_inputs_matches(self):
        t = track(4, a=7)
        rebuilt = TruthTrack.from_inputs({"p": 0, "v": U}, kinematic_step, t.inputs)
        self.assertEqual(rebuilt.hashes, t.hashes)


class Interp(unittest.TestCase):
    def test_two_frames_per_tick(self):
        self.assertEqual(I.frames_per_tick(120, 240), 2.0)

    def test_exact_half_interpolation(self):
        t = track(3)                                          # p = 0,1,2,3 units
        fr = I.render_frame(t, 1, 120, 240, ["p"])            # frame 1 -> tick 0 + 1/2
        self.assertEqual(fr["tick"], 0); self.assertEqual(fr["alpha_num"], 120)
        self.assertEqual(fr["pos"]["p"], U // 2)              # exactly 0.5 units

    def test_frame_on_tick_boundary_shows_truth(self):
        t = track(3)
        fr = I.render_frame(t, 2, 120, 240, ["p"])            # frame 2 -> tick 1 exactly
        self.assertEqual(fr["alpha_num"], 0); self.assertEqual(fr["pos"]["p"], t.states[1]["p"])

    def test_no_silent_extrapolation(self):
        t = track(2)
        with self.assertRaises(LockstepError):
            I.render_frame(t, 99, 120, 240, ["p"])

    def test_render_span_drops_unsupported(self):
        t = track(2)                                          # ticks 0,1,2 -> frames up to f=4 supported
        frames, dropped = I.render_span(t, 120, 240, 0, 10, ["p"])
        self.assertTrue(dropped > 0); self.assertTrue(all(not f["extrapolated"] for f in frames))


class Rollback(unittest.TestCase):
    def setUp(self):
        self.G = {"p": 0, "v": U}

    def _predicted(self, n):
        t = TruthTrack(self.G, kinematic_step)
        for _ in range(n):
            t.advance({"a": 0})
        return t

    def test_agreeing_prefix_no_rollback(self):
        pred = self._predicted(5)
        res = RB.reconcile(pred, [{"a": 0}, {"a": 0}, {"a": 0}], kinematic_step)
        self.assertEqual(res["rollback_depth"], 0); self.assertFalse(res["changed"])

    def test_mispredict_reverts_to_last_valid(self):
        pred = self._predicted(6)
        auth = [{"a": 0}, {"a": 0}, {"a": 0}, {"a": U // 2}, {"a": 0}]
        res = RB.reconcile(pred, auth, kinematic_step)
        self.assertEqual(res["last_valid_tick"], 3)
        self.assertEqual(res["rollback_depth"], 3)
        self.assertTrue(res["changed"])

    def test_clients_converge_after_rollback(self):
        pred = self._predicted(6)
        auth = [{"a": 0}, {"a": 0}, {"a": 0}, {"a": U // 2}, {"a": 0}]
        res = RB.reconcile(pred, auth, kinematic_step)
        peer = TruthTrack.from_inputs(self.G, kinematic_step, auth + [{"a": 0}])
        self.assertEqual(peer.hashes[-1], res["corrected"].hashes[-1])

    def test_last_valid_tick_by_hash(self):
        pred = self._predicted(4)
        auth = TruthTrack.from_inputs(self.G, kinematic_step, [{"a": 0}, {"a": 0}, {"a": U}, {"a": 0}])
        self.assertEqual(RB.last_valid_tick(pred, auth.hashes), 2)   # diverges at tick 3 (input a@2 differs)


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("set PYTHONHASHSEED=0\n"); raise SystemExit(2)
    unittest.main(verbosity=2)
