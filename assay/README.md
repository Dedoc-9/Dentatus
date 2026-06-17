# assay — a meta-audit layer for "correct, fair, or wise"

The rest of the workbench is careful to say **integrity is not truth** — it proves *what was recorded*,
never that a decision was good. `assay` is the honest way to engage the next layer up: it does **not**
certify that a decision is correct, fair, or wise. It makes the **quality judgments themselves** first-class
records — bound to the decisions they assess, reproducible (for metrics), attributable (for opinions), and
tamper-evident. You can't prove a decision was fair, but you *can* prove **nobody fudged the fairness
report.** Integrity, applied one level up.

## Run it

```bash
PYTHONHASHSEED=0 python3 demo_assay.py        # correctness, fairness, signed wisdom, fudge + forgery caught
PYTHONHASHSEED=0 python3 tests/test_assay.py  # 10 unit tests
```

## Three words, three honesty tiers

| Word | How `assay` handles it | Court action | Honest limit |
|---|---|---|---|
| **Correct** | deterministic check vs a supplied ground-truth oracle (`metrics.py`) | **recomputes** the metric | only as good as the oracle; many decisions have no ground truth |
| **Fair** | a statistical metric over a cohort — group approval-parity (`metrics.py`) | **recomputes** the metric | a population property; needs sensitive labels; fairness definitions provably conflict — this is ONE metric |
| **Wise** | a signed opinion under a named, source-hashed rubric, by a registered assessor (`judgment.py`) | verifies **attribution + rubric binding** | a recorded opinion, never a proof |

## What the assay court proves

Each assessment is bound to a decision's `committed_hash` and itself chained + signed by an assay
authority. The court re-derives the log and then, per assessment:

- **metric** → the metric source is unchanged and re-running it over the recorded evidence reproduces the
  recorded value bit-for-bit, and the recorded pass/fail follows from it. Even an attacker **holding the
  assay key** cannot fudge a number — the demo re-signs a doctored fairness value and is still
  `REJECTED: METRIC RECOMPUTE mismatch`.
- **judgment** → the opinion is rubric-bound and verifies under the assessor's **pinned** public key. A
  rogue key signing "this was wise" as a real reviewer is `REJECTED` (impersonation); an altered score
  after signing is rejected; an unknown assessor is rejected.

It does **not** re-decide correctness/fairness/wisdom. It proves the recorded assessments are honest,
reproducible (metrics), and attributable (judgments) — the integrity of the judgments, not their truth.

## Files

| File | Role |
|---|---|
| `metrics.py` | deterministic, recomputable metrics: `correctness_vs_oracle`, `group_approval_parity` |
| `judgment.py` | `Rubric` + signed, attributable `make_judgment` / `verify_judgment` (trusted-assessor registry) |
| `assess.py` | `AssayRecorder` — binds assessments to a decision's `committed_hash`, chains + signs them |
| `court.py` | `assay_audit` — recompute metrics, verify judgments, re-derive the attestation chain |
| `demo_assay.py` | end-to-end over a batch of lending decisions |
| `tests/test_assay.py` | metric, judgment, and tamper/forgery tests |

## Honest scope

A reference layer, not a fairness/ethics oracle. Choosing the metric, the oracle, the rubric, and the
trusted assessors is a human governance act `assay` records but does not make for you — and a different
fair-metric can disagree with the one shown. Depends on `../llm_toolkit` for the shared primitives.
**Integrity is not truth**, all the way up.
