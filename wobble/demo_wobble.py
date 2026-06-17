"""
wobble/demo_wobble.py — verifiable synthetic-gene design on the frozen Chronicle ledger.

Run:  PYTHONHASHSEED=0 python3 demo_wobble.py

  A. FUNCTIONAL IDENTITY  — synonymous sequences (different wobble bases) collapse to one functional hash;
                            a non-synonymous change forks it.
  B. EXACT STRUCTURAL GATE— a design must pass precommitted, exactly-computable biochemical rules
                            (GC clamp, homopolymer limit, no forbidden restriction sites, protein match);
                            breaches are refused fail-closed.
  C. CAPTURE + SEAL + REPLAY — a valid design (codons + provenance + CAI observable) is sealed; the Replay
                            Court reproduces it bit-for-bit without re-simulating any biology.

HONEST BOUND (loud): this proves a design record is unforged, functionally reproducible, and rule-faithful
to a PRECOMMITTED design policy. It does NOT prove the gene expresses in a living cell, nor that the policy
captures real biology. Cryptographic integrity is not biological truth. See README for the biosecurity note.
"""
import os, sys, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import canonical_codon as C
import wobble_capture as W
import core
from court import verify_chain, print_verdict
from signing import Ed25519Signer, Ed25519Verifier, ed25519_available, HmacSigner

# precommitted, exactly-computable design policy (a pinned biochemical constraint set)
GC_MIN, GC_MAX, MAX_HOMOPOLYMER = 40.0, 60.0, 5


def design_logic(inputs):
    """Deterministic: recompute the functional identity + exact structural metrics from the chosen codons.
    CAI is recomputed too (exact given the pinned table) and carried as an observable, never gated."""
    seq = "".join(inputs["_design"]["codons"])
    return {
        "functional_hash": C.functional_hash(seq),
        "protein": C.translate(seq),
        "gc_pct": W.gc_content(seq),
        "max_homopolymer": W.max_homopolymer_run(seq),
        "restriction_hits": [list(h) for h in W.restriction_sites(seq)],
        "cai_observable": W.cai(seq),
    }


def structural_invariant(inputs, outputs):
    """Diamond-hard, EXACT: protein matches the target AND GC in clamp AND homopolymer <= limit AND no
    forbidden restriction site. (CAI is an observable, deliberately NOT part of the gate.)"""
    return (outputs["protein"] == inputs["target_protein"]
            and GC_MIN <= outputs["gc_pct"] <= GC_MAX
            and outputs["max_homopolymer"] <= MAX_HOMOPOLYMER
            and len(outputs["restriction_hits"]) == 0)


def _design(target, codons):
    return {"target_protein": target,
            "_design": W.design_provenance(codons, model_id="demo-codon-optimizer-v1",
                                           usage_table_id="ECOLI_W-illustrative", seed=7)}


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("[wobble] run with PYTHONHASHSEED=0\n"); raise SystemExit(2)

    print("A) FUNCTIONAL IDENTITY (synonymous wobble collapses; non-synonymous forks):")
    g1 = "ATGGCTGGTGAA"; g2 = "ATGGCCGGCGAG"; g4 = "ATGGTTGGTGAA"   # MAGE, MAGE(syn), MVGE(non-syn)
    print("   %s -> %s  +%s" % (g1, C.translate(g1), C.functional_hash(g1)[:10]))
    print("   %s -> %s  +%s   (synonymous: same hash = %s)" %
          (g2, C.translate(g2), C.functional_hash(g2)[:10], C.functional_hash(g1) == C.functional_hash(g2)))
    print("   %s -> %s  +%s   (non-synonymous: same hash = %s)" %
          (g4, C.translate(g4), C.functional_hash(g4)[:10], C.functional_hash(g1) == C.functional_hash(g4)))

    if ed25519_available():
        signer = Ed25519Signer.generate(); verifier = Ed25519Verifier(signer.public_material())
    else:
        signer = HmacSigner(b"wobble"); verifier = signer
    rec = core.Recorder(signer, core.ruleset_hash(design_logic, structural_invariant))
    ledger = []

    print("\nB) EXACT STRUCTURAL GATE (GC %.0f-%.0f%%, homopolymer<=%d, no forbidden sites, protein match):"
          % (GC_MIN, GC_MAX, MAX_HOMOPOLYMER))
    cases = [
        ("VALID  MAGE", _design("MAGE", ["ATG", "GCT", "GGT", "GAA"]), True),
        ("GC>60% MAGE", _design("MAGE", ["ATG", "GCG", "GGC", "GAG"]), False),
        ("homopolymer", _design("MKK", ["ATG", "AAA", "AAA"]), False),
        ("EcoRI site ", _design("MEF", ["ATG", "GAA", "TTC"]), False),
        ("protein!=tgt", _design("MAGE", ["ATG", "GTT", "GGT", "GAA"]), False),  # translates MVGE
    ]
    for label, design, expect_ok in cases:
        out = design_logic(design)
        try:
            r = rec.record("DES-%s" % label.split()[0], design, out, structural_invariant)
            ledger.append(r)
            print("   [SEAL ] %s  protein=%s gc=%.1f homo=%d cai=%.3f sites=%s"
                  % (label, out["protein"], out["gc_pct"], out["max_homopolymer"], out["cai_observable"],
                     [h[0] for h in out["restriction_hits"]]))
        except core.InvariantViolation:
            why = []
            if out["protein"] != design["target_protein"]: why.append("protein!=%s(%s)" % (design["target_protein"], out["protein"]))
            if not (GC_MIN <= out["gc_pct"] <= GC_MAX): why.append("GC=%.1f%%" % out["gc_pct"])
            if out["max_homopolymer"] > MAX_HOMOPOLYMER: why.append("homo=%d" % out["max_homopolymer"])
            if out["restriction_hits"]: why.append("sites=%s" % [h[0] for h in out["restriction_hits"]])
            print("   [REFUSE] %s  fail-closed: %s" % (label, ", ".join(why)))

    print("\nC) REPLAY COURT verifies the sealed valid designs (no biology re-simulated):")
    print_verdict(verify_chain(ledger, verifier, design_logic, structural_invariant), len(ledger))

    print("\n   NOTE: same functional hash != same biology — synonymous codon choice still affects")
    print("   translation/folding (CAI shown as an observable, not a gate). Integrity != biological truth.")
