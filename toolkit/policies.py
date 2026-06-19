"""
toolkit.policies — named scoring functions. A policy maps one item -> an integer priority.

The toolkit does NOT privilege any single policy. `future_surface` is the default heuristic, not
the identity of the toolkit: any callable `item -> int` is a valid scorer, so the library is
"resource allocation under uncertainty", not a "future_surface library".

Dev note — the bounds the architecture already discovered, which is why the scorer is swappable:
  possibility != likelihood   — a reachable option is not a probable one.
  attention   != truth        — a high score is a request for resources, not a fact about the world.
A policy is therefore an ESTIMATE of importance supplied by the caller. Quality of attention follows
quality of signal (see toolkit.benchmarks.make_adversarial_world, where a confident-but-wrong signal
makes the default policy lose on purpose).
"""
from __future__ import annotations


def future_surface(item):
    """Default heuristic: spend where an item is at once consequential, uncertain, and live.

        future_surface = consequence * uncertainty * possibility
    """
    return max(1, (item["consequence"] * item["uncertainty"] * item["possibility"]) // 1_000_000)


def magnitude(item):
    """Naive baseline: spend on the biggest. Often wrong — the butterfly."""
    return item.get("magnitude", item["consequence"])


def uniform(item):
    """Floor: every item scored alike, so greedy becomes cheapest-first (maximize coverage)."""
    return 1
