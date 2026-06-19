# intervention — controlled uncertainty reduction (a causal query protocol)

The sibling after `coupling_discovery`. Observation tells you what **correlates**; intervention tells you what
**survives** when the world is deliberately perturbed under controlled rules. Its job is not to discover truth
— it is to spend bounded computation on the questions where the current model is weakest, and return
**admissible evidence**, never a graph edit. Same law as the rest of the stack, one rung higher:

```
causal_information → attention     ALLOWED
causal_information → proposal      ALLOWED
causal_information → experiment    ALLOWED   (airlock-authorized, shadow-only)
causal_information → truth         FORBIDDEN
```

## An intervention is a question, not a mutation

A persistent ghost yields a coupling candidate `(A, C)`. This module does **not** conclude *A causes C*. It
forms a question — *"if A is held constant for one controlled counterfactual, does C still diverge?"* — and the
airlock decides whether that question is legal, bounded, and admissible **before** any experiment runs:

```
ghost → coupling candidate → intervention REQUEST → airlock AUTHORIZE → shadow do()-experiment → evidence
```

`InterventionCandidate(source, target, hypothesis, expected_effect, allowed_scope, rollback_boundary, h)` is
admitted by `authorize()` only if `source ≠ target`, the scope is bounded, and the rollback boundary is valid.
An unauthorized request returns `UNAUTHORIZED` — never a silent run.

## The do-operator runs on a discarded shadow world

`experiment.do_run` deep-copies the state and forces `{node: value}` every step (Pearl's do-operator),
returning only a trajectory — **the input world is never written**. So the extended invariant

```
experiment cannot change committed history
```

is a property of the type, not a discipline. `causal_effect` runs two counterfactuals — `do(source=v₁)` and
`do(source=v₂)` — and measures how much the target's trajectory diverges between them: *vary the cause, watch
the effect.* `demo_intervention.py` proves it against AetherPulse — running **every** experiment in the
benchmark leaves the committed kernel hash trajectory byte-identical.

## The Causal Intervention Benchmark (`benchmark.py`)

Three worlds where observation gives the *same* signal (A and C move together) but intervention separates them:

```
world        structure     do(A)→C   do(C)→A   verdict
true         A → C         yes       no        CONFIRMED   directed evidence A→C
confounder   A ← X → C     no        no        REJECTED    C rides hidden X, not A
feedback     A ⇄ C         yes       yes       CYCLE       warning — never a stronger edge
```

Verdict `intervention-separates-cause-confounder-cycle`. The **confounder REJECTED** is the headline: it is the
exact case `coupling_discovery`'s persistence layer *cannot* resolve — A and C co-occur forever, yet holding A
constant leaves C untouched because both ride a hidden common cause. Only intervention sees it. The **CYCLE**
verdict is the safety case: a bidirectional dependency is flagged, never promoted to a stronger edge, because
cycles are where causal discovery becomes self-fulfilling.

## Natural experiments — real evidence from committed history (`natural_experiment.py`)

The shadow `do()` tests a counterfactual *of the model*. The one thing the shadow lacks is the real kernel's
actual transitions. `natural_experiment.mine(source, target, confounders, history)` scans committed history for
moments the world *happened* to supply a natural experiment — `source` varied while the named confounders
stayed stable — and asks whether `target` responded (instrumental-variable / quasi-experimental logic on real
data). Verdicts: `SUPPORTS`, `REFUTES`, `MIXED`, or `NONE` (the history never isolated the cause — untested, not
a false positive). No mutation, no alternate world, no fantasy counterfactual — pure observation. This is the
third evidence source feeding a `StructureProposal`'s held-out track record, and the only one drawn from
*reality* rather than the model. Law: `committed-history mining → evidence` ALLOWED; `→ committed reality`
FORBIDDEN.

## Evidence, not authority

A `CausalVerdict` carries an `evidence_delta` (+1 confirm / 0 cycle / −1 reject), updating the *weight of
evidence* for an existing proposal — promotion to a real edge still requires external review (`intent ≠
authority`). The model gains evidence; the territory (the committed hash trajectory) never moves. The whole
stack is now a **closed epistemic loop that is not self-modifying**: kernel → extractor → consequence →
causal_runtime → ghost → coupling candidate → intervention → better *model* — the map improves, the territory
is untouched.

## Run it

```
PYTHONHASHSEED=0 python3 benchmark.py             # the Causal Intervention Benchmark
PYTHONHASHSEED=0 python3 demo_intervention.py     # full chain + experiment ⊥ committed AetherPulse history
PYTHONHASHSEED=0 python3 natural_experiment.py    # quasi-experiments mined from committed history
PYTHONHASHSEED=0 python3 tests/test_intervention.py  # 17 unit tests
```

## Honest bound

Interventional evidence is exact **for the declared dynamics under which the do-operator is applied** — it
proves a counterfactual *of the model*, not a fact of nature (`integrity ≠ truth`). It resolves a confounder
the model contains; it cannot rule out a confounder the model has never represented. It allocates bounded
computation to the weakest part of the current map; it does not certify the map.

## Files

| File | Role |
|---|---|
| `protocol.py` | `InterventionCandidate`, `from_coupling`, the airlock `authorize()` gate |
| `experiment.py` | the shadow do-operator — `do_run` / `causal_effect` / `committed_unchanged` (input never mutated) |
| `query.py` | the four verdicts — `UNAUTHORIZED` / `REJECTED` / `CYCLE` / `CONFIRMED` + evidence delta |
| `benchmark.py` | the **Causal Intervention Benchmark** — true / confounder / feedback |
| `demo_intervention.py` | full chain + proof that experiments ⊥ committed AetherPulse history |
| `_wb.py` | path shim so demos/tests wire `coupling_discovery` + AetherPulse without core cross-imports |
| `natural_experiment.py` | mine committed history for quasi-experiments (SUPPORTS/REFUTES/NONE; pure read) |
| `tests/test_intervention.py` | 17 unit tests |
