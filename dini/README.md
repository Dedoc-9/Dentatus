# dini — a hyperbolic novelty compass (an agent's sense of direction)

A Sibling-Law component: it imports the frozen [`chronicle`](../chronicle/README.md) core read-only and
gives an LLM/autonomous agent a cheap scalar **sense of where it is** inside the space it is exploring.

Named for Ulisse Dini's surface (constant *negative* curvature). The real substance is **hyperbolic tree
embedding**: an execution/state DAG — every state keyed by its content hash — embeds into the Poincaré
disk with low distortion, because hyperbolic volume grows exponentially the way tree branching does
(Sarkar's construction; Nickel & Kiela's Poincaré embeddings). Stdlib-only (`math`, `cmath`) — no numpy.

## What it is — and the rails it runs on

For each state an agent reaches, the compass returns a **captured observable**:

| field | meaning |
|---|---|
| `dini_distance` | Poincaré distance of the state's embedding from the root — grows with depth/novelty |
| `depth` | exact integer tree depth (the un-fuzzy companion signal) |
| `novelty` | `True` the first time a content hash is seen |
| `coord` | `[x, y]` in the open unit disk |

It is a **sensor, not a gate**. `dini_distance` is a float (trig isn't bit-identical across machines), so
it is a **captured observable** — recorded as an input, replayed, **never** placed in the commit hash
(AGENTS.md §1/§4). A spike flags a *topological anomaly* that **correlates with** drift/aberrance; it does
**not** prove hallucination. Integrity ≠ truth: a novelty compass points, it doesn't guarantee.

## Run it

```bash
PYTHONHASHSEED=0 python3 demo_dini.py        # novelty compass / drift-anomaly / navigation / sealed loop
PYTHONHASHSEED=0 python3 tests/test_dini.py  # 9 tests
```

## Three ways an agent uses it (all read-only sensing)

1. **Novelty compass for autonomous fuzzing.** If `dini_distance` stays flat across steps, the agent is
   re-treading the happy path; if it grows, it is diving into new branches. The agent steers its next
   inputs to *increase* distance and reach untested coordinates — an organic curiosity driver.
2. **Drift / anomaly detection.** Because hyperbolic distance expands exponentially, an aberrant nested
   loop makes the distance from a stable baseline climb fast. Past an operator-**pinned** threshold the
   agent treats the path as topologically anomalous and may self-correct — *purge volatile context, roll
   back to the last stable state hash*. (A suggestion to halt, not a hard safety guarantee.)
3. **Compact navigation.** Hyperbolic geometry packs large trees into a small coordinate volume, so an
   agent can reason over `[x, y]` vectors of relative hierarchy instead of dumping raw directory maps into
   its context window.

## Agent-integration recipe (drop into a harness prompt)

> `dini/` is active, providing a `dini_distance` observable over the execution DAG (a **sensor**, not a
> rule). After every state transition: (1) read `dini_distance` from the captured ledger input; (2) keep
> it in context as a feedback variable; (3) if it **stalls**, mutate inputs to push into deeper/untested
> branches (raise the distance); (4) if it **spikes past the pinned threshold**, log a topological anomaly
> and roll back to the last stable state hash. Treat the number as an environmental reading — it guides
> exploration and self-correction, it does not authorize or forbid any action (the fail-closed gates live
> in `chronicle`/`guard_server`, never here).

## Files

| File | Role |
|---|---|
| `compass.py` | `HyperbolicMap` (streaming Poincaré-disk embedding of the state DAG), `poincare_distance`, `anomaly` |
| `demo_dini.py` | novelty compass, drift anomaly + rollback, navigation, chronicle-sealed agent loop |
| `tests/test_dini.py` | embedding, monotonic depth, novelty/revisit, branch separation, determinism, sealed loop |

## Honest scope

A reading, not a verdict. It does not make the agent safer or smarter; it gives it a *direction* to steer
by, and a number to notice when it has wandered. Pairs naturally with [`glitch/`](../glitch/README.md)
(embed its exploration DAG to see where the search spread vs. clustered). **Integrity is not truth.**


## Dual use & responsible use (note for security testers)

Be honest about what a novelty compass is: **direction-agnostic**. The exact loop that helps a defender's
fuzzer reach untested code — "if `dini_distance` stalls, push toward distant, unexplored branches" — is the
same loop that would help an **autonomous exploit crawler** or an **LLM-jailbreak search** map a target's
input/prompt space efficiently. The mathematics doesn't know whose side it's on. Flipped over, `dini/` is a
coverage baseline for offense as readily as for defense.

We state that openly instead of pretending otherwise, and we draw the line at *use*, not at the math:

- **Authorized testing only.** Use it for your own systems, or under an explicit engagement (defined scope,
  rules of engagement, written permission) — pentests, red-team exercises, defensive coverage, research.
  Pointing a `dini`-guided crawler at systems, models, or services you do not own or are not authorized to
  test may be illegal (e.g. computer-misuse / unauthorized-access law) and violate terms of service. That
  is a *you* decision with real legal weight; this note is not legal advice — get authorization and counsel.
- **No operational uplift here.** This module ships a coverage *sensor* and a navigation aid. It contains no
  exploit payloads, no jailbreak prompts, and no logic that targets safety filters or vulnerabilities; we
  won't add any. What you steer with the sensor is your responsibility.
- **The accountability cuts both ways — use it.** `dini` lives on a workbench whose whole point is the
  tamper-evident ledger. An *authorized* red-team run sealed through `chronicle` is itself auditable: every
  probe and path is recorded, signed, and replayable, which is exactly what a clean engagement report and a
  defensible scope boundary need. The honest move is to run offense *inside* that accountability, not around it.

**Integrity is not truth, and capability is not permission.** A compass that finds a path does not grant the
right to walk it.
