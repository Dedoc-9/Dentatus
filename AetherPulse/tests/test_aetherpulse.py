# SPDX-License-Identifier: AGPL-3.0-only
"""AetherPulse/tests/test_aetherpulse.py — deterministic 3D fixed-point kernel + conformance vectors."""
import os, sys, unittest
_A = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _A)
sys.path.insert(0, os.path.join(os.path.dirname(_A), "chronicle"))
import kernel as K
import conformance as C
from _cores import SCALE


def two_cubes():
    A = K.body(1, [-5, 5, 0], [4, 0, 0], [1, 1, 1])
    B = K.body(2, [5, 5, 0], [-4, 0, 0], [1, 1, 1])
    return K.make_world([A, B], bounds=((-10, 0, -10), (10, 10, 10)), gravity=0, dt_ms=16)


class Kernel(unittest.TestCase):
    def test_no_float_coords(self):
        with self.assertRaises(TypeError):
            K.body(1, [0.5, 0, 0], [0, 0, 0], [1, 1, 1])

    def test_deterministic_reruns(self):
        self.assertEqual(K.run(two_cubes(), 150)[1], K.run(two_cubes(), 150)[1])

    def test_source_bodies_not_mutated(self):
        A = K.body(1, [-5, 5, 0], [4, 0, 0], [1, 1, 1])
        before = list(A["vel"])
        w = K.make_world([A], bounds=((-10, 0, -10), (10, 10, 10)), gravity=10)
        K.run(w, 50)
        self.assertEqual(A["vel"], before)                  # the determinism-leak regression guard

    def test_cubes_collide(self):
        w = two_cubes(); hit = None
        for t in range(1, 200):
            pv = [b["vel"][0] for b in sorted(w["bodies"], key=lambda b: b["id"])]
            w = K.step(w)
            if hit is None and [b["vel"][0] for b in sorted(w["bodies"], key=lambda b: b["id"])] != pv:
                hit = t
        self.assertIsNotNone(hit)

    def test_gravity_rests_on_floor(self):
        D = K.body(7, [0, 9, 0], [0, 0, 0], [1, 1, 1])
        w = K.make_world([D], bounds=((-10, 0, -10), (10, 10, 10)), gravity=10, dt_ms=16)
        for _ in range(200):
            w = K.step(w)
        y = sorted(w["bodies"], key=lambda b: b["id"])[0]["pos"][1] / SCALE
        self.assertGreaterEqual(y, 0.5)                      # never falls through the floor (floor+half=1)

    def test_rational_coords(self):
        b = K.body(1, [(1, 2), 0, 0], [0, 0, 0], [(2, 5), (2, 5), (2, 5)])
        self.assertEqual(b["pos"][0], SCALE // 2)


class Conformance(unittest.TestCase):
    def test_vector_verifies(self):
        self.assertTrue(C.verify_vector(C.make_vector(two_cubes(), 100))[0])

    def test_divergent_final_fails(self):
        self.assertFalse(C.verify_vector(dict(C.make_vector(two_cubes(), 100), final_hash="0" * 64))[0])

    def test_divergent_merkle_fails(self):
        self.assertFalse(C.verify_vector(dict(C.make_vector(two_cubes(), 100), merkle_root="0" * 64))[0])

    def test_tampered_init_fails(self):
        vec = C.make_vector(two_cubes(), 100)
        vec = dict(vec, init_hash="0" * 64)
        self.assertFalse(C.verify_vector(vec)[0])

    def test_exported_fixtures_conform(self):
        import export_vectors as X
        for name, ok, detail, _ in X.export():
            self.assertTrue(ok, "%s: %s" % (name, detail))

    def test_stress_deterministic(self):
        bodies = [K.body(i, [(i % 10) - 5, 5, 0], [(i % 3) - 1, 0, 0], [1, 1, 1]) for i in range(50)]
        mk = lambda: K.make_world(bodies, bounds=((-20, 0, -20), (20, 20, 20)), gravity=10)
        self.assertEqual(K.run(mk(), 30)[1][-1], K.run(mk(), 30)[1][-1])


class SeamL1L2L3(unittest.TestCase):
    def _w(self):
        return K.make_world([K.body(1, [0, 5, 0], [1, 0, 0], [1, 1, 1]),
                             K.body(2, [3, 5, 0], [-1, 0, 0], [1, 1, 1])],
                            bounds=((-10, 0, -10), (10, 10, 10)), gravity=10, dt_ms=16)

    def test_no_write_back(self):
        import snapshot as S
        w = self._w(); h = K.state_hash(w)
        snap = S.l1_snapshot(w)
        snap["bodies"][0]["pos"][0] = 10 ** 18                # render layer mutates its read-only copy
        K.step(w)
        self.assertEqual(K.state_hash(w), h)                  # L1 unaffected by the render layer

    def test_l2_drift_is_benign(self):
        import snapshot as S
        snap = S.l1_snapshot(self._w())
        a, b = S.render_observe(snap, 11), S.render_observe(snap, 77)
        self.assertTrue(S.l1_agrees(a, b))                    # gate (L1) matches
        self.assertNotEqual(a["particles"], b["particles"])   # observables (L2) may differ

    def test_l1_injection_detected(self):
        import snapshot as S
        w = self._w(); expected = K.state_hash(w)
        w["bodies"][0]["pos"][1] += SCALE * 5                 # "memory injection" teleport
        ok, _ = S.detect_l1_injection(w, expected)
        self.assertFalse(ok)


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("set PYTHONHASHSEED=0\n"); raise SystemExit(2)
    unittest.main(verbosity=2)
