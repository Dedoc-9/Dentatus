"""
toolkit — a deterministic toolkit for uncertainty-aware resource allocation.

A toolkit for deciding where limited resources should go when you cannot attend to everything.
It does not discover importance; it allocates resources according to supplied estimates of
importance — and it has a built-in way to prove itself wrong (toolkit.benchmarks).

The whole external surface is three lines:

    from toolkit import attention
    field  = attention.observe(world)
    budget = field.allocate(resources=1000, policy="future_surface")

The contract:

    score -> allocation
    allocation != truth

Run the proof:  PYTHONHASHSEED=0 python3 -m toolkit
"""
from .attention import attention, Field, Budget
from .allocation import allocate, captured
from . import policies, benchmarks
from .policies import future_surface, magnitude, uniform

__all__ = [
    "attention", "Field", "Budget",
    "allocate", "captured",
    "policies", "benchmarks",
    "future_surface", "magnitude", "uniform",
]
__version__ = "0.1.0"
