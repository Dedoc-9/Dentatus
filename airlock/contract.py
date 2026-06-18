"""
airlock/contract.py — the deterministic-adapter CONTRACT (the membrane's interface language).

Any reality that wants to be governed by the membrane must speak this language. An adapter is valid iff it
exposes the names below with the right shapes. Keeping this explicit is what turns the system from a pile of
"AI features" into a platform where new realities (physics, config, repo, runtime, deployments, proofs) plug
in without changing the membrane.

Required adapter surface:
    ALLOWED_OPS : tuple[str]                       the declared, bounded transition vocabulary
    ApplyError  : Exception subclass               raised on an inadmissible application (→ APPLY reject)
    cost(txn)            -> int                     fuel cost of a transition
    apply(world, txn)    -> world'                  PURE; never mutates `world`
    delta_norm(w, w')    -> int                     exact-integer ‖Δ‖ (for the magnitude budget)
    state_hash(world)    -> hex str                 content address of a world
    validate(w', cons)   -> (bool, str)             mechanical admissibility on the candidate
    residual(w', claims) -> int | None              R_p telemetry; verified-not-trusted; NEVER gates
"""
REQUIRED_CALLABLES = ("cost", "apply", "delta_norm", "state_hash", "validate", "residual")


class ContractError(Exception):
    pass


def validate_adapter(adapter):
    """Structural check that `adapter` speaks the membrane's interface language. Returns True or raises."""
    ops = getattr(adapter, "ALLOWED_OPS", None)
    if not isinstance(ops, tuple) or not ops or not all(isinstance(o, str) for o in ops):
        raise ContractError("ALLOWED_OPS must be a non-empty tuple[str]")
    err = getattr(adapter, "ApplyError", None)
    if not (isinstance(err, type) and issubclass(err, Exception)):
        raise ContractError("ApplyError must be an Exception subclass")
    for name in REQUIRED_CALLABLES:
        if not callable(getattr(adapter, name, None)):
            raise ContractError("adapter missing callable %r" % name)
    return True
