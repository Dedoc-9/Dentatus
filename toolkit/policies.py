"""
toolkit.policies — named scoring functions. A policy maps one item -> an integer priority.

The toolkit does NOT privilege any single policy. future_surface is the default heuristic, not the
identity of the toolkit: any callable item->int is a valid scorer, so the library is "resource
allocation under uncertainty", not a "future_surface library".

Aggregation is a load-bearing CHOICE, not a fact (see benchmarks.calibration):
  product           consequence * uncertainty * possibility   (1000*1000*1 beats 300*300*300)
  min_gate          min(consequence, uncertainty, possibility) (a weak dimension caps attention)
  weighted_product  consequence-weighted product               (consequence dominates)
The right aggregation depends on how realized importance M actually composes; the benchmark discovers
which assumption is load-bearing rather than asserting one.

(geometric_mean is intentionally omitted: (c*u*p)**(1/3) is a monotone transform of the product, so it
produces the IDENTICAL ranking and therefore the identical allocation. It would add a name, not a policy.)

Dev note -- the bounds that justify making the scorer swappable:
  possibility != likelihood   -- a reachable option is not a probable one.
  attention   != truth        -- a high score is a request for resources, not a fact about the world.
  attention   != discovery    -- the field finds importance only where the signal encodes it.
A policy is an ESTIMATE of importance supplied by the caller. Quality of attention follows quality of signal.
"""
from __future__ import annotations
import zlib


def future_surface(item):
    """Default heuristic (product): spend where an item is at once consequential, uncertain, live."""
    return max(1, (item["consequence"] * item["uncertainty"] * item["possibility"]) // 1_000_000)


def min_gate(item):
    """A weak dimension caps attention: importance is the WEAKEST signal, not the product."""
    return min(item["consequence"], item["uncertainty"], item["possibility"])


def weighted_product(item):
    """Consequence-weighted product: consequence counts twice, uncertainty/possibility once."""
    return max(1, (item["consequence"] ** 2 * item["uncertainty"] * item["possibility"]) // 1_000_000_000)


def magnitude(item):
    """Naive baseline: spend on the biggest. Often wrong -- the butterfly."""
    return item.get("magnitude", item["consequence"])


def uniform(item):
    """Floor: every item scored alike, so greedy becomes cheapest-first (maximize coverage)."""
    return 1


def random_priority(item):
    """Deterministic pseudo-random baseline: priority is a stable hash of the id (no real signal).
    Uses crc32 -- NOT Python's salted hash() -- so it is identical across runs and PYTHONHASHSEED."""
    return 1 + (zlib.crc32(str(item["id"]).encode()) % 1_000_000)
