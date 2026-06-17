# Related Work & Provenance

**chronicle claims no novel cryptography.** It is a small, deliberate *assembly* of well-established
techniques, applied to one problem (auditing consequential automated decisions). This file states what it
borrows and what — modestly — it puts together, so nothing here is mistaken for an invention.

## Techniques chronicle stands on

| Building block | Established prior art | Used in chronicle for |
|---|---|---|
| Hash-linked append-only log | Haber–Stornetta digital timestamping (1991); Merkle trees (1979); Certificate Transparency (RFC 6962); blockchain ledgers | the prev-hash chain that makes insert/delete/reorder detectable |
| Content addressing | Git object model; IPFS | identifying a decision by the hash of its full contents |
| Event sourcing / replay | Fowler's event sourcing; CQRS event logs | re-deriving outputs from recorded inputs instead of trusting stored outputs |
| Symmetric attestation | HMAC (RFC 2104) | zero-dependency tamper-evidence within one trust domain |
| Asymmetric signatures | Ed25519 (RFC 8032) via `cryptography`/libsodium | third-party verify-without-forge |
| Record-replay of side effects | VCR/"cassette" HTTP fixtures; golden-master testing | `capture.py` — turning clock/RNG/external reads into recorded inputs |
| Design-by-contract / fail-closed | Meyer's design by contract; assertion-based invariants | refusing to record a decision that breaches a precommitted invariant |
| Deterministic execution | reproducible-builds.org; deterministic serialization | float canonicalization, sorted encoding, `PYTHONHASHSEED=0` |

## What chronicle assembles (stated modestly)

The combination it offers is not a new primitive but a specific, small bundling for *decision auditing*:

- binding the **source hash of the decision logic + invariant** into every receipt, so an auditor can prove
  the rules that produced a record are the rules that ran ("rules-didn't-change"), and
- doing this **alongside** bit-exact replay and a fail-closed invariant gate, behind one
  backend-agnostic signer interface,
- in a dependency-light reference that runs on the standard library.

Each ingredient is old; the convenience is in having them together, honestly scoped, in ~600 lines.

## Explicit non-claims

- **Not new cryptography.** SHA-256, HMAC, and Ed25519 are used as specified; no custom primitives.
- **Not a blockchain / not consensus.** A single writer with a server-held secret (or one signing key) is
  the *opposite* of trustless distributed consensus. There is no network agreement, no proof-of-work/stake.
- **Not a novelty/IP filing.** Nothing here is asserted as patentable or proprietary over the prior art
  above. The contribution is engineering assembly and honest scoping, not invention.
- **Integrity ≠ truth.** Verification proves a record is unforged, reproducible, and rule-faithful — never
  that the underlying decision was correct or fair.

For the design history that led to these choices, see [`../docs/LESSONS.md`](../docs/LESSONS.md).
