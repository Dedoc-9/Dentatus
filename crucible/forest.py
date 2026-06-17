"""
crucible/forest.py — reverse-Syracuse seed generation: controlled chaos with NO entropy.

Forward, the compressed Syracuse map is T(n)=n/2 (even) or (3n+1)/2 (odd). `crucible` runs it BACKWARD:
starting from the terminus 1, it grows the tree of pre-images upward, so every node it emits is a seed
whose forward stopping time is EXACTLY its reverse depth — known by construction, not by guessing.

Pre-images of m under the compressed map:
  * even branch:  n = 2m            (always valid; 2m is even)
  * odd branch:   n = (2m-1)/3      (valid iff 2m-1 ≡ 0 mod 3, the result is odd, and > 1)
The `n > 1` guard excludes re-entry into the trivial 1→2→1 cycle, so the reverse graph is a tree.

This is a DETERMINISTIC fuzzer: it injects mathematically structured hard cases, not random garbage —
no RNG, no entropy, so it cannot introduce the drift the integer stack forbids. Generation is a pure
function of (max_depth, value_ceiling); re-running yields the identical forest.

HONEST BOUNDS (do not oversell):
  * It constructs seeds with a KNOWN, targeted stopping time and peak. It does NOT find the globally
    hardest seed — that is bound up with the open conjecture. It maps the difficulty landscape; it does
    not claim to maximize it.
  * Surviving these seeds is EVIDENCE of integer integrity over a structured hard set, not a PROOF of
    correctness for all integers. (integrity ≠ truth.)
  * It does not solve Collatz. "Here is a seed that takes S steps — can your stack handle it?"

Imports syracuse + chronicle read-only (Sibling Law).
"""
import os
import sys
from collections import deque

_WB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_WB, "syracuse"))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
import orbit as SY                                           # syracuse/orbit.py
import core                                                  # chronicle/core.py


class CrucibleError(Exception):
    pass


def preimages(m):
    """Compressed-map pre-images of m, in deterministic order: even branch always; odd branch if valid."""
    out = [2 * m]
    t = 2 * m - 1
    if t % 3 == 0:
        n = t // 3
        if n > 1 and n % 2 == 1:
            out.append(n)
    return out


def generate(max_depth, value_ceiling=10 ** 12, max_nodes=200_000):
    """Grow the reverse-Syracuse forest from 1 up to `max_depth`, pruning any node above `value_ceiling`.
    Returns a list of seeds [{n, stopping_time, peak}] (stopping_time == reverse depth, exact)."""
    if max_depth < 1:
        raise CrucibleError("max_depth must be >= 1")
    seeds = []
    q = deque([{"n": 1, "stopping_time": 0, "peak": 1}])
    emitted = 0
    while q:
        node = q.popleft()
        if node["stopping_time"] >= max_depth:
            continue
        for c in preimages(node["n"]):
            if c > value_ceiling:
                continue
            cpeak = max(node["peak"], c)
            child = {"n": c, "stopping_time": node["stopping_time"] + 1, "peak": cpeak, "altitude": cpeak // c}
            seeds.append(child)
            emitted += 1
            if emitted >= max_nodes:
                return seeds
            q.append(child)
    return seeds


def verify_seed(seed):
    """Cross-check a generated seed against the FORWARD syracuse map: the claimed stopping_time and peak
    must match an independent forward replay. This is the generator's own integrity gate."""
    g = SY.gates(seed["n"])
    if not g["reached_one"] or g["stopping_time"] != seed["stopping_time"]:
        return False, "stopping_time mismatch (claimed %s, forward %s)" % (seed["stopping_time"], g["stopping_time"])
    peak = SY.observables(SY.orbit(seed["n"]))["peak"]
    if peak != seed["peak"]:
        return False, "peak mismatch (claimed %s, forward %s)" % (seed["peak"], peak)
    return True, "matches forward replay"


def select(seeds, within_budget=None, by="altitude"):
    """Pick the hardest seed whose stopping_time is within a step budget. Hardness metric `by`:
       'altitude'      = peak // n   (how far the orbit climbs above the seed; a power of 2 has altitude 1)
       'peak'          = raw max value on the path
       'stopping_time' = reverse depth
    'altitude' is the default because raw peak trivially favours large powers of 2 (peak == seed)."""
    pool = [s for s in seeds if within_budget is None or s["stopping_time"] <= within_budget]
    if not pool:
        return None
    return max(pool, key=lambda s: (s[by], s["stopping_time"], -s["n"]))


def seed_just_under(budget_K, value_ceiling=10 ** 12, max_nodes=200_000):
    """A hard (high-peak) seed whose stopping_time is <= budget_K — the worst case the engine must survive
    while staying within its step budget. Returns the seed dict, or None if the forest is empty."""
    forest = generate(budget_K, value_ceiling, max_nodes)
    return select(forest, within_budget=budget_K, by="altitude")
