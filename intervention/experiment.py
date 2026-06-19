"""
intervention/experiment.py — the do-operator, executed on a discarded SHADOW world.

This is where the controlled perturbation happens. It NEVER mutates the world it is given: `do_run` deep-copies
the initial state and forces `holds = {node: value}` every step (Pearl's do-operator), returning only a
trajectory. The committed history is therefore untouched by construction — the extended invariant

    experiment cannot change committed history

is a property of the type (the input dict is never written), not a discipline. `causal_effect` runs two
counterfactuals — do(source=v1) and do(source=v2) — and returns how much the target's trajectory diverges
between them: the interventional signature of "source affects target" (vary the cause, watch the effect).
Deterministic integer dynamics; stdlib only.
"""
import copy


def do_run(dynamics, init, steps, holds=None):
    """Run `dynamics` for `steps` on a COPY of `init`, forcing every node in `holds` to its constant value
    each step (the do-operator). Returns the trajectory (list of state dicts). `init` is never mutated."""
    holds = dict(holds or {})
    s = copy.deepcopy(init)
    for n, v in holds.items():
        s[n] = v                                          # apply do() at t0
    traj = []
    for _ in range(steps):
        s = dynamics(s)
        for n, v in holds.items():
            s[n] = v                                      # re-apply do() after each transition
        traj.append(dict(s))
    return traj


def series(traj, node):
    return [st.get(node, 0) for st in traj]


def causal_effect(dynamics, init, steps, source, target, v1, v2):
    """Interventional effect of `source` on `target`: L1 divergence of target's trajectory between
    do(source=v1) and do(source=v2). >0 iff forcing different values of source changes target. The exogenous
    rest of the world evolves identically in both counterfactuals, so a confounded (non-causal) pair gives 0."""
    t1 = series(do_run(dynamics, init, steps, {source: v1}), target)
    t2 = series(do_run(dynamics, init, steps, {source: v2}), target)
    return sum(abs(a - b) for a, b in zip(t1, t2))


def committed_unchanged(hash_fn, init, dynamics, source, target, steps, v1, v2):
    """Guarantee check: hash the world, run BOTH counterfactual effect probes, hash again. The experiment
    operates on copies, so the two hashes must be identical (experiment ⊥ committed history)."""
    before = hash_fn(init)
    causal_effect(dynamics, init, steps, source, target, v1, v2)
    causal_effect(dynamics, init, steps, target, source, v1, v2)
    after = hash_fn(init)
    return before == after
