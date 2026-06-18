"""aether/tests/test_aether_stiefel.py — fixed-point manifold: exact gate, audit, retraction, evolution."""
import os, sys, unittest
_A = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WB = os.path.dirname(_A)
sys.path.insert(0, _A)
sys.path.insert(0, os.path.join(_WB, "crucible"))
import fixedpoint as F
import stiefel as S
import evolve as E


class ExactGate(unittest.TestCase):
    def test_rational_rotation_orthonormal(self):
        self.assertTrue(S.is_orthonormal_exact([[3, 4], [-4, 3]], 5)[0])

    def test_rational_3x3_orthogonal(self):
        self.assertTrue(S.is_orthonormal_exact([[2, 1, 2], [-2, 2, 1], [1, 2, -2]], 3)[0])

    def test_perturbation_caught_no_epsilon(self):
        ok, viol = S.is_orthonormal_exact([[3, 4], [-4, 4]], 5)
        self.assertFalse(ok); self.assertEqual((viol[0]["i"], viol[0]["j"]), (0, 1))

    def test_exact_skew(self):
        self.assertTrue(E.is_skew_symmetric([[0, 2, -3], [-2, 0, 5], [3, -5, 0]])[0])


class Audit(unittest.TestCase):
    def test_identity_passes(self):
        chk = S.check_orthogonality(F.identity(3))
        self.assertTrue(chk["ok"]); self.assertEqual(chk["E"], 0)

    def test_energy_is_sum_of_squares(self):
        W = F.identity(2)
        W[0][1] = F.SCALE // 2                                # introduce an off-diagonal residual
        E_val = S.frobenius_energy(W)
        self.assertGreater(E_val, 0)

    def test_rotated_frame_fails_then_retracts(self):
        gen = [[0, F.to_fp(1)], [F.to_fp(-1), 0]]
        W = E.evolve_raw(F.identity(2), gen, F.to_fp(1, 100), 4000)   # genuinely drift off the manifold
        self.assertFalse(S.check_orthogonality(W)["ok"])
        Wr = S.handle_retraction(W, last_valid=F.identity(2))["recovered"]
        self.assertTrue(S.check_orthogonality(Wr)["ok"])      # retraction restores within epsilon


class Evolution(unittest.TestCase):
    def test_audited_stays_on_manifold(self):
        gen = [[0, F.to_fp(1), 0], [F.to_fp(-1), 0, F.to_fp(1, 2)], [0, F.to_fp(-1, 2), 0]]
        res = E.evolve_audited(F.identity(3), gen, F.to_fp(1, 1000), 50000, audit_every=1000)
        self.assertTrue(S.check_orthogonality(res["W"])["ok"])

    def test_deterministic(self):
        gen = [[0, F.to_fp(1), 0], [F.to_fp(-1), 0, F.to_fp(1, 2)], [0, F.to_fp(-1, 2), 0]]
        a = E.evolve_audited(F.identity(3), gen, F.to_fp(1, 1000), 50000, audit_every=1000)
        b = E.evolve_audited(F.identity(3), gen, F.to_fp(1, 1000), 50000, audit_every=1000)
        self.assertEqual(a["final_hash"], b["final_hash"])

    def test_retraction_shard_is_content_addressed(self):
        gen = [[0, F.to_fp(1)], [F.to_fp(-1), 0]]
        W = E.evolve_raw(F.identity(2), gen, F.to_fp(1, 100), 4000)
        shard = S.handle_retraction(W, last_valid=F.identity(2))["shard"]
        self.assertIn("shard_hash", shard); self.assertEqual(shard["event"], "RETRACTION")


class CrucibleStress(unittest.TestCase):
    def test_hard_seed_retraction_robust(self):
        # near-degenerate frame: two nearly-parallel columns -> high energy -> must retract within budget
        s = F.SCALE
        W = [[s, s - 3], [3, 5]]                              # not orthonormal; small second column
        self.assertFalse(S.check_orthogonality(W)["ok"])
        rec = S.handle_retraction(W, last_valid=F.identity(2))
        self.assertTrue(S.check_orthogonality(rec["recovered"])["ok"])


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("set PYTHONHASHSEED=0\n"); raise SystemExit(2)
    unittest.main(verbosity=2)
