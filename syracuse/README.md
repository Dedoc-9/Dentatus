# syracuse — the Collatz map as `integrity ≠ truth`, made runnable

The 3n+1 / Syracuse map is the workbench's founding axiom compiled to a runnable example. Its step is pure
integer and fully deterministic — `T(n) = n/2` (n even) or `(3n+1)/2` (n odd, the compressed/accelerated
form) — so every trajectory `n → … → 1` is replayable bit-for-bit and content-addressable, with no float in
its identity. Yet whether *every* trajectory reaches 1 (the Collatz conjecture) is **unproven** — checked by
computer to enormous bounds, never proven in general.

That gap is `integrity ≠ truth`, literal rather than metaphorical:

- **Integrity (provable here):** *this* `n` reaches 1 in *exactly* `S` steps with peak `P` — verifiable on
  any machine, signable, replayable.
- **Truth (NOT provable here):** *all* `n` reach 1. This module is built to **refuse that claim
  structurally** — it signs trajectories, never the conjecture.

## Run it

```
PYTHONHASHSEED=0 python3 demo_syracuse.py          # verify · integrity≠truth · ration tie · lockstep tie
PYTHONHASHSEED=0 python3 tests/test_syracuse.py    # 15 unit tests
```

## The exact-gate / observable split

```
EXACT GATES (decide validity; folded into the orbit hash)   OBSERVABLES (descriptive; never gate)
─────────────────────────────────────────────────────       ──────────────────────────────────
start n ; the orbit sequence                                 peak / max-altitude
reached_one : bool                                           odd_steps / even_steps
stopping_time S : int                                        parity_word of the orbit
within_budget : S ≤ K   (the chosen cut)                     log_drift = odd·ln3 − S·ln2 ≈ −ln n  (float)
orbit_hash = state_hash(orbit)
```

Dual math / code:

```
math:  T(n) = n/2        if n even          code:  def step(n):
            = (3n+1)/2   if n odd                      return n//2 if n%2==0 else (3*n+1)//2
       S(n) = min{ t : Tᵗ(n) = 1 }                 def orbit(n, K):
       gate = [ S(n) ≤ K ]                              seq=[n]
       H    = SHA256(canon(orbit))                      while seq[-1]!=1:
                                                            if len(seq)>K: raise BudgetExceeded
                                                            seq.append(step(seq[-1]))
                                                        return seq
```

The budget `K` is an **admitted coarse-graining**: "terminates within `K`" is a chosen cut, not the
trajectory's inherent property. A budget breach means we have not spent enough steps to *know* the terminus
(`reached_one = None`), **not** a claim that one diverges.

### The ghost — the open conjecture as irreducible residual

`ConjectureWitness` accumulates *empirical* reach (`verified_count`, `max_verified_n`, `max_stopping_time`)
across seeds, and its `report()` **always** returns `conjecture_proven = False`. Raising `max_verified_n` is
integrity (more checked); it is never truth (the general case). The ghost here is the conjecture itself — the
gap between "all checked terminate" and "all terminate," which verifying more seeds never closes. The module
makes that refusal structural rather than a footnote.

## Ties into the workbench (the real value)

Collatz is the textbook "loop that looks like it might run forever," which makes it a genuine reference
workload, not a toy:

- **`ration/`** — `ration_counts(n)` maps an orbit's stopping time onto integer logical-step counts, so
  `ration.within_budget` refuses a long-orbit seed identically on any hardware (`n=703` blows an 80-step
  ceiling; `n=27` at 70 steps passes). The chaotic, unpredictable stopping time is the perfect adversarial
  input for the integer budget clamp.
- **`lockstep/`** — `as_truth_track(n)` turns each Collatz step into a content-addressed tick; the orbit
  becomes a replayable `TruthTrack` (n=27 → 70 ticks → 1, deterministic).
- **`chronicle/`** — record + sign a trajectory; an auditor replays `n → 1` and verifies the stopping time
  without trusting the producer.
- **`glitch/`** — reverse-Collatz generation (`1` upward via `n→2n`, `(n−1)/3`) is a structured, fully
  reproducible seed source for the state-space explorer — deterministic fixtures, never RNG.

## Honest bounds (stated, not hidden)

Collatz is **not** a cryptographic primitive: not a secure proof-of-work (no tunable difficulty, no preimage
resistance — a precomputed orbit replays trivially), not an RNG, not a hash. Claiming any of those would
break the project's bar. Its honest value is exactly two things: a **pure-integer, deterministic,
hard-to-predict / easy-to-verify reference workload** for `ration`/`lockstep`/`glitch`, and the **cleanest
concrete demonstration of `integrity ≠ truth`** in the workbench. It cannot, by construction, resolve the
conjecture — verifying more seeds raises `max_verified_n`, never proves the general case.

## Files

| File | Role |
|---|---|
| `orbit.py` | integer step/orbit, content-addressed `orbit_hash`, `gates` vs `observables`, `ConjectureWitness`, `ration_counts`, `as_truth_track` |
| `demo_syracuse.py` | verify (A) · integrity≠truth (B) · ration tie (C) · lockstep tie (D) |
| `tests/test_syracuse.py` | 15 unit tests (map, gates, ghost, ration tie, lockstep tie) |
