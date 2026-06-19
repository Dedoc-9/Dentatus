# toolkit — uncertainty-aware resource allocation

A deterministic toolkit for deciding where limited resources should go when you cannot attend to
everything.

> **This toolkit does not discover importance. It allocates resources according to supplied
> estimates of importance** — and it has a built-in way to prove itself wrong.

```python
from toolkit import attention

field  = attention.observe(world)
budget = field.allocate(resources=1000, policy="future_surface")
```

`world` is a list of items; each is a dict with a `cost` and the signals your scorer reads. The
default scorer is `future_surface = consequence * uncertainty * possibility`, but the policy is not
the identity of the toolkit — swap in any `item -> int`:

```python
from toolkit import attention

def my_scorer(item):
    return item["consequence"] * item["uncertainty"]

field  = attention.observe(world, scorer=my_scorer)
budget = field.allocate(resources=1000)              # ranks by the field's scorer by default
```

## The contract

```
score -> allocation
allocation != truth
```

A score is a *request for resources*, not a fact about the world (`attention != truth`); a reachable
option is not a probable one (`possibility != likelihood`). Every allocation is graded against a
hidden, independent objective `M` the scorer never sees — so a win can never be "the model says it
picked well because the model says so."

## Proof — `PYTHONHASHSEED=0 python3 -m toolkit`

Three scenarios, graded on the hidden `M` (% of the oracle upper bound):

| scenario    | future_surface | magnitude | floor | meaning |
|-------------|:--------------:|:---------:|:-----:|---------|
| informative | **95%**        | 27%       | 61%   | good signal — uncertainty-aware allocation captured **3.40×** the consequence of size-based allocation at identical budget |
| drift       | 46%            | 44%       | 63%   | signal is noise — **loses to the floor** |
| adversarial | 32%            | 75%       | 82%   | signal is confidently misleading (a loud `fake_crisis`, a silent `quiet_cascade`) — **loses to the floor** |

The drift and adversarial rows are the feature, not the bug: a method that cannot lose is not a
measurement. The quality of attention follows the quality of the signal.

## Layout

```
toolkit/
    __init__.py     the three-line front door
    attention.py    observe() -> Field -> allocate() -> Budget   (the surface)
    allocation.py   allocate() + captured()                      (the proven primitives)
    policies.py     future_surface / magnitude / uniform         (swappable scorers)
    benchmarks.py   informative / drift / adversarial worlds      (the falsifiable proof)
```

Deterministic across `PYTHONHASHSEED`; integer math; standard library only. The `allocate`/`captured`
primitives are identical to the ones in `causal_runtime/allocation.py`.
