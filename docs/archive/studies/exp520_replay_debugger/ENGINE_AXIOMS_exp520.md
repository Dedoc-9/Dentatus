# EXP-520 — Replay / Time-Travel Debugger (Fork τ)

**Protocol** `exp520-v1` · **Declaration hash** `2e489550a816e08ee5d6ace0f4ac293fa059977c9109f15ee87e79604cbb2eb2`
**Scope** NO engine edits. `game/agency/replay.py` uses `dentatus.core` (`MuState`, `Claim`) +
`game.agency.injection`. Engine FROZEN. Closes the cold-restore gap left by EXP-518.

---

## A1 — History as event source

The world's past is reconstructable from two structures:
- **command log** — the deterministic inputs that drove each phase change
  `{seq, inputs:(β_Z, strain, vorticity, N_f, N_γ, mode), result_H, child_id}`,
- **sparse checkpoints** — a full `MuState` every `K` transitions (genesis at `seq 0`).

```
reconstruct(target H or seq):
    seq = h_index[H]                      # content-addressed lookup
    μ   = checkpoints[ max(c ≤ seq) ]     # nearest preceding checkpoint
    for cmd in commands[c .. seq):        # replay forward
        μ = inject(μ, active_leaf(μ), **cmd.inputs)
        assert μ.H == cmd.result_H        # VERIFY (not trust)
    return μ
```

The engine is functional (injection never mutates its input), so stepping from a checkpoint is safe and
reproduces the exact historical state (Fork A [3]).

## A2 — Verified, not trusted (the cryptographic core)

Replay does not *assume* determinism — it **proves** it. Each reconstructed step's engine `H_t` is
compared to the `H_t` recorded at capture; a match is cryptographic evidence that (a) the engine is
deterministic and (b) the history is un-tampered. A mismatch raises `ReplayMismatch` immediately. Fork
A [4] verifies the whole chain; Fork A [7] shows that corrupting a single recorded `H` is caught. This
is the property that makes "the past" a reproducible mathematical coordinate rather than a stored memory:
the coordinate is *checkable*.

## A3 — Cold restore (the EXP-518 bridge)

EXP-518's Skeleton Lineage gives O(1) undo within `N` steps and raises `BeyondWindowError` past it.
Fork τ turns that error into a **cold restore**: `cold_restore(time_machine, target_H)` reconstructs the
out-of-window state from the nearest checkpoint + replay (Fork A [8]). Because eviction is H-inert
(EXP-518 A2), the compacting world's `H` chain and the time machine's `H` chain are identical, so the
machine can restore any state the skeleton dropped. The three tiers compose:

| Tier | Reach | Cost |
|---|---|---|
| Skeleton (EXP-518) | last `N` transitions | O(1) |
| **Replay from checkpoint (EXP-520)** | **any transition** | **O(distance to checkpoint)** |
| Provenance DAG (EXP-516) | hashes/witnesses of all | lookup |

## A4 — P_yz & determinism

Command inputs (`β_Z, strain, vorticity`) are the same physical drive under reflection, and child ids
use material-eigenvalue payloads, so the command log and lineage are P_yz-invariant (Fork B). The engine
`H_t` chain is orientation-bearing, but each orientation is *internally consistent* — `verify_history`
passes for both. Reconstruction is bit-stable across runs (Fork A [10], Fork B [5]).

---

## DEV NOTE — Ghost #53: checkpoint cadence & the unbounded command log

1. **Cadence trade-off.** `checkpoint_every = K` trades memory for replay latency: large `K` stores
   fewer full states but replays more commands to reach a target (the "warm tail"); small `K` is faster
   to restore but heavier. Reconstruction cost is `O(distance to nearest checkpoint)`, bounded by `K`.
   `K` is a per-deployment knob — it changes no observable, only restore latency, so it is not
   constitutional (consistent with EXP-518's `N`).

2. **The command log is the unbounded tier.** Checkpoints amortise replay but the command log itself
   grows `O(#transitions)` — it must persist every input to remain replayable. It is small (a handful
   of scalars per transition) and is the *minimal* unbounded state: strictly less than storing every
   `μ`. Memory hierarchy: skeleton (hot, bounded) ⊂ checkpoints (warm, sparse) ⊂ command log + DAG
   (cold, unbounded but minimal). A future refinement (Fork ω) caps replay by guaranteeing a checkpoint
   within `K` of every state and pruning command segments older than the last durable checkpoint.

3. **Replay as a determinism monitor.** `verify_history` is not only a reconstruction tool — run
   periodically it is a **continuous integrity check**: any platform-level non-determinism
   (floating-point drift, an unpinned `PYTHONHASHSEED`, a smuggled engine mutation) surfaces as a
   `ReplayMismatch`. The residual between "claimed deterministic" and "proven deterministic" is closed
   by making replay verifiable.

## Suggested improvements / forks

- **Fork ω (checkpoint cadence + log pruning).** Guarantee a checkpoint within `K` of every reachable
  state and prune command segments behind the last durable checkpoint — bounds replay cost and trims
  the cold tier.
- **Fork ϙ (branch / counterfactual replay).** Reconstruct a historical `μ`, inject a *different*
  command, and fork a counterfactual lineage — "what if this seam had not sheared?" — as a sibling DAG
  branch with its own verified `H` chain.
- **Fork ϛ (dashboard scrubber → reconstruct).** Wire the EXP-519 scrubber to `reconstruct(H)` so
  dragging the timeline rebuilds the actual `μ` (and its true Fiedler fault / material), not just cached
  frames.

## Foreign-language note (rhetoric → code)

The history is *ereignisbasiert* (event-sourced): a *Befehlsprotokoll* (command log) plus
*Kontrollpunkte* (checkpoints) allow *Wiederherstellung* (reconstruction) of any *μ*. The replay is
*überprüft, nicht vertraut* (verified, not trusted): each `H_t` is *abgeglichen* (matched) against its
*Quittung* (receipt). The *Vergangenheit* (past) becomes a *reproduzierbare Koordinate* (reproducible
coordinate); `BeyondWindowError` becomes a *Kaltstart-Wiederherstellung* (cold restore).
