# elenchus — the reasoning-trace interrogator (footprints, not the mind)

Named for the Socratic *elenchus*, the cross-examination that tests a claim step by step. A producer — an
LLM or any agent — emits a **derivation**: premises plus a sequence of steps, each citing a **pinned exact
rule**. `elenchus` replays it, recomputes every step, and names the **exact failing step**. It is the third
and final child of the Axiom build order (`tessera` → `fuel` → `elenchus`), and it closes the circle: a
reasoning trace becomes a replayable, content-addressed `tessera` shard.

## Run it

```
PYTHONHASHSEED=0 python3 demo_elenchus.py            # valid · fabricated · skipped · unknown · proof
PYTHONHASHSEED=0 python3 tests/test_elenchus.py      # 11 unit tests
```

## What it checks (the form)

A step is `{rule, args, claim}`. The pinned ruleset is `premise · collatz · add · sub · mul · compare ·
transitivity` (all exact, integer/relational, no float). For each step in order:

- the rule must be in the pinned set — else **UNKNOWN_RULE**;
- the inputs it cites must already be established — else **GAP** (a skipped premise / missing prior step);
- re-applying the rule must reproduce the asserted `claim` — else **FABRICATED** (claim ≠ rule output);
- optionally, the declared conclusion must actually be derived — else **INCOMPLETE**.

The verdict names the precise step and reason (e.g. *"GAP: transitivity premise (a<b) or (b<c) not
established"* at step 3). The rules are inlined into `step_trace`, so any change to a rule changes the
source-bound ruleset hash — a verifier proves it ran the **same** rules.

### The verdict is itself a `tessera`

`step_trace` / `done` are a `tessera` rule with the trace in the seed, so `prove_trace` mints a real shard:
a stranger re-runs the interrogation and gets the identical verdict, trusting no producer. Tampering with
the trace, a step, or the claimed length is caught precisely.

## What it does **NOT** do (read this — the overclaim temptation is strongest here)

- **It does not read the model's mind.** It checks the *emitted* trace; a model can emit a faithful-looking
  trace it did not actually use. These are footprints, not cognition.
- **It is not a logic oracle and does not prove "valid reasoning."** It enforces exactly the *pinned* rules;
  it cannot judge whether those rules are the right logic, nor whether the conclusion is **true** in the
  world. integrity ≠ truth, applied to reasoning: a clean verdict means *"the stated steps follow the
  declared rules and replay,"* never *"the reasoning is sound."*
- **It does not solve the Halting Problem.** Like `fuel`, it *sidesteps* non-termination by bounding the
  trace to a finite step list; it does not predict halting.
- **It does not escape Gödel.** It never claims its own consistency — only that a given trace replays under
  the declared rules. The proof is *external* (a stranger replaying the shard), not self-referential.

## Where it sits

| sibling | role |
|---|---|
| `fuel` | proves the machine ran (exact bounded execution) |
| `tessera` | proves the log is real (offline replay) |
| `elenchus` | proves the trace **follows the declared rules** — and emits its verdict as a `tessera` |
| `assay` | the complementary layer: judges *quality* ("correct/fair/wise"), which `elenchus` deliberately does not |

## Files

| File | Role |
|---|---|
| `interrogate.py` | pinned ruleset (inlined into `step_trace`), `verify_trace`, fault localization, `prove_trace` / `verify_proof` |
| `demo_elenchus.py` | valid (A) · fabricated (B) · skipped/GAP (C) · unknown rule (D) · tessera proof (E) |
| `tests/test_elenchus.py` | 11 unit tests (valid, faults, proof) |
