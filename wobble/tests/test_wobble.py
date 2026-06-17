"""Tests for the wobble synthetic-gene verification sibling."""
import os, sys, copy, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import canonical_codon as C
import wobble_capture as W
import core
from court import verify_chain
from signing import HmacSigner
import demo_wobble as D


class TestGeneticCode(unittest.TestCase):
    def test_table_complete(self):
        self.assertEqual(len(C.CODON_TABLE), 64)
        self.assertEqual(sum(1 for v in C.CODON_TABLE.values() if v == "*"), 3)   # 3 stop codons

    def test_translation(self):
        self.assertEqual(C.translate("ATGGCTGGTGAA"), "MAGE")
        self.assertEqual(C.translate("AUGGCUGGU"), "MAG")                          # RNA U->T

    def test_synonymous_collapse_and_fork(self):
        self.assertEqual(C.functional_hash("ATGGCTGGTGAA"), C.functional_hash("ATGGCCGGCGAG"))  # synonymous
        self.assertNotEqual(C.functional_hash("ATGGCTGGTGAA"), C.functional_hash("ATGGTTGGTGAA"))  # A->V

    def test_synonymous_listing(self):
        self.assertEqual(C.synonymous("GGT"), ["GGA", "GGC", "GGG", "GGT"])        # all 4 Gly codons

    def test_bad_sequence_rejected(self):
        with self.assertRaises(C.SequenceError):
            C.codons_of("ATGGC")        # not a multiple of 3
        with self.assertRaises(C.SequenceError):
            C.normalize("ATGZ")         # non-ACGT


class TestStructuralMetrics(unittest.TestCase):
    def test_gc(self):
        self.assertEqual(W.gc_content("GGCC"), 100.0)
        self.assertEqual(W.gc_content("ATAT"), 0.0)

    def test_homopolymer(self):
        self.assertEqual(W.max_homopolymer_run("ATGAAAAAGGG"), 5)

    def test_restriction(self):
        self.assertEqual(W.restriction_sites("GGGAATTCGGG"), [("EcoRI", 2)])
        self.assertEqual(W.restriction_sites("ATGCATGC"), [])

    def test_cai_deterministic_and_bounded(self):
        v = W.cai("ATGGCTGGTGAA")
        self.assertEqual(v, W.cai("ATGGCTGGTGAA"))
        self.assertTrue(0.0 < v <= 1.0)


class TestGatedDesign(unittest.TestCase):
    def _rec(self):
        return core.Recorder(HmacSigner(b"k"), core.ruleset_hash(D.design_logic, D.structural_invariant))

    def test_valid_seals_and_replays(self):
        d = D._design("MAGE", ["ATG", "GCT", "GGT", "GAA"])
        r = self._rec().record("V", d, D.design_logic(d), D.structural_invariant)
        self.assertTrue(verify_chain([r], b"k", D.design_logic, D.structural_invariant).ok)

    def test_gc_breach_refused(self):
        d = D._design("MAGE", ["ATG", "GCG", "GGC", "GAG"])
        with self.assertRaises(core.InvariantViolation):
            self._rec().record("X", d, D.design_logic(d), D.structural_invariant)

    def test_homopolymer_breach_refused(self):
        d = D._design("MKK", ["ATG", "AAA", "AAA"])
        with self.assertRaises(core.InvariantViolation):
            self._rec().record("X", d, D.design_logic(d), D.structural_invariant)

    def test_restriction_site_refused(self):
        d = D._design("MEF", ["ATG", "GAA", "TTC"])
        with self.assertRaises(core.InvariantViolation):
            self._rec().record("X", d, D.design_logic(d), D.structural_invariant)

    def test_protein_mismatch_refused(self):
        d = D._design("MAGE", ["ATG", "GTT", "GGT", "GAA"])   # translates MVGE
        with self.assertRaises(core.InvariantViolation):
            self._rec().record("X", d, D.design_logic(d), D.structural_invariant)

    def test_tamper_caught(self):
        d = D._design("MAGE", ["ATG", "GCT", "GGT", "GAA"])
        r = self._rec().record("V", d, D.design_logic(d), D.structural_invariant)
        bad = copy.deepcopy([r]); bad[0]["frame"]["inputs"]["_design"]["codons"][1] = "GTT"  # silently mutate
        self.assertFalse(verify_chain(bad, b"k", D.design_logic, D.structural_invariant).ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
