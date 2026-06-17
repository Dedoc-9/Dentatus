"""
syracuse/orbit.py — the Collatz (3n+1) / Syracuse map as the workbench's axiom compiled to a runnable example.

The map is pure integer and fully deterministic:  T(n) = n/2 (n even)  |  (3n+1)/2 (n odd, compressed Syracuse
form).  Every trajectory n -> ... -> 1 is replayable bit-for-bit and content-addressable, with no float in the
identity. Yet whether EVERY trajectory reaches 1 is unproven — checked by computer to enormous bounds, never
proven in general.

That is `integrity != truth` made literal, not metaphorical:
  * INTEGRITY (provable here): this n reaches 1 in exactly S steps with peak P — verifiable on any machine.
  * TRUTH      (NOT provable here): all n reach 1 (the Collatz conjecture). This module is built to REFUSE that
    claim structurally — it signs trajectories, never the conjecture (see ConjectureWitness).

EXACT GATES (decide validity; fold into the orbit hash):
  start n, the orbit sequence, reached_one (bool), stopping_time S (int), within_budget (S <= K).
CAPTURED OBSERVABLES (descriptive; never gate):
  peak / max-altitude, odd/even step counts, parity-word of the orbit, and the float log-drift
  odd*ln(3) - S*ln(2) ~ -ln(n).

The step budget K is an admitted coarse-graining (your "event boundaries are model constructs"): "terminates
within K" is a chosen cut, not the trajectory's inherent property — a budget breach means we have not spent
enough steps to know the terminus, not that one does not exist.

HONEST BOUND: Collatz is NOT a cryptographic primitive — not a secure proof-of-work (no tunable difficulty, no
preimage resistance; a precomputed orbit replays trivially), not an RNG, not a hash. Its honest value here is a
pure-integer, deterministic, hard-to-predict / easy-to-verify reference workload (for ration/lockstep/glitch)
and the cleanest concrete demonstration of integrity != truth in the workbench.

Imports chronicle read-only (Sibling Law); optional ration/lockstep adapters import those siblings read-only.
"""
import os
import sys
import math

_WB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
import core                                                  # chronicle/core.py


class SyracuseError(Exception):
    pass


class BudgetExceeded(SyracuseError):
    """Raised when an orbit exceeds the step budget K before reaching 1 — terminus unknown WITHIN budget
    (not a claim that the trajectory diverges)."""


# ----------------------------------------------------------------- the integer map
def step(n, compressed=True):
    """One Collatz/Syracuse step on a positive integer. compressed: odd n -> (3n+1)/2 (the accelerated map)."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise SyracuseError("the Syracuse map is defined on positive integers; got %r" % (n,))
    if n % 2 == 0:
        return n // 2
    return (3 * n + 1) // 2 if compressed else 3 * n + 1


def orbit(n, max_steps=100_000, compressed=True):
    """The trajectory [n, T(n), ..., 1]. Raises BudgetExceeded if it does not reach 1 within max_steps."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise SyracuseError("orbit start must be a positive integer; got %r" % (n,))
    seq = [n]
    while seq[-1] != 1:
        if len(seq) - 1 >= max_steps:
            raise BudgetExceeded("orbit of %d exceeded %d steps (terminus unknown within budget)" % (n, max_steps))
        seq.append(step(seq[-1], compressed))
    return seq


def orbit_hash(seq):
    """Content address of a trajectory (integer-exact, no float)."""
    return core.state_hash({"orbit": seq})


# ----------------------------------------------------------------- exact gates vs observables
def gates(n, max_steps=100_000, compressed=True):
    """The EXACT, validity-deciding facts. within_budget is the gate; reached_one/stopping_time are exact."""
    try:
        seq = orbit(n, max_steps, compressed)
    except BudgetExceeded:
        return {"start": n, "reached_one": None, "stopping_time": None,
                "within_budget": False, "orbit_hash": None}
    return {"start": n, "reached_one": True, "stopping_time": len(seq) - 1,
            "within_budget": True, "orbit_hash": orbit_hash(seq)}


def observables(seq):
    """Descriptive stats. NEVER gate a decision: a float drift or an altitude does not decide validity."""
    steps = seq[:-1]
    odd = sum(1 for x in steps if x % 2 == 1)
    even = len(steps) - odd
    S = len(steps)
    drift = odd * math.log(3) - S * math.log(2)              # ~ -ln(n); a captured FLOAT observable
    return {"peak": max(seq), "odd_steps": odd, "even_steps": even,
            "parity_word": "".join("1" if x % 2 else "0" for x in steps),
            "log_drift": drift}


# ----------------------------------------------------------------- the ghost: empirical reach, never a proof
class ConjectureWitness:
    """Accumulates EMPIRICAL reach across verified seeds. It is the project's modesty made structural: its
    report() always returns conjecture_proven=False. Raising max_verified_n is integrity (more checked); it
    is never truth (the general case). This is the irreducible residual G — the open conjecture itself."""

    def __init__(self):
        self.verified_count = 0
        self.max_verified_n = 0
        self.max_stopping_time = 0
        self.refused = []                                    # seeds whose terminus was unknown within budget

    def record(self, g):
        if g["reached_one"]:
            self.verified_count += 1
            self.max_verified_n = max(self.max_verified_n, g["start"])
            self.max_stopping_time = max(self.max_stopping_time, g["stopping_time"])
        else:
            self.refused.append(g["start"])
        return self

    def report(self):
        return {"verified_count": self.verified_count, "max_verified_n": self.max_verified_n,
                "max_stopping_time": self.max_stopping_time, "refused_within_budget": list(self.refused),
                "conjecture_proven": False}                  # structural refusal — integrity != truth


# ----------------------------------------------------------------- ration tie (hardware-invariant budget)
def ration_counts(n, max_steps=100_000, compressed=True):
    """Map an orbit's stopping time onto ration's integer logical-step counts, so ration.within_budget can
    gate it identically on any hardware. A non-terminating-within-budget seed reports the budget as spent."""
    g = gates(n, max_steps, compressed)
    iters = g["stopping_time"] if g["within_budget"] else max_steps
    return {"iterations": iters, "tokens": 0, "mutations": 0, "nodes": 0}


# ----------------------------------------------------------------- lockstep tie (each step a content-addressed tick)
def as_truth_track(n, max_steps=100_000, compressed=True):
    """Build a lockstep TruthTrack whose ticks ARE Collatz steps — each step content-addressed, replayable."""
    sys.path.insert(0, os.path.join(_WB, "lockstep"))
    from tick import TruthTrack                              # lockstep/tick.py

    def collatz_step(state, _inp):
        return {"n": step(state["n"], compressed)}

    track = TruthTrack({"n": n}, collatz_step)
    while track.states[-1]["n"] != 1:
        if track.tick >= max_steps:
            raise BudgetExceeded("orbit of %d exceeded %d ticks" % (n, max_steps))
        track.advance({})
    return track
