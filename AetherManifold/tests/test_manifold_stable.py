"""AetherManifold/tests/test_manifold_stable.py — Riemannian GD, projection, two-tier, stability, conformance."""
import os, sys, unittest
_M = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _M)
sys.path.insert(0, os.path.join(os.path.dirname(_M), "chronicle"))
import objective as O
import riemann as R
import stability as STA
import conformance as C
from _cores import SCALE
fp = O.fp


def problem():
    Xstar = [[fp(3, 5), 0], [fp(4, 5), 0], [0, fp(1)]]
    A = O.identity(3); B = R.F.matmul(A, Xstar)
    grad, energy = O.procrustes(A, B)
    return grad, energy, [[fp(1, 2), 0], [fp(1, 2), 0], [0, fp(1)]]


class Optimizer(unittest.TestCase):
    def test_converges(self):
        grad, energy, X0 = problem()
        res = R.optimize(X0, grad, fp(1, 5), 60, energy)
        self.assertLess(res["energies"][-1], res["energies"][0] // 1000)   # energy drops >1000x

    def test_orthonormality_held(self):
        grad, energy, X0 = problem()
        res = R.optimize(X0, grad, fp(1, 5), 60, energy)
        self.assertLessEqual(max(res["defects"]), 16)        # within a few ulp throughout

    def test_deterministic(self):
        grad, energy, X0 = problem()
        self.assertEqual(R.optimize(X0, grad, fp(1, 5), 60)["hashes"],
                         R.optimize(X0, grad, fp(1, 5), 60)["hashes"])

    def test_projection_is_tangent(self):
        # P_X(Z) has near-zero symmetric part of X^T P (it lies in the tangent space)
        X = R.retract([[fp(1), 0], [0, fp(1)], [0, 0]])
        Z = [[fp(1, 3), fp(1, 7)], [fp(1, 5), fp(1, 2)], [fp(1, 9), fp(1, 4)]]
        P = R.proj_tangent(X, Z)
        XtP = R.F.matmul(R.transpose(X), P)
        s = R.sym(XtP)
        self.assertTrue(all(abs(s[i][j]) <= 4 for i in range(2) for j in range(2)))  # ~0 symmetric part


class TwoTier(unittest.TestCase):
    def test_exact_tier_no_epsilon(self):
        ok, _ = R.ST.is_orthonormal_exact([[3, 4, 0], [0, 0, 5]], 5)
        self.assertTrue(ok)

    def test_exact_tier_catches_perturbation(self):
        ok, _ = R.ST.is_orthonormal_exact([[3, 4, 0], [0, 1, 5]], 5)
        self.assertFalse(ok)


class StabilityObs(unittest.TestCase):
    def test_shadowing_contracts(self):
        grad, energy, X0 = problem()
        d = STA.co_run(X0, grad, fp(1, 5), 60)
        self.assertLessEqual(d[-1], d[0])                    # converging problem -> not diverging
        self.assertLessEqual(STA.lyapunov_estimate(d), 0.0)


class Conformance(unittest.TestCase):
    def test_all_edge_cases_verify(self):
        for name in ("converge", "near_singular", "zero_gradient", "aggressive_eta"):
            self.assertTrue(C.verify_vector(C.make_vector(name))[0], name)

    def test_divergent_fails(self):
        self.assertFalse(C.verify_vector(dict(C.make_vector("converge"), final_hash="0" * 64))[0])

    def test_zero_gradient_stays(self):
        # starting at the minimum, the trajectory should barely move (final defect 0)
        self.assertEqual(C.make_vector("zero_gradient")["final_defect"], 0)


class Lyapunov(unittest.TestCase):
    def setUp(self):
        import lyapunov as L
        self.L = L
        grad, energy, X0 = problem()
        self.res = R.optimize(X0, grad, fp(1, 5), 60, energy)

    def test_discrete_derivative(self):
        self.assertEqual(self.L.discrete_derivative([3, 1, 0]), [-2, -1])

    def test_compress_bounded_and_signed(self):
        self.assertLess(abs(self.L.compress(10 ** 30)), SCALE)
        self.assertEqual(self.L.compress(-10 ** 30), -self.L.compress(10 ** 30))
        self.assertEqual(self.L.compress(5), (5 * SCALE) // (SCALE + 5))   # ~identity for small dv

    def test_compress_rejects_bad_scale(self):
        with self.assertRaises(ValueError):
            self.L.compress(5, R=0)

    def test_saturate(self):
        self.assertEqual(self.L.saturate(100, 10), 10)
        self.assertEqual(self.L.saturate(-100, 10), -10)

    def test_certificate_monotone_single_branch(self):
        c = self.L.certificate(self.res["energies"], self.res["defects"])
        self.assertTrue(c["monotone_descent"]); self.assertEqual(c["n_branches"], 1)
        self.assertLess(c["max_compressed_dV"], SCALE)        # certificate cannot overflow

    def test_certificate_forks_near_singular(self):
        grad, energy, _ = problem()
        res = R.optimize([[fp(1), fp(99, 100)], [0, fp(1, 100)], [fp(1, 100), 0]], grad, fp(1, 5), 60, energy)
        c = self.L.certificate(res["energies"], res["defects"], tol=2)
        self.assertEqual(c["n_branches"], 2)                  # the fork is detected
        self.assertTrue(all(b["descent_holds"] for b in c["branches"].values()))  # descent holds per branch

    def test_composite_max(self):
        comp, active = self.L.composite_max([1, 5, 2], [3, 4, 9])
        self.assertEqual(comp, [3, 5, 9]); self.assertEqual(active, [1, 0, 1])


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("set PYTHONHASHSEED=0\n"); raise SystemExit(2)
    unittest.main(verbosity=2)
