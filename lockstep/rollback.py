"""
lockstep/rollback.py — reconciliation by reverting to the last valid hashed state, then re-simulating.

A client predicts remote inputs to render *now* instead of waiting a network round-trip. When the
authoritative inputs arrive and differ from what was predicted, the client does NOT patch the present in
place: it reverts to the last tick whose hash still matches authority (the last valid hashed state) and
RE-SIMULATES forward with the corrected inputs. Because the sim is deterministic integer logic (tick.py),
the re-simulation is exact, so two clients on different hardware converge to one truth.

This is the workbench's "revert to the last valid hashed state" rule expressed as netcode: the truth a
client showed between the divergence and now was a *prediction* (an observable), never committed truth;
correcting it costs a bounded re-sim, not a contradiction in the ledger.

OBSERVABLES (captured, never gated): rollback_depth (ticks re-simulated), last_valid_tick, whether the
final hash changed. They measure the cost and reach of a correction; they do not themselves decide truth --
the corrected track's tick hashes do.

DEV NOTE — the rollback ghost: the residual between the predicted track and the corrected track is the
mispredict. It is bounded by rollback_depth and is exactly analogous to quorum's dissent ghost: a recorded
divergence the system absorbs by reverting, never a state it commits. A persistently large rollback_depth
(EMA-able like quorum's S_t) is an early signal of bad prediction or an out-of-sync peer -- a sensor, not a
gate.

HONEST BOUND: deterministic convergence holds ONLY if the sim is pure integer logic and all clients share
the genesis state + step function. A non-deterministic step (float drift, un-captured clock/RNG) breaks the
guarantee -- route such reads through chronicle's capture seam first. Rollback also assumes inputs are
eventually authoritatively known; it does not invent missing inputs.
"""
import os
import sys

_WB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core                                                  # chronicle/core.py
from tick import TruthTrack


def first_input_divergence(predicted_inputs, authoritative_inputs):
    """Earliest tick index where the predicted input differs from the authoritative one (canonical
    compare), within the common prefix. None if they agree on everything compared."""
    m = min(len(predicted_inputs), len(authoritative_inputs))
    for i in range(m):
        if core.canonical_bytes(predicted_inputs[i]) != core.canonical_bytes(authoritative_inputs[i]):
            return i
    return None


def last_valid_tick(predicted_track, authoritative_hashes):
    """Largest tick n whose predicted hash still equals authority's hash (the last valid hashed state)."""
    m = min(len(predicted_track.hashes), len(authoritative_hashes))
    last = 0
    for n in range(m):
        if predicted_track.hashes[n] == authoritative_hashes[n]:
            last = n
        else:
            break
    return last


def reconcile(predicted_track, authoritative_inputs, step_fn, genesis_state=None):
    """Revert-and-resim. `authoritative_inputs` is the corrected input prefix the server affirms. Returns:

        {rollback_depth, last_valid_tick, changed, corrected}

    where `corrected` is a fresh deterministic TruthTrack: authoritative inputs for their length, then the
    client's predicted inputs for any ticks beyond what authority has affirmed."""
    genesis = predicted_track.states[0] if genesis_state is None else genesis_state
    d = first_input_divergence(predicted_track.inputs, authoritative_inputs)

    merged = list(authoritative_inputs) + predicted_track.inputs[len(authoritative_inputs):]
    corrected = TruthTrack.from_inputs(genesis, step_fn, merged)

    if d is None and len(authoritative_inputs) <= len(predicted_track.inputs):
        return {"rollback_depth": 0, "last_valid_tick": predicted_track.tick,
                "changed": False, "corrected": corrected}

    valid = d if d is not None else len(predicted_track.inputs)   # state[valid] still trustworthy
    rollback_depth = predicted_track.tick - valid
    changed = corrected.hashes[-1] != predicted_track.hashes[-1]
    return {"rollback_depth": rollback_depth, "last_valid_tick": valid,
            "changed": changed, "corrected": corrected}
