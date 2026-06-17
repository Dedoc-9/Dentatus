# lockstep — what becomes truth at frame rates

A deterministic **reconciliation core** for real-time 2D/3D simulation: it decouples *what becomes truth*
from *what gets shown*, so a game can present at 1440p/240fps while its authoritative state advances as an
exact, content-addressed, integer tick stream. It is the exact-gate / captured-observable split applied to
a frame loop.

> **Honest bound, up front.** This is the scheduler + integer-exact interpolation/rollback math — **not a
> GPU renderer.** It produces the verifiable authoritative stream a real engine's render thread *consumes*;
> it does not push pixels at 1440p/240Hz (Python/stdlib can't, and claiming otherwise would be false).
> Integrity is not truth: it proves the tick stream is exact and replayable, not that the simulation models
> anything real.

## The tension it resolves

The workbench's truth is **exact, integer, content-addressed**. A 240fps render is **float, GPU, lossy,
fast**. They cannot be the same stream. `lockstep` separates them:

| | rate | arithmetic | status |
|---|---|---|---|
| **truth** (`tick.py`) | e.g. 120 Hz | integer fixed-point | **gated** — `H_n = state_hash({tick:n, state})` |
| **render** (`interp.py`) | e.g. 240 fps | integer-exact lerp | **observed** — interpolated, never in a truth hash |

Truth advances in abstract **integer tick indices**, so 120 Hz vs 240 fps is exact rational arithmetic — no
microsecond rounding ever enters. A render frame `f` maps to tick-time `f·T/R = n + rem/den`, and its shown
position is an **integer** lerp `x_n + (x_{n+1}−x_n)·rem // den`. The observable is bit-exact yet explicitly
excluded from the truth hash, so a divergence in *presentation* can never masquerade as a divergence in
*truth*.

## Run it

```
PYTHONHASHSEED=0 python3 demo_lockstep.py          # truth ticks, render observables, rollback
PYTHONHASHSEED=0 python3 tests/test_lockstep.py    # 13 unit tests
```

## Three ideas, each from a project constraint

**Decoupled truth-rate / frame-rate.** `TruthTrack` advances the integer sim one tick at a time and
content-addresses each tick. At 240 fps over 120 Hz truth there are exactly 2 render frames per tick, with
`α ∈ {0, 1/2}` — the demo shows positions `0.0, 0.5, 1.0, 1.5, …` interpolated exactly, none of which exist
in any tick hash.

**Rollback = "revert to the last valid hashed state."** A client predicts remote inputs to render *now*
instead of waiting a round-trip. When the authoritative inputs arrive and differ, it reverts to the last
tick whose hash still matches authority and **re-simulates** forward. Because the sim is deterministic
integer logic, the re-sim is exact, so two clients on different hardware converge to identical tick hashes
(the demo and `test_clients_converge_after_rollback` prove it). This is GGPO-style netcode expressed as the
workbench's own revert-to-last-valid-hash rule.

**The tick boundary is an admitted coarse-graining.** Truth is defined *only* at integer ticks; a sub-tick
render position is an interpolated observable with no truth-status. Events "between ticks" are model
constructs of the scheduler, not inherent limits — the frame is a presentation artifact, the tick is the
chosen discretization.

### Dev note — the rollback ghost, and no backreaction

The residual between the *predicted* track and the *corrected* track is the mispredict — bounded by
`rollback_depth`, recorded, and absorbed by reverting, never committed. It is the direct analogue of
`quorum`'s dissent ghost: a divergence the system tracks and resolves, not a truth it asserts. A
persistently large `rollback_depth` (EMA-able like quorum's `S_t`) is an early signal of bad prediction or
an out-of-sync peer — a sensor, not a gate. And **no backreaction**: an interpolated render position must
never flow back into the integer sim; the observable cannot perturb the gated state.

## Observables (captured, never gated)

```
frames_per_tick  = render_rate / truth_rate        # 240/120 = 2
alpha            = rem / den ∈ [0,1)               # sub-tick render phase
rollback_depth   = current_tick − last_valid_tick  # cost of a correction
changed          = corrected final hash != predicted final hash
```

## Honest bounds

Deterministic convergence holds **only** if the sim is pure integer logic and all clients share the genesis
state + step function. A non-deterministic step (float drift, un-captured clock/RNG) breaks the guarantee —
route such reads through chronicle's capture seam first. `interp.py` does **interpolation only**; it refuses
to silently **extrapolate** (inventing truth past the last simulated tick). Rollback assumes inputs are
eventually authoritatively known; it does not invent missing inputs. And, again: this is the reconciliation
core, not a renderer.

## Where it sits in the workbench

| sibling | role here |
|---|---|
| `chronicle` | replays any contested tick bit-for-bit from the recorded inputs |
| `anti_cheat` | server-authoritative ticks; `lockstep` is the rate/rollback layer beneath it |
| `quorum` | *what becomes truth across witnesses*; `lockstep` is *what becomes truth across frames* on one node |
| game-layer `multivelocity` | per-section co-moving frames consume the decoupled tick stream |

## Files

| File | Role |
|---|---|
| `tick.py` | integer fixed-timestep `TruthTrack`; content-addressed tick hashes; the canonical `kinematic_step` sim |
| `interp.py` | deterministic integer render interpolation as observables; interpolation-only (no silent extrapolation) |
| `rollback.py` | revert-to-last-valid-hash reconciliation; `first_input_divergence`, `last_valid_tick`, `reconcile` |
| `demo_lockstep.py` | truth ticks (A) + render observables (B) + rollback convergence (C) |
| `tests/test_lockstep.py` | 13 unit tests (tick, interp, rollback) |
