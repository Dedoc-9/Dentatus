# Applications — downstream products built on the workbench

> **Not legal advice.** License-scope questions (what is a derivative, how AGPL applies across an API or
> network boundary) are fact-specific — see [`DUAL_LICENSE.md`](DUAL_LICENSE.md) and have an IP attorney
> review before relying on scope. This file declares the *intended* track per product; the authoritative
> text is the root [`LICENSE`](LICENSE) (AGPL-3.0) and each app's `NOTICE`.

These are **products**, not siblings. The Chronicle workbench is 2 frozen cores + 27 decoupled *siblings*
(counted, gated by `integration/preflight_check.py`). The five entries below sit *one level up*: each imports
the frozen cores read-only via the Sibling Law (a path shim) and composes the stack into something product-
shaped — but **none is a counted sibling and none is a deployed system.** They live at the repo root today
(no `applications/` folder yet — see *Tree note* below); this index is the legible boundary in the meantime.

## The boundary, stated once

```
cores (2, frozen)  +  siblings (27, counted, in preflight)        =  the workbench
applications (5, NOT counted, own tests, read-only imports)       =  downstream products
```

A component is a **sibling** only when its suite is in `integration/preflight_check.py` and the cores' tests
+ `parity_proof.py` still pass. An **application** is verified by its own tests and a pinned conformance
golden (run by `verify_all.py`), never by entering the suite count.

## The five products

| Application | What it is | Honest bound | License track | Evidence |
|---|---|---|---|---|
| [`aegis_gate/`](aegis_gate/) | a verifiable transfer & KYC agent over exact gates + `ration` + `quorum` + `tessera` | a **mock** bank — proves the audit trail, **not** that the decision was wise | AGPL-3.0 (Track A) | 14 tests + pinned golden |
| [`VeriSim/`](VeriSim/) | a verifiable simulation engine emitting a replayable proof shard | proves the **test was real** and replayable, not that the model matches reality | AGPL-3.0 (Track A) | 12 tests + pinned golden |
| [`VeriVerse/`](VeriVerse/) | a verifiable procedural world/physics-engine prototype (integer terrain, content-addressed chunks) | a **scaffold** competing on provable determinism, not render speed/fidelity | AGPL-3.0 (Track A) | 13 tests + pinned golden |
| [`AetherPulse/`](AetherPulse/) | a Stage-1 deterministic 3-D fixed-point engine kernel + cross-language conformance vectors | the deterministic **semantics**, not the 240fps performance engine; a native port must hash-match | AGPL-3.0 (Track A) | 15 tests + pinned golden |
| [`AetherManifold/`](AetherManifold/) | deterministic Riemannian optimization on the Stiefel manifold | proves a **trajectory** was computed exactly, not that the minimum is global | AGPL-3.0 (Track A) | 10 tests + pinned golden |

Every product carries a `NOTICE` declaring its track; `integration/license_audit.py` (run inside `verify_all.py`)
**fails the gate** if any product is missing a parseable license declaration — so "every product declares its
track" is a verified invariant, not a convention.

## License, in plain terms (not legal advice)

All five are **published modules** of Dentatus and therefore default to **AGPL-3.0 (Track A)** today — they
inherit it from the root `LICENSE` and `DUAL_LICENSE.md` ("the engine core and all published modules are
licensed under AGPL-3.0"), and now also state it explicitly in each `NOTICE`. As the **sole copyright holder**
(Daniel J. Dillberg), you are not bound by AGPL on your own code and may relicense any product on a different
track at any time; this index + the per-app `NOTICE` are the seam that makes such a change clean. A commercial,
closed-source **Track B** license is available per `DUAL_LICENSE.md` (contact `bigdilly95@gmail.com`).

Where the copyleft actually has teeth: the mock/scaffold products (`aegis_gate`, `VeriSim`, `VeriVerse`) are
demonstrations, so the network-copyleft is largely moot for them; the live ones are **AetherPulse** (a reusable
engine kernel) and **VeriVerse**, because those are what a third party would realistically build on.

## Tree note (deferred)

A physical `applications/` (or `children/`) folder is **deliberately not created yet.** The honest reason is
the project's own discipline: don't introduce a state transition unless it buys something real. Every app
resolves its imports via `ROOT = dirname(dirname(__file__))` (it assumes it sits one level below the repo
root), so a move would break every `_cores.py`/`_workbench.py` shim and require re-pinning the conformance
goldens — pure plumbing that changes **nothing** about licensing (AGPL scope is set by `LICENSE` + notices,
not by directory). If the visual separation is later judged worth the refactor, it is a *deliberate migration*
(relocate, fix every `ROOT`, re-pin, re-green the gate) — a Commit 2, not this one.
