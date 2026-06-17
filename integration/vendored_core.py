"""
integration/vendored_core.py — an UNCOUPLED, standalone copy of the deterministic primitives.

This is a deliberate, self-contained re-implementation of the canonicalization + content-addressing used
across the workbench (chronicle / llm_toolkit / guard_server). It imports nothing from those packages. Its
sole purpose is to PROVE that the coupling choice is a convenience, not a correctness dependency: a team
that lifts a component out and vendors these ~20 lines gets byte-identical hashes (see parity_proof.py).

If this file and agent_core ever disagree, the parity proof fails loudly — that is the regression guard
that keeps "build for extraction" honest.
"""
import hashlib
import inspect
import json


def canon(obj):
    if isinstance(obj, bool):           return obj
    if isinstance(obj, float):          return format(obj, ".12g")
    if isinstance(obj, dict):           return {k: canon(obj[k]) for k in sorted(obj)}
    if isinstance(obj, (list, tuple)):  return [canon(x) for x in obj]
    return obj


def canonical_bytes(obj):
    return json.dumps(canon(obj), sort_keys=True, separators=(",", ":")).encode("utf-8")


def state_hash(obj):
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def source_hash(*fns):
    src = "\n--\n".join(inspect.getsource(f) for f in fns)
    return hashlib.sha256(src.encode("utf-8")).hexdigest()[:16]
