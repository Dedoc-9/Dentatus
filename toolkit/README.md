# toolkit — uncertainty-aware resource allocation

A deterministic toolkit for deciding where limited resources should go when you cannot attend to
everything.

> **This toolkit does not determine what matters. It assumes a signal exists and tests whether that
> signal is a better allocator than simpler policies under constrained budgets** — and it has a
> built-in way to prove itself wrong.

```python
from toolkit import attention

budget = attention.allocate(world, resources=1000)      # smallest path; you never name the metric
```

`world` is a list of items; each is a dict with a `cost` and the signals your scorer reads. The
default scorer is `future_surface = consequence * uncertainty * possibility`, but the policy is not
the identity of the toolkit — swap in any `item -> int`:

```python
from toolkit import attention, min_gate

field  = attention.observe(world, scorer=min_gate)      # "a weak dimension caps attention"
budget = field.allocate(resources=1000)
```

Or run a competition — which policy allocates best under stated conditions?

```python
from toolkit import compare, future_surface, magnitude, random_priority

print(compare([future_surface, magnitude, random_priority], worlds=1000).table())

# or a policy x regime matrix: where does each policy win and lose?
from toolkit import robustness
print(robustness([future_surface, magnitude, random_priority]).table())

# certify a policy: assumptions, honesty checks, and its known failure envelope
from toolkit import certify
print(certify(future_surface).report())

# a certificate is a first-class artifact -- serialize, store, and regression-check it
from toolkit import diff_certificates, weighted_product
old, new = certify(future_surface), certify(weighted_product)
print(diff_certificates(old, new).report())   # judged by envelope + integrity, never score alone

# provenance: why did an item get budget? (observable signals only, never the hidden objective)
budget = attention.allocate(world, resources=1000)
print(budget.explain("region_07"))
```

## The contract

```
score -> allocation
allocation != truth
```

A score is a *request for resources*, not a fact about the world. Every allocation is graded against
a hidden, independent objective `M` the scorer never sees, so a win can never be "the model says it
picked well because the model says so."

## Bounds (the doors this toolkit keeps shut)

| bound | meaning | enforced by |
|---|---|---|
| `attention != truth` | a high score is a claim on budget, not a fact | grading on independent `M` |
| `attention != discovery` | it finds importance only where the signal encodes it | unknown-unknown benchmark |
| `possibility != likelihood` | a reachable option is not a probable one | scorer is an estimate, swappable |
| `importance != eligibility` | a top score never buys budget an item is not entitled to | eligibility gate |
| coherence time | a fixed allocation has a finite useful horizon | coherence benchmark + `Field.tick()` |
| `attention -> explanation` ALLOWED, `-> hidden justification` FORBIDDEN | every claim on a policy's label is a runnable check | `certify()` |
| `observable drift != semantic drift` | a monitor sees marginals, not the signal->outcome map | `Monitor` blind-spot |
| forbidden channels | the score must be invariant to M / future / hidden / private state | anti-oracle suite in `certify()` |
| `attention should have provenance` | every decision cites observable signals, never truth | `Budget.reason()` / `.explain()` |
| `test_quality != test_count` | a suite that cannot notice a broken allocator is one test | `mutate()` mutation testing |
| `confidence != memory` | a certificate is trustworthy only if it reproduces | `replay()` |
| `importance != selection` | a thing can matter and still lose to a finite budget | counterfactual provenance |
| `allowed input != allowed information` | a permitted channel can encode a forbidden variable | `leakage()` |

## Commands

```
python3 -m toolkit              # the full proof (forty-four asserted properties)
python3 -m toolkit tournament  # compare() + robustness() tables
python3 -m toolkit certify     # certificate for future_surface
python3 -m toolkit evaluate    # full allocator report (onboard any policy)
python3 -m toolkit manifest    # portable Allocation Manifest (JSON evidence boundary)
```

## Proof — `PYTHONHASHSEED=0 python3 -m toolkit`

Forty-four asserted properties. Graded on the hidden `M` (% of the oracle upper bound):

**[1] Signal quality.**

| scenario    | future_surface | magnitude | floor | |
|-------------|:--------------:|:---------:|:-----:|---|
| informative | **95%**        | 27%       | 61%   | good signal — **3.40×** the consequence of size-based allocation at identical budget |
| drift       | 46%            | 44%       | 63%   | signal is noise — **loses to the floor** |
| adversarial | 32%            | 75%       | 82%   | signal is confidently misleading — **loses to the floor** |

**[2] `attention != discovery`.** A low-consequence / high-`M` category is found *only* if
uncertainty/possibility encode it: encoded → future_surface 88% vs floor 72% (found); uninformative
signal → 60% vs floor 88% (**not** discovered). The toolkit does not find importance by magic.

**[3] Calibration (aggregation is load-bearing).** Product-structured `M`: product 95% ≥ min_gate
92%. Min-structured `M`: min_gate 99% ≥ product 93%. No single aggregation is universal; the right
one depends on how importance composes.

**[4] Budget curve.** Sweeping scarcity, future_surface dominates magnitude at every budget, and the
advantage is largest under scarcity and shrinks toward abundance (fs 83→99%, mag 17→60% as budget
100→3000). The claim is "better under *constrained* resources," made precise.

**[5] Coherence time.** An allocation decided at `t=0`, graded as the world drifts: 97% → 68% → 14%
→ 11% over 5 ticks, falling below a fresh floor (~57%) by `t=3`. Attention has a finite horizon.

**[6] `importance != eligibility`.** A top-`future_surface` but ineligible item (`eligible=False`)
receives **zero** budget.

**[7] Policy competition.** Run every policy over 1000 worlds, same budget, same hidden `M`, ranked
by average capture (% of oracle):

```
policy                 avg captured M (% of oracle, 1000 worlds)
  oracle               100%
  future_surface        95%
  min_gate              93%
  random_priority       59%
  magnitude             33%
```

Note `magnitude` (33%) ranks *below* `random` (59%): in a butterfly world "spend on the biggest" is
anti-informative, worse than chance. The toolkit never asks "is future_surface true?" — only "does
this policy out-allocate the alternatives under these conditions?"

**[8] Policy robustness.** The same experiment across four regimes — a policy survives only where its
assumptions hold:

```
policy                   clean       noisy   adversarial       stale
  oracle                  100%        100%        100%        100%
  future_surface           96%         52%         21%         11%
  magnitude                33%         32%         67%         43%
  random_priority          58%         59%         70%         43%
```

`future_surface` dominates the clean regime and **collapses** under noise, misleading signal, and
staleness — where `magnitude` and even `random` overtake it. The result is not "future_surface is
best"; it is "future_surface wins when its assumptions hold, and loses when they do not."

**[9] Allocator certification.** Treat a policy like any engineering primitive: make it declare its
assumptions, failure modes, and evidence. `certify(policy)` emits a safety label:

```
Policy: future_surface
Certified:
  [x] deterministic
  [x] does not use the hidden objective M
  [x] respects eligibility (importance != eligibility)
Operating envelope (beats the random floor):
  + clean         96% vs random 58%
Known failure envelope (does not beat random):
  - noisy         52% vs random 59%
  - adversarial   21% vs random 70%
  - stale         11% vs random 43%
Verdict: CERTIFIED as an allocator (with the failure envelope above)
```

The honesty checks are runnable, not assurances: a policy that reads `item["M"]` (the graded
objective) **fails** the *no hidden objective* check automatically — the certifier catches a cheater.

**[10] Certificate regression.** A certificate is a first-class artifact (`to_dict()` / `to_json()`),
so a change to a policy is reviewed as a diff, not a score bump. The gate rejects a higher-scoring
change if it regressed integrity:

```
future_surface  ->  _oracle (reads item["M"])
  adversarial  +79%
  clean         +4%
  noisy        +48%
  stale        +88%
integrity changes: no_hidden True->False
Acceptance: REJECTED -- integrity regression (a higher score does not buy it back)
```

The oracle scores higher in *every* regime and is still rejected. A change is accepted because its
envelope moved in an understood way, never because the number went up. And the certificate's scope is
fixed in the artifact itself — *"certified under the tested regimes with the declared assumptions;
never a claim of correctness."*

**[11] Runtime drift monitor.** A certificate has to keep being earned after deployment. `Monitor`
tracks how far the live input has moved from the certified distribution and reports a lifecycle status
— `CERTIFIED -> DEGRADED -> QUARANTINED` (outside its evidence boundary, not "wrong"):

```
clean input stream      -> status=CERTIFIED    drift_ema=55
shifting input domain   -> status=QUARANTINED  drift_ema=510
adversarial stream      -> status=CERTIFIED    drift_ema=56   (BLIND SPOT)
```

The blind spot is the honest part: a distribution monitor sees the **marginals** of the signals, not
the signal->outcome relationship, so it catches a new input domain but is invisible to a confidently
misleading world. `observable drift != semantic drift`. The certificate artifact carries this in its
`expires_if` field (input shift / policy change / new hidden variable).

**[12] Anti-oracle suite + provenance.** Two halves of one boundary — *forbid reading reality, then
prove the decision used only what was allowed.* `certify(policy, forbidden=(...))` requires the score
to be invariant to every forbidden channel (`M`, `future_state`, `hidden`, `private`); a policy whose
score moves when a forbidden channel moves is caught:

```
future_surface forbidden-channels read: none
reads_hidden   forbidden-channels read: ['hidden']
```

And `Budget.reason(id)` / `.explain(id)` gives auditable provenance that cites observable signals only:

```
allocation_reason: region_00
  signals (observable only): consequence=583  uncertainty=868  possibility=822  cost=37  magnitude=783
  future_surface = 415   rank #1 of 20   outranked 18
  funded: True   eligible: True
  not read (forbidden): M, future_state, hidden, private
```

The proof asserts the trace never cites `M` and always declares it unread. Provenance is *allowed*
(every decision is explainable); hidden justification is *forbidden* (the explanation can only name
what the policy was permitted to see).

**[13] Mutation testing.** Turn the scrutiny on the suite itself: deliberately break the policy and
check the harness *notices*.

```
drop_uncertainty     detected=True   clean score dropped 18%
invert_possibility   detected=False  NOT detected -- degradation invisible to the suite
cost_only            detected=True   lost the clean operating envelope
constant             detected=True   clean score dropped 29%
reads_hidden         detected=True   reads a forbidden channel (integrity)
```

It catches 4 of 5 — and is honest about the miss: inverting `possibility` is invisible *because that
signal carried no information in the clean world*, so breaking it changes nothing. `test_quality !=
test_count`: a suite that cannot notice a broken allocator is one test, however many it runs.

**[14] Certificate replay.** A certificate is trustworthy only if it reproduces — `confidence !=
memory`. `replay(policy, certificate)` re-derives the evidence and checks it matches:

```
replay(future_surface, its own certificate)            -> reproduced=True
replay(weighted_product, future_surface's certificate) -> reproduced=False (mismatch: wins, fails)
```

A certificate that no longer matches its policy is caught — the policy has drifted from the evidence
that vouches for it.

**[15] Counterfactual provenance + leakage.** Provenance also answers *why not*: an eligible item
left out under a tight budget reports what would change it — `region_00 not funded; would enter if
budget +576` (`importance != selection`: a thing can matter and still lose to finite resources). And
`leakage(world, observable, forbidden)` catches a permitted channel that secretly encodes a forbidden
one — proxy `995` vs independent `71` (`allowed input != allowed information`).

**[16] External allocator onboarding.** The milestone: a stranger's policy, judged without the
author's help. `evaluate(policy)` composes the whole harness into one report:

```
Allocator Report: future_surface
  Verdict:            CERTIFIED
  Operating envelope: clean
  Failure envelope:   noisy, adversarial, stale
  Forbidden access:   PASS
  Replay:             PASS
  Suite strength:     4/5 mutations detected (test_quality != test_count)
  Scope:              certified under tested regimes; never a claim of correctness
```

A policy that reads a forbidden channel comes back `NOT CERTIFIED, forbidden_access=FAIL`. The toolkit
is a **judge, not an optimizer**: it reports where a system should be trusted; it never modifies the
policy or proposes a "better" one — that would turn an attention engine into a truth engine.

**[17] Allocation Manifest.** The portable freezing artifact: a policy ships with a self-describing
evidence boundary, so the downstream question becomes *"does this manifest match my environment?"*
rather than *"do I trust it?"*

```
Allocation Manifest: future_surface v1.0   [CERTIFIED]
  does:     rank observed items under a fixed budget
  does not: discover truth; read hidden state; predict causality
  signals:  consequence, uncertainty, possibility
  tested:   regimes=[clean, noisy, adversarial, stale]  mutations_detected=4/5
  forbidden:M, future_state, hidden, private  (clean=True)
  replay:   PASS
  scope:    certified under the tested regimes; never a claim of correctness
```

The `signals` are *detected*, not declared by the author (each observable is perturbed to see if the
score responds). `manifest.matches(world)` is the executable form of the question — it accepts a
fitting world and rejects one missing a declared signal (`signals_present=False missing=['possibility']`).

The losing rows are the feature, not the bug: a method that cannot lose is not a measurement.

## Layout

```
toolkit/
    __init__.py     the smallest front door + the contract
    attention.py    observe() -> Field -> allocate() -> Budget, eligibility gate, tick()
    allocation.py   allocate() + captured()                      (the proven primitives)
    policies.py     future_surface / min_gate / weighted_product / magnitude / uniform
    benchmarks.py   eighteen asserted properties across nine worlds
    tournament.py   compare() ranked table + robustness() policy x regime matrix
    certify.py      certify(policy) -> safety label + to_json() + diff_certificates()
    monitor.py      Monitor.observe(world) -> CERTIFIED/DEGRADED/QUARANTINED (runtime drift)
    mutate.py       mutate() -> can the suite notice a degraded allocator? (+ replay/leakage in certify.py)
    evaluate.py     evaluate(policy) -> one-page Allocator Report (onboard a stranger's policy)
    manifest.py     manifest(policy) -> portable Allocation Manifest + matches(world)
```

## Dev note — the `!=` family

The whole project keeps converging on one shape: a statement of the form *X is not Y*, where Y is the
easy claim it would be convenient to collapse X into. Every module enforces one of these. Read top to
bottom it is the spine of the toolkit:

```
score            != truth          a number is a request for resources, not a fact
attention        != truth          allocating effort somewhere is not a claim it matters
attention        != discovery      the field finds importance only where the signal encodes it
possibility      != likelihood     a reachable option is not a probable one
importance       != eligibility    a top score never buys budget an item is not entitled to
importance       != selection      a thing can matter and still lose to a finite budget
observable drift != semantic drift a monitor sees marginals, not the signal->outcome map
allowed input    != allowed information   a permitted channel can still encode a forbidden one
test_quality     != test_count     a suite that cannot notice a broken allocator is one test
confidence       != memory         a certificate is trustworthy only if it reproduces
```

It inherits the same move from the wider project (`prediction != causation`, `proposal != authority`,
`integrity != truth`). The one equality the toolkit *does* assert is the contract: `score -> allocation`.
Everything else is a refusal. The toolkit becomes more useful by refusing to become a truth engine:

```
The system may decide where to look.
It may never decide what reality is.
```

## Honest scope — what this is and is not

Two clarifications that keep the claims falsifiable:

1. **Integrity ⊥ utility is the only irreducible split.** The lenses are not all mutually orthogonal
   (drift and coherence are both temporal; leakage and the anti-oracle suite are both information-access).
   The one separation the code actually *proves* is two-way: **integrity** (invariance on forbidden axes)
   versus **utility** (regime performance). The regression gate is the proof — a policy that scores
   higher in every regime is still rejected if it reads a forbidden channel. A high enough score never
   buys back lost integrity; that is why the two cannot collapse into one number.

2. **Every result is conditional on the world generator.** `make_min_world` exists *so that* `min_gate`
   wins; `make_adversarial_world` is built *so that* `future_surface` loses. These are constructed
   stress tests, not facts about attention in general. The honest reading is: *a framework for
   stress-testing allocation policies under explicitly constructed observability constraints* — never a
   general epistemic engine. `manifest.matches(world)` is the in-code form of this caveat: a certificate
   is valid only where the environment supplies the coordinates it was tested on. The undecidable part —
   whether the chosen `M` is the *right* notion of importance — is a parameter, not a result.


Deterministic across `PYTHONHASHSEED`; integer math; standard library only. The `allocate`/`captured`
primitives are identical to the ones in `causal_runtime/allocation.py`.
