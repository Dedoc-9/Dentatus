```
================================================================================
        CHRONICLE WORKBENCH — SYSTEM CONTEXT & LLM / AGENT HANDOFF
================================================================================
```

**To any human or model editing this repository:** this is a high-assurance,
deterministic, content-addressed workbench ("Dentatus/Chronicle"). Code you add
is bound by the contract below. The boundaries are enforced by 78 tests across 7
suites and by the Replay Court / Parity Proof — violate them and the regression
suite fails. Equally binding is the *epistemic* rule: **never oversell what the
code protects.**

This file is the canonical handoff. For narrative depth see [`README.md`](README.md),
[`OVERVIEW.md`](OVERVIEW.md), and [`docs/LESSONS.md`](docs/LESSONS.md).

---

## 0. The one idea (read this first)

A tiny deterministic core — **canonical bytes → SHA-256 content hash** — plus one
discipline: **capture nondeterminism at the boundary; never fake it away.**
Everything else (replay court, signed verdicts, policy enforcement, quality
assay, hardware signing) is that idea wearing a different hat. If a change does
not reduce to those two things, it probably does not belong.

---

## 1. Determinism (reproducibility-by-construction)

- State logic must be a **pure function of its recorded inputs**. No raw
  `time.time()`, no `random`/`uuid`, no reliance on dict/set iteration order, no
  un-isolated network or disk reads inside the logic.
- Route every side-effect through a **capture seam** (`chronicle/capture.py`,
  `llm_toolkit/agent_capture.py`): at record time the effect runs and its result
  is captured *into the inputs*; at replay the captured value is replayed. Replay
  must never touch the live clock/model/network.
- Canonicalize floats explicitly via `format(x, ".12g")` so GPU/architecture
  float reassociation cannot fork a hash. **Caveat:** this is a *12-significant-
  digit floor* — carry money / high-precision values as integers or fixed-point,
  not floats.
- **Honest note on `PYTHONHASHSEED=0`:** it is a *discipline guard*, not a
  load-bearing dependency of the hashing. The content hashes use SHA-256 over
  `sort_keys` JSON and are **not** affected by Python's randomized `hash()`. The
  demos refuse to run without the flag on purpose (to enforce the reproducible-
  invocation habit), but do **not** add security controls that *key off* this
  env var — that is cargo-culting (see §5).
- `verify_determinism()` / `verify_replay_determinism()` are leak detectors: run
  the logic N times; if outputs differ, a side-effect escaped the seam. Use them.

## 2. Privilege isolation (out-of-process PEP)

- Do **not** write naked filesystem mutations or shell/exec calls from agent or
  generation logic. Every consequential or disk-writing action must request a
  signed authorization ticket from the out-of-process PEP
  ([`guard_server/isolated_pep.py`](guard_server/isolated_pep.py)).
- The PEP enforces a **directory allow-list clamp** (e.g. strictly under
  `~/projects/design/`), pre-resolving `..` traversal and symlink escapes via
  deepest-existing-ancestor `realpath` (fail-closed on anything unresolvable).
- Every verdict (`allow`/`deny`) is **bound to the SHA-256 of the exact action**
  and Ed25519-signed. The agent cannot alter a verdict, replay it for a different
  action, or forge an `allow` (it lacks the key). Denials append to a fsync'd
  append-only log.
- Run the PEP under a **separate OS user** from the agent for real separation;
  the code warns if it detects same-uid / root.
- **What this protects / does NOT:** bounded authority + tamper-evidence — *not*
  host tamper-proofness. On a single compromised host the same user can abuse the
  capture path; the PEP bounds *authority to act*, it does not make a compromised
  host honest.

## 3. Cognitive modesty — integrity ≠ truth

- Treat the generation layer (LLM) as **inherently untrusted and volatile.** Do
  not write wrappers that try to make the model "smarter" or soft-classify safety
  inside the prompt. Safety lives in **host-side, precommitted validity
  predicates at the ledger commit boundary**, not in the model's good intentions.
- If generated content violates a precommitted invariant, the state machine must
  **fail closed**: reject the commit, roll back, log. (`InvariantViolation`,
  `TransitionRefused`.)
- Every component proves a record is *unforged, exactly reproducible, and
  rule-faithful* — **never** that the decision was correct, fair, or wise.
  [`assay/`](assay/README.md) extends this one level up: it makes quality
  judgments recomputable (metrics) or attributable (signed opinions), but still
  does **not** certify truth. State the narrowest claim your mechanism supports.
- Trust boundaries verify against **pinned** keys held in config — never a key
  taken from the payload/inputs. (PEP trust anchor, `assay` assessor registry.)
  Verifying against an input-supplied key silently defeats the property.

## 4. Extractability, dependencies, and crypto tiers

- **Build for extraction, not just execution.** Keep modules decoupled. Core
  logic is **standard-library only**; `cryptography` is an *optional* enhancement
  (asymmetric attestation), never a hard import in a core path.
- **Sibling Law:** add capability as a NEW sibling component that imports the frozen cores read-only;
  never edit a core to add a feature. A new component is "in" only when its suite passes, it is in
  `integration/preflight_check.py`, and the cores' tests + `parity_proof.py` still pass. (See README -> *The Sibling Law*.)
- `chronicle/` and `llm_toolkit/` deliberately **vendor** their own copy of the
  primitives so each lifts out as a standalone repo. That duplication is
  intentional; [`integration/parity_proof.py`](integration/parity_proof.py) is
  the regression guard proving the copies are byte-identical. `guard_server/`,
  `integration/`, and `assay/` are *coupled* (import `llm_toolkit`).
- Signing is tiered and degrades **loudly, never silently**
  ([`chronicle/hardware_signing.py`](chronicle/hardware_signing.py)):
  - **Tier 1** `pkcs11-ecdsa-p256` — TPM 2.0 / YubiKey via `ctypes` PKCS#11; key
    never enters RAM. *(Implemented to PKCS#11 v2.40; not exercisable without a
    physical token.)*
  - **Tier 2** `ed25519-soft` — asymmetric; private key **AES-GCM encrypted at
    rest under a scrypt KEK**, in RAM only during the signing call.
  - **Tier 3** `hmac-scrypt` — stdlib-only, **symmetric** last resort. No
    third-party non-repudiation; the warning says so.
  scrypt's role is *key hardening* (at-rest encryption / derivation), never a
  "signing primitive."
- `sign()` returns a **hex string** (it must round-trip through the JSON ledger);
  raw bytes are not serializable. Match this convention in any new signer.
- `source_hash` (a.k.a. `ruleset_hash`) binds logic by its **exact source text**
  via `inspect.getsource`. This proves "the rules didn't change" — but it also
  means reformatting, renaming, or re-commenting a rule/guard function changes its
  hash and **invalidates prior attestations**. Treat recorded rule functions as
  frozen; version them deliberately.

---

## 5. Anti-patterns (these fail review)

- A security control that keys off `PYTHONHASHSEED` (it is a determinism guard).
- Verifying a signature against a public key taken from inputs instead of pinned config.
- A `cryptography` import in a core path with no stdlib fallback.
- Mutating files / running commands without a PEP-signed, action-bound ticket.
- Reading a clock / RNG / network inside state logic instead of via the capture seam.
- Claiming a record proves a decision is correct/fair/safe. It proves integrity, not truth.
- "Improving" determinism by hand-rolling crypto or collapsing the dual (coupled/uncoupled) representations.
- Reporting a change as *done* — or emitting any green/`[FOUNDRY]` status — without actually running
  `integration/preflight_check.py`. A status you did not earn by running is integrity-theater.

---

## 6. The verification contract

Before proposing a change as done, all suites must pass under the flag:

```bash
export CHRONICLE_SIGNER_PASSPHRASE=...        # for the Tier-2/3 signer tests
for t in chronicle/tests/test_chronicle.py chronicle/tests/test_hardware_signing.py \
         llm_toolkit/tests/test_llm_toolkit.py guard_server/tests/test_guard_server.py \
         guard_server/tests/test_isolated_pep.py integration/tests/test_integration.py \
         assay/tests/test_assay.py; do
  PYTHONHASHSEED=0 python3 "$t" || echo "FAIL: $t"
done
PYTHONHASHSEED=0 python3 integration/parity_proof.py   # must print: PARITY HOLDS
```

**Current verification state: 113 tests passing across 11 suites.**

| Suite | Tests | Guards |
|---|---|---|
| `chronicle/tests/test_chronicle.py` | 19 | chain, replay, rule-binding, fail-closed, Ed25519/HMAC, capture, store |
| `chronicle/tests/test_hardware_signing.py` | 5 | Tier-2/3 signer round-trip, at-rest encryption, drop-in recorder |
| `llm_toolkit/tests/test_llm_toolkit.py` | 18 | capture replay, guardrails, Ed25519 audit, HMAC fallback |
| `guard_server/tests/test_guard_server.py` | 10 | pinned policy, request-bound verdicts, tamper/forge |
| `guard_server/tests/test_isolated_pep.py` | 11 | path clamp, traversal/symlink escape, verdict binding, append-only log |
| `integration/tests/test_integration.py` | 5 | coupled stack, separation of powers, coupled/uncoupled parity |
| `assay/tests/test_assay.py` | 10 | recomputable metrics, attributed judgments, fudge/forgery |
| `manifold/tests/test_manifold.py` | 9 | topology->world_H, exact connectivity/bridge gate, captured λ₂ |
| `anti_cheat/tests/test_anti_cheat.py` | 9 | pinned visibility, occlusion gate, culling, replay/tamper |
| `glitch/tests/test_glitch.py` | 8 | state-space explore, content-hash dedup, shrink, seal+replay |
| `dini/tests/test_dini.py` | 9 | hyperbolic embedding sensor (captured observable, never a gate) |

### Definition of done

A change is not complete until **all three** hold — anything less is not "done":

1. `integration/preflight_check.py` prints `[FOUNDRY VERIFIED]` (it actually ran the 7 suites + parity).
2. A **Verification Record** is produced for review — the copy-paste template, run triggers, and reject
   criteria live in `README.md` -> *"Using this in a project"*. Hand a reviewer only **public** material
   (ledger + public key + hashes); never a private key or HMAC secret.
3. Any `ruleset_hash` / `policy_hash` / `guardrail_hash` that changed is a **deliberate, documented**
   version bump (editing rule/guard source invalidates prior attestations — see §4 `source_hash`).

Do not state "done" or paste a green status you did not earn by running the contract.

If your change breaks Replay Court, Parity Proof, or privilege separation, it is
wrong by definition here — fix the change, not the test.

---

## 7. Acknowledgement (machine-parseable)

```
ACK: deterministic-capture=enforced  privilege-pep=required  integrity!=truth=acknowledged
     stdlib-core=required  crypto=optional-tiered  parity=must-hold  fail-closed=required
     done=preflight-green+verification-record  status=earned-not-pasted
```

Proceed under these constraints.
