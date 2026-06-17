# chronicle — a verifiable decision recorder

A tamper-evident "flight recorder + replay court" for consequential automated decisions (lending,
eligibility, pricing, moderation, model scoring). The stdlib-only **core** records and verifies with
zero dependencies; optional layers add asymmetric attestation, determinism capture, and pluggable
storage so a corporate team can adopt it without re-architecting their stack.

Distilled from the verification discipline of the [Dentatus](../OVERVIEW.md) project — the determinism
and audit core, without the game/physics framing.

## The one-sentence value

> Give me a decision's hash, and I will **replay** the exact computation that produced it, prove the
> record and the rules were **not altered**, and prove it satisfied the safety rules **committed before
> deployment** — on a separate machine, line by line, and (with Ed25519) without the power to forge.

## Run it

```
PYTHONHASHSEED=0 python3 demo_policy.py      # end-to-end: record, verify, tamper, rule-swap, capture, store
PYTHONHASHSEED=0 python3 tests/test_chronicle.py   # 18 unit tests
```

The demo prints, in order: a clean verify, a flipped denial caught as REPLAY drift, a secretly-loosened
ruleset caught as RULESET changed, an unsafe decision refused at record time, an Ed25519 third-party
verify (and a wrong key rejected), a clock+bureau-reading decision that still replays bit-for-bit, and
the same flow verified out of an append-only file.

## What the court proves (and what it doesn't)

For each recorded decision, `court.verify_chain` checks five things and names the exact failure point:

1. **Chain** — prev-hash links + contiguous seq → no past decision can be inserted, deleted, or reordered.
2. **Rule-bound** — the auditor's logic is source-hashed and must equal the recorded `ruleset_hash` → the
   rules did not change after the fact.
3. **Replay** — re-running the logic on the recorded inputs reproduces the recorded outputs bit-for-bit.
4. **Invariant** — the replayed decision still satisfies a precommitted hard rule; the recorder **refuses
   to log** a decision that breaches it (fail-closed).
5. **Attest** — the re-derived content hash + signature match the receipt (record/key untampered).

**Honest boundary (integrity ≠ truth).** This proves a decision is *unforged, exactly reproducible, and
rule-faithful*. It does **not** claim the decision was *correct or fair* — only that the record is honest
and the declared rules were the ones applied. That modesty is the credible claim for an auditor or court.

## Designed for adoption — the three usual blockers, addressed

**1. The determinism tax (`capture.py`).** Real decision code reads clocks, RNGs, databases, and APIs, so
naive replay drifts. Instead of forcing a rewrite to "pure" logic, route those reads through a `Capture`
handle: at record time the side-effects run and their results are **captured into the decision's inputs**;
at replay the captured values are fed back, so the same logic reproduces the same outputs without ever
touching the clock/DB/network again. `verify_determinism()` is a CI leak-detector that flags any read you
forgot to route. The only discipline required is the capture seam — the business logic is otherwise untouched.

**2. Symmetric-key limitation (`signing.py`).** The default `HmacSigner` is symmetric (the verifier can
also forge), which needs heavy secrets infrastructure and gives an auditor no independent guarantee.
`Ed25519Signer` makes attestation **asymmetric**: the private key signs, and a third-party auditor holds
only the public key — they can prove authenticity and **cannot forge**. The signed message is the
`committed_hash`, identical across backends, so a ledger can be re-signed under a stronger backend without
changing any content address. (`pip install cryptography` enables it; HMAC remains the dependency-free
fallback.)

**3. No out-of-the-box integrations (`store.py`).** A ledger is just an **append-only** sequence, which
maps onto stores teams already run. `LedgerStore` is a 4-method ABC; `JsonlStore` is a real, durable
(fsync'd) file backend, and `store.py` documents ~15-line adapter sketches for **S3 Object-Lock (WORM)**,
**append-only Postgres**, and **Kafka**. The store only moves bytes — correctness is always re-derived by
the court — so any append-only store you operate becomes a verifiable decision log.

## Files

| File | Role |
|---|---|
| `core.py` | recorder: recursive float-stable canonicalization, source-hashed rule binding, hash chaining, fail-closed invariant gate, pluggable signer + store |
| `court.py` | verifier: `verify_chain()` + CLI (`python court.py ledger.json`) |
| `signing.py` | HMAC (symmetric, stdlib) and Ed25519 (asymmetric, optional) backends |
| `capture.py` | record-replay of nondeterministic reads + determinism leak-detector |
| `store.py` | `LedgerStore` ABC, `MemoryStore`, durable `JsonlStore`, adapter sketches |
| `demo_policy.py` | end-to-end proof on a credit-eligibility flow |
| `tests/test_chronicle.py` | 18 unit tests covering all guarantees + hardening |

## Honest scope

A reference implementation, not a product: no access control, no throughput tuning, single-writer. The
genuinely hard part of any deployment is making the decision logic deterministic — `capture.py` lowers
that cost but does not remove it. See `OVERVIEW.md` for where the underlying discipline was developed.
