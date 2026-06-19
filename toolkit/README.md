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

## Proof — `PYTHONHASHSEED=0 python3 -m toolkit`

Twelve asserted properties. Graded on the hidden `M` (% of the oracle upper bound):

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

The losing rows are the feature, not the bug: a method that cannot lose is not a measurement.

## Layout

```
toolkit/
    __init__.py     the smallest front door + the contract
    attention.py    observe() -> Field -> allocate() -> Budget, eligibility gate, tick()
    allocation.py   allocate() + captured()                      (the proven primitives)
    policies.py     future_surface / min_gate / weighted_product / magnitude / uniform
    benchmarks.py   twelve asserted properties across eight worlds
    tournament.py   compare(policies, worlds=N) -> ranked table (the competition harness)
```

Deterministic across `PYTHONHASHSEED`; integer math; standard library only. The `allocate`/`captured`
primitives are identical to the ones in `causal_runtime/allocation.py`.
