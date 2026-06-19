"""intervention/_wb.py — path shim. Lets DEMOS/TESTS wire real sources (causal_runtime's coupling_discovery,
the AetherPulse kernel) without the core modules importing across siblings. Core stays decoupled-by-data."""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def coupling_discovery():
    d = os.path.join(ROOT, "causal_runtime")
    if d not in sys.path:
        sys.path.insert(0, d)
    import coupling_discovery as cd  # noqa
    return cd


def aetherpulse_kernel():
    d = os.path.join(ROOT, "AetherPulse")
    if d not in sys.path:
        sys.path.insert(0, d)
    import kernel as k  # noqa
    return k
