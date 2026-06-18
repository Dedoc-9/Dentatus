"""
stasis/canon.py — the Iron Canon: a strict canonical boundary between the chaos zone and the order zone.

`stasis` does not make the cloud deterministic (impossible) or eliminate latency (physics). It builds an
opinionated boundary so that whatever enters `fuel` / `tessera` / `quorum` is already canonical and integer-
clean. `canonicalize()` REJECTS the types that have no stable byte representation, and normalizes the rest,
so two logically identical inputs always produce the identical SHA-256.

What it rejects (raise CanonizationError):
  * float (by default) — floats must not enter a hash; pass allow_float=True only for explicitly captured,
    non-gated observables, and even then NaN/inf are refused;
  * set / frozenset — no canonical order;
  * raw bytes — ambiguous in a JSON canon (hex-encode to str first);
  * non-string dict keys — key order/representation would be unstable.
What it normalizes: dict key order (sorted), number/format via the frozen `chronicle` canonical serializer.

HONEST BOUND: identical bytes are guaranteed across OS / process / time *for the supported types*, because
this reuses `chronicle.core.canonical_bytes`. "Across languages" is only true if the other language
implements the SAME canon spec — this module is the spec for Python, not a cross-language guarantee by fiat.

Imports chronicle read-only (Sibling Law).
"""
import os
import sys
import hashlib

_WB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
import core                                                  # chronicle/core.py


class CanonizationError(Exception):
    pass


def _check(obj, allow_float, path="$"):
    if isinstance(obj, bool) or isinstance(obj, int) or obj is None or isinstance(obj, str):
        return
    if isinstance(obj, float):
        if not allow_float:
            raise CanonizationError("%s: float not allowed in canonical bytes (use integers/fixed-point)" % path)
        if obj != obj or obj in (float("inf"), float("-inf")):
            raise CanonizationError("%s: non-finite float %r" % (path, obj))
        return
    if isinstance(obj, (list, tuple)):
        for i, x in enumerate(obj):
            _check(x, allow_float, "%s[%d]" % (path, i))
        return
    if isinstance(obj, dict):
        for k in obj:
            if not isinstance(k, str):
                raise CanonizationError("%s: dict keys must be str for a stable canon, got %r" % (path, type(k).__name__))
            _check(obj[k], allow_float, "%s.%s" % (path, k))
        return
    if isinstance(obj, (set, frozenset)):
        raise CanonizationError("%s: set/frozenset has no canonical order; sort into a list first" % path)
    if isinstance(obj, (bytes, bytearray)):
        raise CanonizationError("%s: raw bytes are ambiguous in the JSON canon; hex-encode to str first" % path)
    raise CanonizationError("%s: unsupported type %r" % (path, type(obj).__name__))


def canonicalize(obj, allow_float=False):
    """Strict canonical bytes. Rejects ambiguous/non-deterministic types; normalizes the rest. Default is
    integer-clean (allow_float=False) so no float pollution reaches a hash."""
    _check(obj, allow_float)
    return core.canonical_bytes(obj)


def canon_hash(obj, allow_float=False):
    return hashlib.sha256(canonicalize(obj, allow_float)).hexdigest()


def is_canonical(obj, allow_float=False):
    """(ok, reason): does this object pass the Iron Canon without modification of meaning?"""
    try:
        canonicalize(obj, allow_float)
        return True, "canonical"
    except CanonizationError as e:
        return False, str(e)
