"""
VeriSim/court.py — the Replay Court: download a Shard, replay it locally, confirm bit-for-bit.

`replay` re-runs the scenario from the seed under the same source-hashed rules (via `tessera.verify`) AND
recomputes the `stasis` Merkle root, so a producer cannot have faked either the path or the per-step history.
`classify_final` uses the exact-gate / observable split to separate a real LOGIC change from benign
hardware/observable drift. `spot_check_step` proves a single step is in the run without replaying all of it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cores import tessera, drift, merkle
import scenarios
import runner


def replay(shard):
    """Verify a Shard end-to-end. Returns {verified, detail, steps, final_match, merkle_match}."""
    scenario = shard["scenario"]
    if scenario not in scenarios.REGISTRY:
        return {"verified": False, "detail": "unknown scenario %r" % scenario, "steps": 0}
    rule, done = scenarios.REGISTRY[scenario]
    ok, detail = tessera.verify(shard["tessera"], rule, done)                 # full bit-for-bit replay
    leaves, final, steps = runner.step_history(rule, done, shard["tessera"]["seed"], shard["steps"] + 2)
    merkle_match = (merkle.merkle_root(leaves) == shard["merkle_root"])
    final_match = (final == shard["final_state"])
    return {"verified": bool(ok and merkle_match and final_match),
            "detail": detail if not ok else ("merkle mismatch" if not merkle_match else
                      ("final-state mismatch" if not final_match else "VERIFIED")),
            "steps": steps, "final_match": final_match, "merkle_match": merkle_match}


def classify_final(shard, observed_final, gate_fields):
    """Compare a re-run's final state against the shard's, splitting LOGIC_ERROR (a gated field changed ->
    FAIL) from OBSERVABLE_DRIFT (only non-gated fields differ -> benign WARN). Never halts."""
    return drift.classify(shard["final_state"], observed_final, gate_fields)


def spot_check_step(shard, step_index):
    """Prove a single step is part of the recorded run via an O(log n) Merkle inclusion proof, without
    replaying the whole simulation against the root. Returns (ok, leaf_hash)."""
    scenario = shard["scenario"]
    rule, done = scenarios.REGISTRY[scenario]
    leaves, _, _ = runner.step_history(rule, done, shard["tessera"]["seed"], shard["steps"] + 2)
    if not (0 <= step_index < len(leaves)):
        return False, None
    proof = merkle.inclusion_proof(leaves, step_index)
    return merkle.verify_inclusion(leaves[step_index], proof, shard["merkle_root"]), leaves[step_index]
