"""
toolkit -- a deterministic toolkit for uncertainty-aware resource allocation.

A toolkit for deciding where limited resources should go when you cannot attend to everything. It
does not determine what matters: it assumes a signal exists and tests whether that signal is a better
allocator than simpler policies under constrained budgets -- and it has a built-in way to prove
itself wrong (toolkit.benchmarks).

Smallest path:

    from toolkit import attention
    budget = attention.allocate(world, resources=1000)

The contract:

    score -> allocation
    allocation != truth

Run the proof:  PYTHONHASHSEED=0 python3 -m toolkit
"""
from .attention import attention, Field, Budget
from .allocation import allocate, captured
from . import policies, benchmarks
from .policies import future_surface, min_gate, weighted_product, magnitude, uniform

__all__ = [
    "attention", "Field", "Budget",
    "allocate", "captured",
    "policies", "benchmarks",
    "future_surface", "min_gate", "weighted_product", "magnitude", "uniform",
]
__version__ = "0.1.0"
