"""
stasis/drift.py — the Divergence Ledger: distinguish a LIE from NOISE, without crashing the system.

The naive contract "replay must match 100% or fail" is too fragile for a real cloud LLM: GPU float
reassociation can shift a logprob without changing a single decision. But you cannot tell "hardware noise"
from "subtle logic error" by staring at differing bytes — both just differ. `stasis` resolves this with the
workbench's own spine, the EXACT-GATE / OBSERVABLE split:

  * if the GATED fields differ (the integer/string facts that decide the outcome) -> LOGIC_ERROR -> FAIL.
    The decision changed; that is not noise, it is a different computation (and `elenchus` would catch it).
  * if the gates are identical but some OBSERVABLE field differs -> OBSERVABLE_DRIFT -> WARN. The decision
    is unchanged; the divergence is benign and is LOGGED (e.g. fed to `assay` as a quality signal), not
    treated as a security breach.
  * if nothing differs -> PASS.

HONEST BOUND: "OBSERVABLE_DRIFT" means *the gated decision is unchanged while some observable differs*. It
does NOT prove the cause was hardware (it could be any benign nondeterministic field). It proves the
DECISION is identical — which is exactly the thing that matters, because observables never gate. A verdict
is returned; the system is never halted by drift.

Imports stasis.canon read-only.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canon import canonicalize

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
_MISSING = object()


def _get(d, dotted):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return _MISSING
        cur = cur[part]
    return cur


def classify(expected, actual, gate_fields):
    """Compare two results. `gate_fields` are the dotted paths that DECIDE the outcome (exact gates).
    Returns a StasisVerdict: {verdict, event}. Never raises on a mismatch; never halts."""
    for f in sorted(gate_fields):
        if _get(expected, f) != _get(actual, f):
            return {"verdict": FAIL,
                    "event": {"type": "LOGIC_ERROR", "field": f,
                              "expected": _get(expected, f) if _get(expected, f) is not _MISSING else None,
                              "actual": _get(actual, f) if _get(actual, f) is not _MISSING else None}}
    # gates identical -> any remaining difference is non-deciding
    if canonicalize(expected, allow_float=True) != canonicalize(actual, allow_float=True):
        drifted = _first_observable_diff(expected, actual, set(gate_fields))
        return {"verdict": WARN, "event": {"type": "OBSERVABLE_DRIFT", "field": drifted}}
    return {"verdict": PASS, "event": None}


def _first_observable_diff(a, b, gate_fields, prefix=""):
    keys = sorted(set(list(a.keys()) + list(b.keys()))) if isinstance(a, dict) and isinstance(b, dict) else []
    for k in keys:
        path = "%s.%s" % (prefix, k) if prefix else k
        if path in gate_fields:
            continue
        av, bv = a.get(k, _MISSING), b.get(k, _MISSING)
        if isinstance(av, dict) and isinstance(bv, dict):
            deeper = _first_observable_diff(av, bv, gate_fields, path)
            if deeper:
                return deeper
        elif av != bv:
            return path
    return None


def feed_assay(verdict):
    """Map a StasisVerdict to a quality signal an auditor (e.g. `assay`) can record. PASS/WARN are quality
    observations; FAIL is a decision change that belongs in front of `elenchus`, not buried as 'noise'."""
    return {"signal": verdict["verdict"], "kind": (verdict["event"]["type"] if verdict["event"] else "match"),
            "field": (verdict["event"]["field"] if verdict["event"] else None)}
