# What we learned designing this kind of system — Dentatus → MCL_OBS2 → chronicle

A design retrospective. Not a changelog and not marketing: the transferable judgment behind a verifiable,
deterministic state machine, written so the *next* such system is built faster and with fewer illusions.
The active artifact this arc produced is [`../chronicle/`](../chronicle/README.md); the archived lineage
is under [`archive/`](archive/), and the de-inflated technical overview is [`../OVERVIEW.md`](../OVERVIEW.md).

## The arc in one paragraph

Dentatus began as an ambitious "Reality Engine" — a cellular-sheaf state machine dressed in physics
vocabulary (Citadel, manifold, Zeeman field, ghosts). A game was prototyped on top of it as a cheap test.
The test failed in the most useful way: it proved the system was **not** a renderer or a game engine but a
**verification / determinism backend**. The MCL_OBS2 observability discipline ("integrity is not truth")
then forced an honest accounting of what was real versus narrated. chronicle is the distillate — the
determinism-and-audit core, with the physics framing removed. Every lesson below is something the arc cost
us, restated as a principle.

## Lesson 1 — Let the artifact tell you what it is

We spent effort making the system look like a game because the vocabulary implied one. Playtesting
collapsed that: the 2D client was only ever a harness exercising the server, and the thing of value was the
content-addressed, replayable, attested state log underneath. **Principle:** name a system by what it can
*prove*, not by the metaphor it's wrapped in. The moment we renamed "Reality Engine" to "deterministic,
content-addressed state machine with a cryptographic audit trail," the right product (chronicle) became
obvious.

## Lesson 2 — Measure before optimizing; the bottleneck is never where the story says

A "better math" rewrite of the eigensolver was tempting and assumed. We built a frame-time profiler
*first*. It showed the real cost was redundant re-hashing of world state — roughly 75% of a tick — while
the linear algebra everyone wanted to optimize had ~7× headroom at working scale. The highest-value change
was "seal the hash once per tick," which is also a *correctness* improvement, not a micro-optimization.
**Principle:** an unprofiled optimization is a guess with extra steps. Profile, then optimize the thing the
profile names, even when it's boring.

## Lesson 3 — Run the experiment; never paste the result

Several speculative studies arrived with pre-written numbers. Running them disproved the numbers every
time:

```
claimed Hilbert-curve compression  30.92%   →  measured ~5%  (and NEGATIVE on adversarial data)
claimed Menger fractal porosity     40.62%   →  measured 37.57% on a faithful 3^4 grid
claimed "Klein bottle" boundary       ok     →  had a real topological involution bug
```

Each was corrected in the ledger with the measured value, and only the genuine win was kept (Hilbert block
locality ~13× tighter — real, and unrelated to the fabricated compression figure). **Principle:** a number
you did not measure is a liability, not an asset. The habit of *disproving your own claims* is the single
most credibility-bearing thing in the whole repo.

## Lesson 4 — Determinism is a property you can silently lose

A real bug: off-beat commits folded `time.time()` into a committed hash, so replay drifted across machines.

```
H_t = HASH(state ⊕ wall_clock)     # forks every run — NOT reproducible
H_t = HASH(state ⊕ tick_index)     # frame-derived — bit-identical on replay
```

The same class of hazard is float reassociation (GPU/SIMD reorder a sum, the hash forks) and unordered
iteration (Python's randomized `hash()` over sets/dicts). chronicle inherits all three defenses directly:
float **canonicalization** to a fixed decimal, **sorted** serialization, and a `demo` that **refuses to
run** without `PYTHONHASHSEED=0`. **Principle:** determinism leaks through clocks, floats, and iteration
order. Close those three doors explicitly or replay is a lie.

## Lesson 5 — Integrity is not truth (the MCL_OBS2 discipline)

The witness protocol's hard rule: *a chain hash certifies integrity, never truth.* The system was required
to refuse verdict-shaped outputs and to register a falsification condition before any experiment counted.
This is now chronicle's central honest boundary: it proves a decision is *unforged, exactly reproducible,
and rule-faithful* — it does **not** claim the decision was correct or fair. **Principle:** state the
narrowest claim your mechanism actually supports. Overclaiming what a hash means is how audit tools lose
the room.

## Lesson 6 — Precommit the rules, then fail closed

Invariants moved through a propose → human-license → enforce pipeline; nothing self-authorized. chronicle's
recorder refuses, at write time, to log a decision that breaches a precommitted invariant. **Principle:**
the time to decide what is forbidden is *before* the decision, and the safe failure mode is to not record
rather than to record-and-warn.

## Lesson 7 — Treat the repo as a workbench for purpose-built foundations

The most useful reframe of the whole arc: this was never one monolith to ship — it was a **workbench** on
which reusable, purpose-built foundations get forged, tested under load, and then lifted out as standalone
components. The clean-room seam made that literal: the engine core stayed frozen, and the game/test layers
were forbidden from importing engine internals, so each foundation matured behind a boundary instead of
fusing into the whole. That is exactly what let chronicle be *extracted* cleanly — it has **zero** imports
from the archived tree and depends only on the stdlib (plus optional `cryptography`). The same bench still
holds other forge-able foundations (the differential fuzzer, the chaos/arrival-order harness, the Ed25519
licensing airlock) that could be lifted out the same way. **Principle:** build for extraction, not just
execution. Keep each foundation decoupled enough to stand alone, and the workbench keeps yielding
purpose-built parts long after the original framing is retired. Coupling is the tax you would otherwise pay
at extraction time.

## What carried over, explicitly

| Lesson from the arc | Where it lives in chronicle |
|---|---|
| Content-addressing + replay | `core.py` state/committed hashing; `court.verify_chain` bit-exact replay |
| Determinism leaks (clock/float/order) | float canonicalization, sorted serialization, `PYTHONHASHSEED=0` guard |
| Capture nondeterminism instead of banning it | `capture.py` record-replay of clock/RNG/external reads |
| Integrity ≠ truth | the "what it does NOT claim" boundary in `README.md` |
| Precommit + fail closed | `Recorder` invariant gate (`InvariantViolation`) |
| Rules-didn't-change | source-hashed `ruleset_hash` bound into every receipt |
| Workbench → extractable foundation | chronicle lifts out with **zero** archived-tree imports |
| Honest provenance, no overclaim | [`../chronicle/RELATED_WORK.md`](../chronicle/RELATED_WORK.md) |

## The one durable takeaway

The most valuable output of this project was not a feature; it was a *method*: measure, prove, and state
the smallest true claim. The physics vocabulary was scaffolding. What remained standing once it was removed
— a small, deterministic, honestly-scoped verifier — is the part worth keeping.
