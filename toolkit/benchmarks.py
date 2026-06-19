"""
toolkit.benchmarks — three honest scenarios. Each can FAIL the toolkit; that is the point.

  informative  : signals are noisy views of truth        -> future_surface should WIN
  drift        : signals are pure noise                   -> future_surface should LOSE to the floor
  adversarial  : signals are confidently MISLEADING       -> future_surface should LOSE to the floor

The adversarial case is the README's first sentence:
    "This toolkit does not discover importance. It allocates resources according to supplied
     estimates of importance."
Quality of attention follows quality of signal. A method that cannot lose is not a measurement.

Deterministic: integer math, ties by id, stdlib only.   Run:  PYTHONHASHSEED=0 python3 -m toolkit
"""
from __future__ import annotations
import random

from .attention import attention


def make_world(n=60, seed=1):
    """Informative world. M (hidden truth) drives realized consequence; the observed signals are noisy
    views of it; magnitude is raw size (the butterfly: the biggest region is the most inert)."""
    rng = random.Random(seed)
    world = []
    for i in range(n):
        t_cons = rng.randint(1, 1000)
        t_unc  = rng.randint(1, 1000)
        M = max(1, (t_cons * t_unc) // 1000)
        size = max(1, 1000 - t_cons + rng.randint(-40, 40))
        world.append({
            "id": "region_%02d" % i,
            "cost": rng.randint(20, 100),                 # total demand ~3600 >> budget 1000: scarcity
            "consequence": max(1, t_cons + rng.randint(-80, 80)),
            "uncertainty": max(1, t_unc + rng.randint(-80, 80)),
            "possibility": rng.randint(300, 1000),
            "magnitude": size,
            "M": M,
        })
    return world


def make_drift_world(n=60, seed=1):
    """Estimate decoupled from truth: the observed signals are pure noise. future_surface must lose."""
    rng = random.Random(seed)
    world = []
    for i in range(n):
        t_cons = rng.randint(1, 1000)
        t_unc  = rng.randint(1, 1000)
        M = max(1, (t_cons * t_unc) // 1000)
        world.append({
            "id": "region_%02d" % i,
            "cost": rng.randint(20, 100),
            "consequence": rng.randint(1, 1000),
            "uncertainty": rng.randint(1, 1000),
            "possibility": rng.randint(1, 1000),
            "magnitude": max(1, 1000 - t_cons),
            "M": M,
        })
    return world


def make_adversarial_world(n=60, seed=1):
    """Confidently MISLEADING signals. High consequence/uncertainty/possibility is engineered to
    anti-correlate with true M: a loud `fake_crisis` (M=1) and a silent `quiet_cascade` (M=900),
    plus a population whose signal strength is inverse to its realized consequence. future_surface
    must lose to the floor — it cannot recover importance the signal actively hides."""
    rng = random.Random(seed)
    world = [
        {"id": "fake_crisis",   "cost": 50, "consequence": 1000, "uncertainty": 1000, "possibility": 1000,
         "magnitude": rng.randint(1, 1000), "M": 1},
        {"id": "quiet_cascade", "cost": 50, "consequence": 300,  "uncertainty": 300,  "possibility": 300,
         "magnitude": rng.randint(1, 1000), "M": 900},
    ]
    for i in range(n - 2):
        s = rng.randint(1, 1000)                            # signal strength
        world.append({
            "id": "region_%02d" % i,
            "cost": rng.randint(20, 100),
            "consequence": s,
            "uncertainty": s,
            "possibility": s,
            "magnitude": rng.randint(1, 1000),              # raw size: independent noise, not the oracle
            "M": max(1, 1000 - s + rng.randint(-50, 50)),   # the inversion: loud signal -> low consequence
        })
    return world


def grade(world, budget=1000):
    """Allocate `budget` by each policy and score every allocation on the hidden objective M."""
    field = attention.observe(world)                        # default scorer = future_surface
    return {p: field.allocate(budget, policy=p).captured("M")
            for p in ("future_surface", "magnitude", "uniform", "M")}   # M = oracle upper bound


def _pct(x, whole):
    return (100 * x) // max(1, whole)


def run(budget=1000):
    inf = grade(make_world(), budget)
    dft = grade(make_drift_world(), budget)
    adv = grade(make_adversarial_world(), budget)

    print("=" * 78)
    print("toolkit — deciding where limited resources go when you cannot attend to everything")
    print("=" * 78)
    print("\nthree scenarios, each graded on a hidden, independent objective M (% of oracle):\n")
    header = f"  {'scenario':12s}  {'future_surface':>14s}  {'magnitude':>10s}  {'floor':>7s}"
    print(header)
    for name, r in (("informative", inf), ("drift", dft), ("adversarial", adv)):
        o = r["M"]
        print(f"  {name:12s}  {_pct(r['future_surface'],o):13d}%  "
              f"{_pct(r['magnitude'],o):9d}%  {_pct(r['uniform'],o):6d}%")

    ratio = (100 * inf["future_surface"]) // max(1, inf["magnitude"])
    print("\nMEASURABLE IMPROVEMENT (informative world)")
    print(f"  uncertainty-aware allocation captured {ratio/100:.2f}x the realized consequence of")
    print(f"  size-based allocation at identical budget "
          f"({_pct(inf['future_surface'],inf['M'])}% vs {_pct(inf['magnitude'],inf['M'])}% of oracle).")

    print("\nTHE TOOLKIT CAN LOSE (this is the point — attention quality follows signal quality)")
    print(f"  drift       : signal is noise       -> future_surface {_pct(dft['future_surface'],dft['M'])}% "
          f"loses to floor {_pct(dft['uniform'],dft['M'])}%")
    print(f"  adversarial : signal is misleading  -> future_surface {_pct(adv['future_surface'],adv['M'])}% "
          f"loses to floor {_pct(adv['uniform'],adv['M'])}%")
    print("  => it does not DISCOVER importance; it ALLOCATES by supplied estimates of it.")

    # the claims, asserted — the file fails loudly if any stops being true
    assert inf["future_surface"] > inf["magnitude"], "informative: must beat size"
    assert inf["future_surface"] > inf["uniform"],   "informative: must beat the floor"
    assert dft["future_surface"] <= dft["uniform"],  "drift: a noisy estimate must not beat the floor"
    assert adv["future_surface"] <= adv["uniform"],  "adversarial: a misleading estimate must lose to floor"
    print("\n[OK] wins when the signal is good; loses when the signal is noise or misleading.")
    return {"informative": inf, "drift": dft, "adversarial": adv}


if __name__ == "__main__":
    run()
