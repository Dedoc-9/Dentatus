"""
game/observability/integrity.py — EXP-523 Validity Witness (Fork omega).

Closes Ghost #5. The engine H_t = HASH(Z ⊕ S ⊕ W ⊕ t) is the GEOMETRIC identity; it does NOT encode the
SPRT validity class (EXP-309: FULL_VALID / LOD_RELAXED / INVALID). So a LOD_RELAXED state (a predicate
bypassed because the viewer is far -- level-of-detail) hashes identically to a FULL_VALID state of the
same geometry: a coarsened view could claim full integrity.

Containment (already true): Gamma_309 -- the only LOD_RELAXED producer -- is NOT reachable from the
dentatus.* facade, and the Series-500 firewall (api.observe) only ever mints FULL_VALID. So no clean-room
path can stamp H_verified on a relaxed state today. This module CLOSES the hole rather than merely
relying on that containment: it binds the validity class to the verified address.

    verified_address(mu):
        INVALID      -> None                         (no admissible address)
        FULL_VALID   -> H_t                           (UNCHANGED -> backward compatible with EXP-602)
        LOD_RELAXED  -> HASH(H_t ⊕ class ⊕ pv)        (a DISTINCT address that records the bypass)

A relaxed state therefore can never share an address with a full-valid one -> no integrity laundering
across level-of-detail. Engine FROZEN (no _compute_H change); core facade only.
"""
import os, sys, hashlib

_HERE = os.path.dirname(os.path.abspath(__file__))
_REALITY = os.path.dirname(os.path.dirname(_HERE))
if _REALITY not in sys.path:
    sys.path.insert(0, _REALITY)
from dentatus import core as _core

PROTOCOL = "exp523-v1"
VALID_CLASSES = ("FULL_VALID", "LOD_RELAXED", "INVALID")


def _class_of(mu, override=None):
    vc = override if override is not None else getattr(mu, "validity_class", "FULL_VALID")
    if vc not in VALID_CLASSES:
        raise ValueError("unknown validity_class %r" % vc)
    return vc


def verified_address(mu, validity_class=None):
    """The integrity-bound verified address. FULL_VALID -> plain H_t (backward compatible);
    LOD_RELAXED -> a distinct hash binding the bypass; INVALID -> None."""
    vc = _class_of(mu, validity_class)
    if vc == "INVALID":
        return None
    if not mu._sealed:
        mu.seal()
    if vc == "FULL_VALID":
        return mu.H
    payload = "\x1f".join([mu.H, vc, PROTOCOL])
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def integrity_witness(mu, validity_class=None):
    """Full witness: the geometric H_t, the validity class, and the integrity-bound address.
    Makes the relaxation auditable (which predicates were bypassed is recoverable from the class)."""
    vc = _class_of(mu, validity_class)
    if not mu._sealed and vc != "INVALID":
        mu.seal()
    return {"protocol": PROTOCOL, "H_geometric": (None if vc == "INVALID" else mu.H),
            "validity_class": vc, "verified_address": verified_address(mu, vc),
            "is_full_integrity": vc == "FULL_VALID"}


def addresses_distinct(mu_full, mu_relaxed):
    """True iff a full-valid and a relaxed state of identical geometry get DISTINCT addresses
    (the property that closes the laundering hole)."""
    return verified_address(mu_full, "FULL_VALID") != verified_address(mu_relaxed, "LOD_RELAXED")
