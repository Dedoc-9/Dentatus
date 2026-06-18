"""
VeriSim/runner.py — run a verifiable simulation and emit a Shard.

A Shard is the unit of VeriSim: a content-addressed, offline-replayable record that a specific scenario was
run, with these inputs, under these exact (source-hashed) rules, producing this exact final state and this
exact step history. It bundles a `tessera` proof (full bit-for-bit replay) with a `stasis` Merkle root over
the per-step states (so any single step can be spot-checked in O(log n) without replaying the whole run).

HONEST BOUND: a Shard proves the SIMULATION was real and replayable — never that the simulation matches
reality, that the model is correct, or that any real-world system is safe. integrity != truth, applied to
simulation: a verifiable simulation is not a verified reality.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cores import tessera, canon, merkle
import scenarios

SCHEMA = "verisim/1"


def step_history(rule, done, seed, max_steps):
    """Replay the scenario, returning (per-step state hashes, final_state, steps). Pure integer states are
    canonicalized through the stasis Iron Canon (rejects float pollution)."""
    leaves = [canon.canon_hash(seed)]
    state = seed
    steps = 0
    while not done(state):
        if steps >= max_steps:
            break
        state = rule(state)
        steps += 1
        leaves.append(canon.canon_hash(state))
    return leaves, state, steps


def run_simulation(scenario, seed, input_data=None, signer=None, fuel_budget=200000):
    """Run `scenario` from `seed` and emit a Shard. `input_data` (optional) is any external data the run
    consumed; its canonical hash is bound into the shard so a verifier knows exactly what was fed in."""
    if scenario not in scenarios.REGISTRY:
        raise ValueError("unknown scenario %r" % scenario)
    rule, done = scenarios.REGISTRY[scenario]
    tess = tessera.mint(rule, done, seed, max_steps=fuel_budget, signer=signer,
                        meta={"scenario": scenario})
    leaves, final, steps = step_history(rule, done, seed, fuel_budget)
    return {
        "schema": SCHEMA,
        "scenario": scenario,
        "ruleset_hash": tess["ruleset_hash"],
        "input_data_hash": (canon.canon_hash(input_data) if input_data is not None else None),
        "steps": steps,
        "final_state": final,
        "merkle_root": merkle.merkle_root(leaves),
        "leaf_count": len(leaves),
        "tessera": tess,
    }
