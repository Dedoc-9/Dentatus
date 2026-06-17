# chronicle — a verifiable decision recorder

**Start here:** [`chronicle/`](chronicle/README.md)

`chronicle` is a tamper-evident **flight recorder + replay court** for consequential automated
decisions (lending, eligibility, pricing, moderation, model scoring). Given a decision's hash it will
**replay** the exact computation that produced it, prove the record and the rules were **not altered**,
and prove the decision satisfied safety rules **committed before deployment** — on a separate machine,
line by line, and (with Ed25519) without the power to forge.

The stdlib-only core records and verifies with **zero dependencies**; optional layers add asymmetric
attestation, determinism capture, and pluggable storage so a team can adopt it without re-architecting.

```bash
cd chronicle
PYTHONHASHSEED=0 python3 demo_policy.py              # record, verify, tamper, rule-swap, capture, store
PYTHONHASHSEED=0 python3 tests/test_chronicle.py     # 19 unit tests
```

> `demo_policy.py` refuses to run without `PYTHONHASHSEED=0` — bit-identical hashing across processes is
> the premise of the replay court, so it fails fast rather than produce a chain you cannot reproduce.

## What it proves (and what it doesn't)

For each recorded decision the court checks five things and names the exact failure point: **chain**
(no insert/delete/reorder), **rule-bound** (the audited logic source-hashes to the recorded ruleset),
**replay** (inputs reproduce outputs bit-for-bit), **invariant** (a precommitted hard rule still holds;
unsafe decisions are refused at record time, fail-closed), and **attest** (re-derived hash + signature
match). It proves a record is *unforged, exactly reproducible, and rule-faithful* — **not** that the
decision was correct or fair. Integrity is not truth.

See [`chronicle/README.md`](chronicle/README.md) for the full design, the three adoption blockers it
addresses (the determinism tax, symmetric-key limitation, and missing integrations), and the file map.

## Background / lineage

`chronicle` is distilled from the verification discipline of **Dentatus** (the "Reality Engine"), a
deterministic, content-addressed state machine with a cryptographic audit trail. For an honest,
de-inflated account of that project — what it is, what's genuinely solid, and what it is *not* — read
[`OVERVIEW.md`](OVERVIEW.md).

The full Dentatus / Citadel implementation (engine, game layer, forge test-harnesses, constitution,
experiment runners, studies) has been moved under [`docs/archive/`](docs/archive/) so this directory
leads with the active artifact. Its self-verifying proofs still run — from inside `docs/archive/`:

```bash
cd docs/archive
PYTHONHASHSEED=0 python3 forge/oracle_fuzz.py         # differential fuzzer, 0 violations / 20k cases
PYTHONHASHSEED=0 python3 walkthrough_genesis.py       # end-to-end self-verifying lifecycle
```

The legacy game client lives in [`Game1/`](Game1/), a separately-connected folder.

## Repository map

| Path | What it is |
|---|---|
| [`chronicle/`](chronicle/README.md) | **active** — verifiable decision recorder (library + CLI + tests) |
| [`OVERVIEW.md`](OVERVIEW.md) | honest technical overview of the Dentatus lineage |
| [`docs/archive/`](docs/archive/) | archived Reality Engine / Citadel implementation + experiment runners |
| `Game1/` | archived game client (separately-connected folder) |
| `LICENSE`, `DUAL_LICENSE.md` | licensing |

**Primary architect:** Daniel J. Dillberg — bigdilly95@gmail.com
**License:** dual-licensed (AGPL-3.0 open track / commercial closed track) — see `DUAL_LICENSE.md`.
