"""
dini/compass.py — a hyperbolic "novelty compass": a captured SENSOR over an agent's execution DAG.

Named for Ulisse Dini's surface (constant negative curvature). The honest substance is HYPERBOLIC tree
embedding: a state DAG (every state keyed by its chronicle content hash) embeds into the Poincaré disk
with low distortion, because hyperbolic volume grows exponentially the way tree branching does
(Sarkar's construction; Nickel & Kiela's Poincaré embeddings). That gives an agent a cheap scalar sense
of *where it is* in the space it is exploring.

================================================================================================
WHAT THIS IS — and the rails it runs on
================================================================================================
IS: a SENSOR. For each state reached it returns a captured observable:
      dini_distance  : Poincaré distance of the state's embedding from the root (grows with depth/novelty)
      depth          : exact integer tree depth (the un-fuzzy companion signal)
      novelty        : True the first time a content hash is seen
      coord          : [x, y] in the open unit disk
IS NOT: a gate, a safety mechanism, or a "hallucination detector". It is an *environmental reading* an
      agent may steer by. A distance spike flags a TOPOLOGICAL ANOMALY (the state moved far/deep relative
      to a baseline), which CORRELATES with drift/aberrance — it does not prove the agent hallucinated.

DETERMINISM BOUNDARY: dini_distance is a FLOAT and float trig is not bit-identical across architectures,
so it is a CAPTURED OBSERVABLE — recorded as an input, replayed, NEVER placed in the commit hash. The
exact integer `depth`/`novelty` are reproducible and may be used directly. (AGENTS.md §1, §4.)

Integrity != truth: a coverage/novelty number is a heuristic compass, never a guarantee of correctness.

Stdlib only (`math`, `cmath`). Imports the frozen chronicle core read-only for `state_hash` (Sibling Law).
"""
import os
import sys
import math
import cmath

_WB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
import core  # frozen: state_hash / canonical_bytes

GOLDEN = math.pi * (3.0 - math.sqrt(5.0))   # ~2.39996 rad: spreads siblings without knowing the count
_EPS = 1e-12


def _clamp_disk(z):
    r = abs(z)
    if r >= 1.0 - 1e-9:
        z = z / r * (1.0 - 1e-9)
    return z


def poincare_distance(u, v):
    """Hyperbolic distance between two points of the open unit disk (Poincaré model)."""
    u = _clamp_disk(complex(u)); v = _clamp_disk(complex(v))
    num = 2.0 * abs(u - v) ** 2
    den = (1.0 - abs(u) ** 2) * (1.0 - abs(v) ** 2)
    return math.acosh(1.0 + num / max(den, _EPS))


def _mobius_to_origin(a, z):
    """Mobius transform sending a -> 0 (an isometry of the disk)."""
    return (z - a) / (1.0 - a.conjugate() * z + 0j)


def _mobius_from_origin(a, w):
    """Inverse: sends 0 -> a."""
    return (w + a) / (1.0 + a.conjugate() * w + 0j)


class HyperbolicMap:
    """Streaming, deterministic embedding of a state DAG. Coordinates are assigned on FIRST discovery
    (a BFS/exploration tree), so the embedding is reproducible given the order states are observed."""

    def __init__(self, edge_length=1.0):
        self.edge = float(edge_length)            # hyperbolic distance placed between parent and child
        self.coord = {}                           # hash -> complex coordinate
        self.parent = {}                          # hash -> parent hash
        self.depth = {}                           # hash -> int
        self._kids = {}                           # hash -> count of children placed (for sibling fan)
        self.root = None

    def set_root(self, state):
        h = core.state_hash(state)
        if h not in self.coord:
            self.coord[h] = 0j
            self.depth[h] = 0
            self._kids[h] = 0
        self.root = h
        return self._report(h, novelty=(self.depth[h] == 0))

    def _place_child(self, ph):
        zp = self.coord[ph]
        gp = self.coord.get(self.parent.get(ph))
        # fan children AWAY from the grandparent direction (in the parent-centered frame)
        if gp is not None:
            back = cmath.phase(_mobius_to_origin(zp, gp))
            away = back + math.pi
        else:
            away = 0.0
        i = self._kids[ph]; self._kids[ph] = i + 1
        angle = away + i * GOLDEN
        w = math.tanh(self.edge / 2.0) * cmath.exp(1j * angle)   # child image at hyperbolic radius `edge`
        return _clamp_disk(_mobius_from_origin(zp, w))

    def observe(self, parent_state, state):
        """Record a transition parent_state -> state; return the captured observable for `state`."""
        if self.root is None:
            self.set_root(parent_state)
        ph = core.state_hash(parent_state)
        if ph not in self.coord:                  # parent unseen: attach it to root first
            self.coord[ph] = self._place_child(self.root) if ph != self.root else 0j
            self.parent[ph] = self.root; self.depth[ph] = self.depth.get(self.root, 0) + 1; self._kids[ph] = 0
        h = core.state_hash(state)
        novelty = h not in self.coord
        if novelty:
            self.coord[h] = self._place_child(ph)
            self.parent[h] = ph
            self.depth[h] = self.depth[ph] + 1
            self._kids[h] = 0
        return self._report(h, novelty)

    def _report(self, h, novelty):
        z = self.coord[h]
        return {
            "dini_distance": round(poincare_distance(0j, z), 6),   # captured float observable
            "depth": self.depth[h],                                 # exact int companion
            "novelty": bool(novelty),
            "coord": [round(z.real, 6), round(z.imag, 6)],
        }

    def distance_between(self, state_a, state_b):
        return round(poincare_distance(self.coord[core.state_hash(state_a)],
                                       self.coord[core.state_hash(state_b)]), 6)


def anomaly(observation, threshold):
    """Heuristic flag: True if dini_distance exceeds an operator-PINNED threshold. A flag is a *suggestion*
    to self-correct/rollback — NOT a safety guarantee and NOT proof of hallucination."""
    return observation["dini_distance"] > float(threshold)
