"""
lockstep/tick.py — the authoritative truth track: a fixed-timestep, integer, content-addressed simulation.

This is the half of a real-time engine that *becomes truth*. It advances in abstract INTEGER tick indices
(n = 0, 1, 2, ...) and every tick is content-addressed:  H_n = state_hash({tick:n, state}).  All simulation
state is integer (positions/velocities in fixed-point micro-units); no float ever enters a truth hash,
because float arithmetic is not associative under rounding and two replays of the "same" float sim can
diverge in the last bit -- a truth that cannot be content-addressed is not a truth.

The truth RATE (ticks/second) is deliberately NOT the frame rate. A render thread may draw 240 frames a
second on top of a 120 Hz truth track; those frames are interpolations (see interp.py), captured as
observables, never gated. Time-as-wall-clock is kept out of here entirely: a tick is a pure index, and the
mapping to seconds (n / truth_rate) is a rational handled at the render boundary, so nothing is ever forced
through a lossy microsecond rounding.

HONEST BOUND: this is the deterministic reconciliation CORE -- the scheduler and the integer-exact state it
hashes. It is NOT a GPU renderer; it produces the verifiable authoritative stream a real engine's render
thread consumes, it does not push pixels at 1440p/240Hz. (Integrity is not truth: it proves the tick stream
is exact and replayable, not that the simulation models anything real.)

Imports chronicle read-only (Sibling Law).
"""
import os
import sys

_WB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
import core                                                  # chronicle/core.py


class LockstepError(Exception):
    pass


def truth_hash(n, state):
    """Content address of the authoritative state AT tick n. Render positions never enter this."""
    return core.state_hash({"tick": n, "state": state})


# ----------------------------------------------------------------- a canonical integer simulation
def kinematic_step(state, inp):
    """A tiny deterministic integer sim used by the demo/tests. state in fixed-point micro-units:
        state = {"p": int position, "v": int velocity-per-tick};  inp = {"a": int acceleration}
    Pure integer: v += a; p += v. Bit-identical on any machine."""
    v = state["v"] + int(inp.get("a", 0))
    p = state["p"] + v
    return {"p": p, "v": v}


class TruthTrack:
    """Append-only authoritative tick history. state[n] is the truth at tick n; inputs[n] is applied to
    state[n] to produce state[n+1]; hashes[n] content-addresses state[n]."""

    def __init__(self, genesis_state, step_fn):
        self.step = step_fn
        self.states = [dict(genesis_state)]
        self.inputs = []                                     # inputs[n] : state[n] -> state[n+1]
        self.hashes = [truth_hash(0, genesis_state)]

    @property
    def tick(self):
        return len(self.states) - 1

    def advance(self, inp):
        n = self.tick
        new_state = self.step(self.states[-1], inp)
        self.states.append(new_state)
        self.inputs.append(dict(inp))
        self.hashes.append(truth_hash(n + 1, new_state))
        return self.hashes[-1]

    def state_at(self, n):
        return self.states[n]

    def hash_at(self, n):
        return self.hashes[n]

    @classmethod
    def from_inputs(cls, genesis_state, step_fn, inputs):
        """Rebuild a track deterministically from a list of inputs (used by rollback re-simulation)."""
        t = cls(genesis_state, step_fn)
        for inp in inputs:
            t.advance(inp)
        return t
