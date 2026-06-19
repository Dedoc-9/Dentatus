"""
toolkit -- a deterministic toolkit for uncertainty-aware resource allocation.

A toolkit for deciding where limited resources should go when you cannot attend to everything. It
does not determine what matters: it assumes a signal exists and tests whether that signal is a better
allocator than simpler policies under constrained budgets -- and it has a built-in way to prove
itself wrong (toolkit.benchmarks, toolkit.compare).

Smallest path:

    from toolkit import attention
    budget = attention.allocate(world, resources=1000)

Competition (which policy allocates best under stated conditions?):

    from toolkit import compare, future_surface, magnitude, random_priority
    print(compare([future_surface, magnitude, random_priority], worlds=1000).table())

The contract:

    score -> allocation
    allocation != truth

Run the proof:  PYTHONHASHSEED=0 python3 -m toolkit
"""
from .attention import attention, Field, Budget
from .allocation import allocate, captured
from . import policies, benchmarks, tournament, certify as _certify_mod, monitor as _monitor_mod, mutate as _mutate_mod
from .policies import future_surface, min_gate, weighted_product, magnitude, uniform, random_priority
from .tournament import compare, robustness
from .certify import certify, Certificate, diff_certificates, CertificateDiff
from .monitor import Monitor, baseline_fingerprint
from .certify import replay
from .mutate import mutate

__all__ = [
    "attention", "Field", "Budget",
    "allocate", "captured",
    "policies", "benchmarks", "tournament", "compare", "robustness", "certify", "Certificate", "diff_certificates", "CertificateDiff",
    "Monitor", "baseline_fingerprint", "replay", "mutate",
    "future_surface", "min_gate", "weighted_product", "magnitude", "uniform", "random_priority",
]
__version__ = "0.1.0"
