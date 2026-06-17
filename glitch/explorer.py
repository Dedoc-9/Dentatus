"""
glitch/explorer.py — a deterministic, bounded state-space explorer (stateful property fuzzer).

================================================================================================
HONEST FRAMING — what this is, and the marketing it is NOT
================================================================================================
IS:
  * A deterministic, bounded explorer of interleavings / contradictory inputs over a state machine built
    on the frozen `chronicle` core (imported read-only; the Sibling Law — we never edit or inject into it).
  * It DEDUPS states by their CONTENT HASH (chronicle.state_hash): identical states reached by different
    paths are explored exactly once. THIS is the real efficiency — cost is bounded by the number of
    DISTINCT states, not the number of paths, and many "timelines" converge to the same state.
  * On the first invariant-violating state it returns the triggering path, SHRINKS it to a minimal
    counterexample (delta-debugging), and seals that run into a signed chronicle ledger so it replays
    bit-for-bit in the Replay Court.

IS NOT (these parts of the pitch are physically impossible or rule-breaking — dropped on purpose):
  * NOT "quantum" / "super-position" anything, and NOT "millions of timelines evaluated in a single CPU
    pass." Each distinct state is evaluated once; there is no magical simultaneity.
  * NOT a bytecode injector into core.py. It drives the core ONLY through its public API.
  * NOT thread-free parallelism via memoryview. It explores deterministically, single-threaded.

BOUNDED MODEL-CHECK (integrity != truth, applied to testing): it finds counterexamples up to `max_depth`.
The ABSENCE of a counterexample at depth k is NOT a proof of total absence of bugs.
"""
import os
import sys
import collections

_WB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
import core                                              # frozen: state_hash, canonical_bytes, Recorder, ...
from core import Recorder, ruleset_hash, InvariantViolation


class Result:
    def __init__(self, found, path, states_explored, depth_reached, distinct_states):
        self.found = found
        self.path = path                                 # list of events (the counterexample, if found)
        self.states_explored = states_explored           # transitions evaluated
        self.depth_reached = depth_reached
        self.distinct_states = distinct_states           # unique content hashes seen (the dedup win)

    def __repr__(self):
        return ("Result(found=%s, path_len=%s, states_explored=%s, distinct_states=%s, depth=%s)"
                % (self.found, len(self.path) if self.path else 0, self.states_explored,
                   self.distinct_states, self.depth_reached))


def explore(initial, events, step_fn, invariant_fn, max_depth=6):
    """Breadth-first search over event sequences (length <= max_depth). Dedup visited states by content
    hash. Return the FIRST path whose resulting state violates `invariant_fn`. Deterministic: `events` is
    iterated in given order and states are keyed by canonical hash, so the counterexample is reproducible.

    step_fn(state, event) -> new_state        (pure; must not mutate `state`)
    invariant_fn(state) -> bool               (True == healthy)
    """
    seen = {core.state_hash(initial)}
    q = collections.deque([(initial, [])])
    explored = 0
    depth_reached = 0
    while q:
        state, path = q.popleft()
        depth_reached = max(depth_reached, len(path))
        if len(path) >= max_depth:
            continue
        for ev in events:
            new_state = step_fn(state, ev)
            explored += 1
            new_path = path + [ev]
            if not invariant_fn(new_state):
                return Result(True, new_path, explored, len(new_path), len(seen))
            h = core.state_hash(new_state)
            if h not in seen:                            # content-hash dedup: skip already-seen states
                seen.add(h)
                q.append((new_state, new_path))
    return Result(False, None, explored, depth_reached, len(seen))


def replay_path(initial, path, step_fn):
    """Deterministically re-apply a path; return the final state (for verification / shrinking)."""
    s = initial
    for ev in path:
        s = step_fn(s, ev)
    return s


def _still_fails(initial, path, step_fn, invariant_fn):
    if not path:
        return False
    s = initial
    for ev in path:
        s = step_fn(s, ev)
        if not invariant_fn(s):
            return True
    return False


def shrink(initial, path, step_fn, invariant_fn):
    """Delta-debug to a minimal counterexample: greedily drop events while a violation still occurs.
    Deterministic and order-stable -> the minimal sequence is itself reproducible."""
    current = list(path)
    changed = True
    while changed:
        changed = False
        for i in range(len(current)):
            candidate = current[:i] + current[i + 1:]
            if _still_fails(initial, candidate, step_fn, invariant_fn):
                current = candidate
                changed = True
                break
    return current


def seal_counterexample(initial, path, step_fn, invariant_fn, signer):
    """Seal the counterexample into a signed chronicle ledger: each VALID step is recorded; the final,
    invariant-breaking step is REFUSED by the recorder's fail-closed gate (that refusal IS the proof the
    workbench catches the bug). Returns (ledger, refused_event_or_None, logic, gate) so the caller can
    verify the sealed prefix in the Replay Court with the same ruleset. The ledger replays bit-for-bit."""
    def logic(inp):
        return {"state": step_fn(inp["state"], inp["event"])}

    def gate(inp, out):
        return invariant_fn(out["state"])

    rec = Recorder(signer, ruleset_hash(logic, gate))
    ledger = []
    state = initial
    for i, ev in enumerate(path):
        inp = {"state": state, "event": ev}
        out = logic(inp)
        try:
            ledger.append(rec.record("STEP-%d" % i, inp, out, gate))
            state = out["state"]
        except InvariantViolation:
            return ledger, ev, logic, gate               # fail-closed at the exact breaking step
    return ledger, None, logic, gate
