"""
wobble/canonical_codon.py — content-addressed FUNCTIONAL identity for nucleotide sequences.

Strip the biology to the data structure: the genetic code is degenerate. Synonymous codons (often
differing only at the 3rd "wobble" base) translate to the same amino acid — e.g. GGT/GGC/GGA/GGG all ->
Glycine. So the PROTEIN is the content-addressable functional identity; the nucleotide string is the
volatile representation. Two different sequences encoding the same protein get the SAME functional hash.

DETERMINISTIC + EXACT: translation is a table lookup (NCBI standard code, table 1), so `functional_hash`
is a pure function of the sequence — bit-stable, replay-safe, stdlib-only. Imports the frozen `chronicle`
core read-only for `state_hash` (Sibling Law).

HONEST BOUND (kept loud everywhere in this module): collapsing synonymous codons proves PRIMARY-STRUCTURE
(amino-acid) identity. It deliberately abstracts away codon choice — which DOES affect translation
efficiency, mRNA folding, and co-translational folding. Same functional hash != same biological behavior.
Cryptographic integrity is not biological truth.
"""
import os
import sys

_WB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
import core  # frozen: state_hash / canonical_bytes

# NCBI standard genetic code (translation table 1). DNA letters; 'U' is normalized to 'T'. '*' = stop.
CODON_TABLE = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L", "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M", "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S", "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T", "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*", "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K", "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W", "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R", "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}

# amino acid -> its synonymous codons (the degeneracy classes)
SYNONYMS = {}
for _c, _aa in CODON_TABLE.items():
    SYNONYMS.setdefault(_aa, []).append(_c)
for _aa in SYNONYMS:
    SYNONYMS[_aa] = sorted(SYNONYMS[_aa])


class SequenceError(Exception):
    pass


def normalize(seq):
    """Uppercase, strip whitespace, map RNA U->T. Validate alphabet {A,C,G,T}."""
    s = "".join(seq.split()).upper().replace("U", "T")
    bad = set(s) - set("ACGT")
    if bad:
        raise SequenceError("non-ACGT/U symbols: %s" % sorted(bad))
    return s


def codons_of(seq):
    s = normalize(seq)
    if len(s) % 3 != 0:
        raise SequenceError("length %d is not a multiple of 3" % len(s))
    return [s[i:i + 3] for i in range(0, len(s), 3)]


def translate(seq, stop_at_stop=True):
    """Exact codon->amino-acid translation. Returns the 1-letter amino-acid string (no trailing '*')."""
    aas = []
    for c in codons_of(seq):
        aa = CODON_TABLE[c]
        if aa == "*":
            if stop_at_stop:
                break
            aa = "*"
        aas.append(aa)
    return "".join(aas)


def functional_hash(seq):
    """Content address of the FUNCTIONAL identity = hash of the translated protein. Synonymous sequences
    collapse to the same hash; a non-synonymous change forks it."""
    return core.state_hash({"protein": translate(seq), "code": "ncbi-1"})


def synonymous(codon):
    """All codons synonymous with `codon` (same amino acid), sorted."""
    return list(SYNONYMS[CODON_TABLE[normalize(codon)]])
