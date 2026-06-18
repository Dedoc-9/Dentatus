# stasis — the boundary layer (the admission of reality)

The order zone (`fuel`, `tessera`, `quorum`) is exact by construction. The real world — cloud APIs, OS
randomness, GPU floats, network latency — is not. `stasis` does **not** try to make the cloud deterministic
(impossible) or eliminate latency (physics). It builds a strict, opinionated boundary so that whatever
crosses into the order zone is already canonical and integer-clean, and so that the messiness *outside* is
handled as a first-class, logged event rather than a crash. It is the hardening sibling: survival, not new
power.

## Run it

```
PYTHONHASHSEED=0 python3 demo_stasis.py            # iron canon · divergence ledger · lazy lattice
PYTHONHASHSEED=0 python3 tests/test_stasis.py      # 15 unit tests
```

## 1 · The Iron Canon (`canon.py`)

`canonicalize()` rejects the types that have no stable byte representation and normalizes the rest, so two
logically identical inputs always produce the identical SHA-256:

| rejected (CanonizationError) | why |
|---|---|
| `float` (by default) | floats must not enter a hash; pass `allow_float=True` only for explicitly captured, non-gated observables (and NaN/inf are still refused) |
| `set` / `frozenset` | no canonical order |
| raw `bytes` | ambiguous in a JSON canon — hex-encode to `str` first |
| non-string dict keys | key order/representation would be unstable |

It reuses the frozen `chronicle` canonical serializer (sorted keys, fixed number format) underneath.
**Honest bound:** identical bytes are guaranteed across OS / process / time *for the supported types*.
"Across languages" holds only if the other language implements the **same** canon spec — this module is the
spec for Python, not a guarantee by fiat.

## 2 · The Divergence Ledger (`drift.py`)

The naive contract "replay must match 100% or fail" is too fragile for a cloud LLM — float reassociation can
shift a logprob without changing any decision. But you cannot tell *noise* from a *lie* by staring at
differing bytes. `stasis` resolves it with the workbench's own spine, the **exact-gate / observable split**:

```
classify(expected, actual, gate_fields) ->
   gated field differs        -> FAIL  (LOGIC_ERROR)      the decision changed; not noise
   gates equal, observable    -> WARN  (OBSERVABLE_DRIFT)  decision unchanged; logged, fed to assay
     differs
   nothing differs            -> PASS
```

This distinguishes **malicious tampering** (wrong logic → `FAIL`, belongs in front of `elenchus`) from
**benign drift** (right decision, different bits → `WARN`, a quality signal). It never halts; it returns a
verdict. **Honest bound:** `OBSERVABLE_DRIFT` means *the gated decision is unchanged while some observable
differs* — it does **not** prove the cause was hardware (it proves the *decision* is identical, which is the
thing that matters, because observables never gate).

## 3 · The Lazy Lattice (`batch.py`)

Running a full `quorum` check per message kills throughput. `stasis` folds many shard hashes into one Merkle
root; the expensive consensus check runs on the **root**, and a single leaf is proven on demand with an
O(log M) inclusion proof when challenged. **Honest bound:** this is **optimistic / lazy** verification, not
free verification — you *trust the root until you challenge a leaf*; the total work of full verification is
unchanged, batching only defers and amortizes it. It is a simple Merkle tree (duplicate-last, no RFC-6962
domain separation) — a reference accumulator, not a hardened transparency log.

## Why it is the hardening child

| it protects | by |
|---|---|
| `fuel` | enforcing integer-clean inputs at the boundary — no float pollution reaches the VM |
| `elenchus` | distinguishing GPU drift from a lie, so the model isn't falsely accused of hallucination |
| `quorum` | batching, so high-security consensus is viable at high frequency |

## Files

| File | Role |
|---|---|
| `canon.py` | strict canonical bytes; rejects ambiguous/non-integer types (`CanonizationError`); `canon_hash`, `is_canonical` |
| `drift.py` | `classify` (gate vs observable → PASS/WARN/FAIL), `feed_assay` |
| `batch.py` | Merkle `merkle_root`, `inclusion_proof`, `verify_inclusion`, `batch_shard` (lazy verification) |
| `demo_stasis.py` | iron canon (A) · divergence ledger (B) · lazy lattice (C) |
| `tests/test_stasis.py` | 15 unit tests (canon, drift, batch) |
