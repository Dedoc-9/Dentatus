"""
wobble/wobble_capture.py — structural metrics (EXACT, gate material) + biophysical observables (CAPTURED).

THE SPLIT (mirrors `manifold`'s exact-gate / captured-observable design):
  EXACT, deterministic, gate-able (pure functions of the nucleotide string):
      gc_content, max_homopolymer_run, restriction_sites
  MODEL-DEPENDENT, captured OBSERVABLE only (never a gate, never in the commit hash):
      cai (Codon Adaptation Index) — exact *given a pinned codon-usage table*, but the table is a
      PARAMETER, not ground truth; and mRNA folding ΔG / expression curves (not implemented — they need a
      biophysical model and would be captured, never gated).

The genuinely non-deterministic thing is the DESIGN CHOICE — which synonymous codons an LLM/model picked.
That choice is recorded as input (the codon sequence) with its provenance (`design_provenance`), exactly
like `llm_toolkit` captures a model call. Once the codons are fixed, every metric below is exact.

Imports nothing biological; stdlib + the frozen chronicle core only.
"""
import math
import canonical_codon as C

# Common type-II restriction sites (palindromic recognition sequences) to forbid in a synthetic insert.
DEFAULT_RESTRICTION_SITES = {
    "EcoRI": "GAATTC", "BamHI": "GGATCC", "HindIII": "AAGCTT", "NotI": "GCGGCCGC",
    "XhoI": "CTCGAG", "NdeI": "CATATG",
}

# ILLUSTRATIVE pinned relative-adaptiveness weights (E. coli-flavored), w in (0,1] per codon. This is a
# PARAMETER for CAI, deliberately not authoritative — swap in a real organism table for production use.
ECOLI_W = {
    "TTT": 0.50, "TTC": 1.00, "TTA": 0.10, "TTG": 0.10, "CTT": 0.10, "CTC": 0.10, "CTA": 0.04, "CTG": 1.00,
    "ATT": 0.50, "ATC": 1.00, "ATA": 0.10, "ATG": 1.00, "GTT": 1.00, "GTC": 0.40, "GTA": 0.30, "GTG": 0.40,
    "TCT": 0.80, "TCC": 0.80, "TCA": 0.20, "TCG": 0.20, "AGT": 0.20, "AGC": 1.00,
    "CCT": 0.30, "CCC": 0.20, "CCA": 0.30, "CCG": 1.00, "ACT": 0.50, "ACC": 1.00, "ACA": 0.20, "ACG": 0.30,
    "GCT": 0.80, "GCC": 0.50, "GCA": 0.40, "GCG": 1.00, "TAT": 0.60, "TAC": 1.00, "CAT": 0.60, "CAC": 1.00,
    "CAA": 0.30, "CAG": 1.00, "AAT": 0.50, "AAC": 1.00, "AAA": 1.00, "AAG": 0.30, "GAT": 1.00, "GAC": 0.60,
    "GAA": 1.00, "GAG": 0.40, "TGT": 0.50, "TGC": 1.00, "TGG": 1.00, "CGT": 1.00, "CGC": 0.70, "CGA": 0.10,
    "CGG": 0.10, "AGA": 0.05, "AGG": 0.05, "GGT": 0.90, "GGC": 1.00, "GGA": 0.20, "GGG": 0.30,
    "TAA": 1.00, "TAG": 1.00, "TGA": 1.00,
}


def gc_content(seq):
    """Percent G+C. Exact rational; rounded to 4 dp for a stable observable/gate value."""
    s = C.normalize(seq)
    if not s:
        return 0.0
    return round(100.0 * (s.count("G") + s.count("C")) / len(s), 4)


def max_homopolymer_run(seq):
    """Longest run of a single base (e.g. 'AAAAA' -> 5). Exact."""
    s = C.normalize(seq)
    best = run = 0
    prev = ""
    for b in s:
        run = run + 1 if b == prev else 1
        prev = b
        best = max(best, run)
    return best


def restriction_sites(seq, sites=None):
    """Every forbidden recognition site found, as sorted (enzyme, position) pairs. Exact substring scan."""
    s = C.normalize(seq)
    sites = sites or DEFAULT_RESTRICTION_SITES
    hits = []
    for name, motif in sites.items():
        start = 0
        while True:
            i = s.find(motif, start)
            if i < 0:
                break
            hits.append((name, i))
            start = i + 1
    return sorted(hits)


def cai(seq, weights=None):
    """Codon Adaptation Index: geometric mean of per-codon weights over the pinned table. OBSERVABLE only
    (the weight table is a parameter, not ground truth). Met/Trp/stop are excluded (non-degenerate)."""
    weights = weights or ECOLI_W
    ws = []
    for c in C.codons_of(seq):
        aa = C.CODON_TABLE[c]
        if aa in ("M", "W", "*"):
            continue
        ws.append(weights.get(c, 0.5))
    if not ws:
        return 1.0
    return round(math.exp(sum(math.log(w) for w in ws) / len(ws)), 6)


def design_provenance(codons, model_id, usage_table_id, seed=None):
    """Record WHAT process chose the codons (the captured non-determinism). The codons themselves are the
    concrete recorded sequence; this is the provenance an auditor needs to attribute the design choice."""
    return {"codons": list(codons), "design_model": model_id,
            "codon_usage_table": usage_table_id, "seed": seed}
