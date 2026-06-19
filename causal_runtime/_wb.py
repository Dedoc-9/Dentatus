"""causal_runtime/_wb.py — path shim. Adds sibling/app dirs so DEMOS can wire real sources (AetherPulse kernel,
consequence graph) WITHOUT the core modules (field/runtime/freshness) importing across siblings. Core stays
decoupled-by-data; only demos/tests use this. Named _wb to avoid the _cores collision (see airlock)."""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(modname, relpath):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(ROOT, relpath))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def aetherpulse_kernel():
    # AetherPulse/kernel.py imports its own _cores via package-relative path; load the package dir on sys.path
    apdir = os.path.join(ROOT, "AetherPulse")
    if apdir not in sys.path:
        sys.path.insert(0, apdir)
    import kernel as k          # noqa
    return k


def consequence_graph():
    cdir = os.path.join(ROOT, "consequence")
    if cdir not in sys.path:
        sys.path.insert(0, cdir)
    import graph as g           # noqa
    return g


def dini_compass():
    ddir = os.path.join(ROOT, "dini")
    if ddir not in sys.path:
        sys.path.insert(0, ddir)
    import compass as d        # noqa  (compass self-adds the chronicle core to sys.path)
    return d
