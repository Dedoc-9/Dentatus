"""
airlock/membrane.py — the LLM→kernel membrane (transitions-only, kernel-agnostic).

The LLM is a PROPOSER; the kernel is the AUTHORITY; this is the membrane between them. Two laws, enforced
structurally (not by convention):

    telemetry ≠ control     observables (R_p, aether metrics) are computed but NEVER read by any gate
    intent    ≠ authority    claims / provenance (intent) never commit state; only mechanical checks do

A proposal is a typed object:

    p = { transition, claims, constraints, provenance, budget }

and crosses the membrane through a one-way pipeline:

    stasis canon  →  budget (fuel)  →  SHADOW apply  →  validate  →  witness (quorum)  →  COMMIT (shard)

Every gate that rejects emits a content-addressed (optionally signed) proof-of-rejection shard into an
append-only ledger and leaves state UNCHANGED. The shadow apply is pure (no write-back); only an admissible
candidate is promoted. `R_p = ‖Δ_proposed − Δ_real‖` (the proposal residual = the LLM's "ghost") is captured
as telemetry and is NEVER a gate. `integrity ≠ truth`: a commit proves the transition was applied exactly and
admissibly, never that it was a good idea.

The deterministic kernel is injected as an `adapter` (see adapters.py) exposing: ALLOWED_OPS, cost(txn),
apply(world, txn), delta_norm(world, world2), state_hash(world), validate(world2, constraints) and
residual(world2, claims). Stdlib + chronicle/stasis (read-only).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _wb as C

core = C.core
canon = C.canon

GATES = ("CANON", "SCHEMA", "BUDGET", "APPLY", "CONSTRAINT", "WITNESS")


class Ledger:
    """Append-only commit + rejection ledgers. Each record is content-addressed and hash-chained via `prev`."""
    def __init__(self):
        self.commits = []
        self.rejections = []

    def head(self):
        return self.commits[-1]["shard_hash"] if self.commits else ("0" * 64)


def _shard(kind, fields, signer=None):
    rec = {"event": kind, **fields}
    rec["shard_hash"] = core.state_hash(rec)
    if signer is not None:
        rec["signature"] = signer.sign(core.canonical_bytes(rec))
        rec["algo"] = signer.algo
    return rec


def _reject(ledger, gate, reason, proposal_hash, prev, telemetry, signer):
    shard = _shard("REJECT", {"gate": gate, "reason": reason, "prev": prev,
                              "proposal_hash": proposal_hash, "telemetry": telemetry}, signer)
    ledger.rejections.append(shard)
    return {"ok": False, "gate": gate, "reason": reason, "shard": shard, "telemetry": telemetry, "world": None}


def propose(world, proposal, adapter, ledger=None, witnesses=None, k=None, signer=None):
    """Run a single proposal through the membrane. `witnesses` is an optional list of callables
    (world, txn) -> candidate_hash that INDEPENDENTLY re-derive the candidate (reproduction-admission);
    commit requires ≥k of them to match. Returns a COMMIT or REJECT result; state mutates ONLY on commit."""
    import hashlib
    ledger = ledger if ledger is not None else Ledger()
    prev = ledger.head()
    txn = proposal.get("transition")
    budget = proposal.get("budget", {})

    # 1) CANON — well-formed under the declared schema (no floats/sets/non-str keys; stasis Iron Canon).
    #    canonicalizing the proposal both validates it AND yields its stable hash; a failure IS the CANON reject.
    try:
        phash = canon.canon_hash(proposal)
    except canon.CanonizationError as e:
        phash = "noncanon:" + hashlib.sha256(repr(proposal).encode()).hexdigest()
        return _reject(ledger, "CANON", str(e), phash, prev, {}, signer)
    if not isinstance(txn, dict) or txn.get("op") not in adapter.ALLOWED_OPS:
        return _reject(ledger, "SCHEMA", "unknown or missing op", phash, prev, {}, signer)

    # 2) BUDGET — fuel: bounded cost (declared op budget). Magnitude budget checked post-shadow (needs Δ).
    cost = adapter.cost(txn)
    if "max_cost" in budget and cost > budget["max_cost"]:
        return _reject(ledger, "BUDGET", "cost %d > max_cost %d" % (cost, budget["max_cost"]), phash, prev, {}, signer)

    # 3) SHADOW APPLY — pure; no write-back. Invalid op application is a mechanical reject.
    try:
        world2 = adapter.apply(world, txn)
    except adapter.ApplyError as e:
        return _reject(ledger, "APPLY", str(e), phash, prev, {}, signer)
    delta = adapter.delta_norm(world, world2)
    if "max_delta" in budget and delta > budget["max_delta"]:
        return _reject(ledger, "BUDGET", "delta %d > max_delta %d" % (delta, budget["max_delta"]), phash, prev, {}, signer)

    # 4) VALIDATE — hard admissibility (constraints on the candidate). Mechanical only.
    ok, why = adapter.validate(world2, proposal.get("constraints", {}))
    # ---- TELEMETRY (computed here, used by NOTHING below: telemetry ≠ control) ----
    R_p = adapter.residual(world2, proposal.get("claims", {}))
    telemetry = {"R_p": R_p, "cost": cost, "delta": delta, "post_hash_preview": None}
    if not ok:
        return _reject(ledger, "CONSTRAINT", why, phash, prev, telemetry, signer)

    # 5) HASH the candidate
    h2 = adapter.state_hash(world2)
    telemetry["post_hash_preview"] = h2[:16]

    # 6) WITNESS — reproduction admission: ≥k independent re-derivations must match (witness ≠ controller).
    if witnesses:
        need = k if k is not None else len(witnesses)
        agree = sum(1 for w in witnesses if w(world, txn) == h2)
        if agree < need:
            return _reject(ledger, "WITNESS", "reproduction %d/%d < k=%d" % (agree, len(witnesses), need),
                           phash, prev, telemetry, signer)

    # 7) COMMIT — promote the candidate; emit a hash-chained, optionally-signed commit shard.
    shard = _shard("COMMIT", {"prev": prev, "txn": txn, "txn_hash": canon.canon_hash(txn),
                              "pre_hash": adapter.state_hash(world), "post_hash": h2,
                              "telemetry": telemetry,
                              "provenance": proposal.get("provenance", {})}, signer)
    ledger.commits.append(shard)
    return {"ok": True, "gate": "COMMIT", "world": world2, "shard": shard, "telemetry": telemetry}
