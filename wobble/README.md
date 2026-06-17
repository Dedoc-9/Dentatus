# wobble — verifiable synthetic-gene design (codon degeneracy as a data structure)

A Sibling-Law component: it imports the frozen [`chronicle`](../chronicle/README.md) core read-only and
treats the genetic translation pipeline as a deterministic state machine. Strip the biology to the data
structure and one fact does the work: the genetic code is **degenerate** — synonymous codons (often
differing only at the 3rd "wobble" base) translate to the same amino acid (GGT/GGC/GGA/GGG → Glycine). So
the **protein is the content-addressable functional identity; the nucleotide string is the volatile
representation.**

## Run it

```bash
PYTHONHASHSEED=0 python3 demo_wobble.py        # functional identity, exact structural gate, capture+replay
PYTHONHASHSEED=0 python3 tests/test_wobble.py  # 15 tests
```

## What it does — the exact / observable split

| Layer | What | Where it runs |
|---|---|---|
| **Functional identity** (`canonical_codon.py`) | `functional_hash` = hash of the translated protein; synonymous sequences collapse to one hash, a non-synonymous change forks it (NCBI standard code, exact table lookup) | the commit hash (deterministic) |
| **Diamond-hard gate** (`wobble_capture.py`) | **exact** structural rules: GC-content clamp, homopolymer-run limit, forbidden restriction sites, protein-match | the precommitted invariant (fail-closed) |
| **Biophysical observable** | **CAI** (Codon Adaptation Index) vs a *pinned* codon-usage table — exact given the table, but the table is a parameter, not ground truth; mRNA folding ΔG / expression curves would also be captured here | a captured observable, **never** the gate, **never** in the hash |

The genuinely non-deterministic thing is the **design choice** — which synonymous codons a model picked.
That choice is recorded as input with its provenance (`design_provenance`: model id, usage table, seed),
exactly as `llm_toolkit` records a model call. Once the codons are fixed, every metric is exact.

The demo seals a valid `MAGE` design, **refuses** four breaches fail-closed (GC > 60 %, a 6-base
homopolymer, an EcoRI site, and a protein that doesn't match the target), and the Replay Court reproduces
the sealed design bit-for-bit — **without re-simulating any biology**.

## What's genuinely new here (and what isn't)

Content-addressing, deterministic replay, and out-of-process privilege separation are **not** new in
computer science. What's new is *transferring that exact discipline onto biological sequence design*, where
the status quo treats DNA/RNA as flat text in a database and codon optimization as a loosely-logged,
non-deterministic generation task. `wobble/` upends that on three vectors — each with its honest bound.

**1. Functional identity vs. volatile representation.** Standard bioinformatics fingerprints a gene by its
*nucleotide* hash. But the code is degenerate: many distinct nucleotide strings translate to the identical
protein. `wobble/` content-addresses the **protein** (`functional_hash` over the exact amino-acid
translation), so synonymous third-base "wobble" mutations collapse to one identity while the codon choice
is cleanly isolated as a recorded, volatile representation. *Bound:* this is primary-structure identity —
same hash ≠ same biology (codon choice still affects translation/folding), which is exactly why the choice
is recorded, not erased.

**2. The exact-gate / captured-observable split, applied to biology.** Biophysics tooling suffers model
drift: mRNA-folding (ΔG) and translation-efficiency models get re-parameterized, so historical simulations
stop reproducing. `wobble/` splits the pipeline — the **diamond-hard gate** is only the *exactly* computable
string/integer rules (GC clamp, homopolymer limit, restriction-site match, protein identity), fail-closed
and host-side; the **model-dependent metrics** (CAI today, ΔG tomorrow) are computed at the boundary and
captured into the ledger inputs. *Result:* the Replay Court never re-simulates an unstable biological model
during an audit — it reads the frozen metrics from the record, so verification is bit-identical on any
machine. *Bound:* it verifies the *design trail*, not the biology; a captured CAI is only as meaningful as
its pinned table.

**3. Machine-checkable governance for automated gene editors.** As LLM agents design sequences at speed, a
reviewer cannot eyeball thousands of bases for a forbidden restriction site or a GC breach. `wobble/` moves
that to a signed, precommitted predicate at the ledger boundary: an agent that mutates wobble positions to
chase a metric but trips a homopolymer run or a GC clamp gets an immediate `InvariantViolation` and a
rollback. *Bound:* the gate refuses **exactly what the precommitted predicate encodes** — not unsafety you
never wrote down, and not anything a biosecurity screen would catch (see the responsible-use note). The
agent cannot *commit* a design the gate rejects; that is enforcement of a declared policy, not a claim of
biological safety.

**The modest baseline.** Net: `wobble/` offers a tamper-evident, reproducible, and (with Ed25519)
third-party-verifiable *record* of a genetic design — proof that a design was untampered, rule-faithful to
a precommitted policy, and exactly reproducible from the moment it was conceived. It does **not** predict
biological truth or substitute for biosecurity screening. A clean record is the floor, not the ceiling.

## Honest boundary (integrity ≠ biological truth)

This proves a design record is **unforged, functionally reproducible, and rule-faithful to a precommitted
structural policy.** It does **not** prove the gene will express in a living cell, that the policy captures
real biology, or that the CAI table is accurate. Crucially, **same functional hash ≠ same biology** —
synonymous codon choice still affects translation efficiency and folding, which is *why* codon choice is
recorded rather than erased.

## ⚠️ Biosecurity & responsible use

This is gene-design bookkeeping (translate, GC, homopolymer, restriction-site scan, content-addressing) —
**not** a biosecurity screen, hazard classifier, or biocontainment control, and it makes no judgment about
whether a sequence is safe to synthesize. Use it only for authorized work on benign sequences. Legitimate
synthesis runs through providers that screen orders against controlled-/select-agent sequence databases
and applicable export-control and biosafety law; this module neither performs nor replaces that screening.
Capability is not permission.

## Files

| File | Role |
|---|---|
| `canonical_codon.py` | NCBI standard code, exact `translate`, `functional_hash` (protein = identity), `synonymous` |
| `wobble_capture.py` | exact `gc_content`/`max_homopolymer_run`/`restriction_sites`, CAI observable, design provenance |
| `demo_wobble.py` | functional identity + exact gate + capture/seal/replay |
| `tests/test_wobble.py` | 15 tests: genetic code, metrics, gated design (seal + every breach refused), tamper |
