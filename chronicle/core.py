"""
chronicle/core.py — a verifiable decision recorder (the "flight recorder").

Stdlib-only. Records consequential automated decisions into a hash-chained, attested ledger such that an
auditor can later REPLAY each decision bit-for-bit, prove the record was not altered, and prove the rules
that produced it are the rules that were recorded. Distilled from the Dentatus verification discipline:
deterministic content-addressing, rolling-hash chaining, precommitted invariants, integrity-not-truth.

HONEST BOUNDARIES (stated, not hidden):
  * Attestation here is HMAC (symmetric): the key-holder can verify and detect tampering. For THIRD-PARTY
    non-repudiation (an auditor who must NOT be able to forge), swap the HMAC for an Ed25519 signature —
    the same pattern proven in the parent project's registry signing. Left as HMAC to stay dependency-free.
  * This proves a record is UNFORGED and EXACTLY REPRODUCIBLE and RULE-FAITHFUL. It does NOT claim the
    decision was correct or fair — only that it is honest and replayable. (Integrity is not truth.)
  * Floats are the enemy of bit-exactness. They are canonicalised to a fixed decimal string here; a real
    high-assurance deployment should keep committed decision values in integers / fixed-point.
"""
import hashlib, hmac, json, inspect

GENESIS = "0" * 64


class InvariantViolation(Exception):
    """Raised when a decision would breach a precommitted invariant — the recorder refuses to log it."""


def _canon(obj):
    # recursive, platform-stable canonicalisation (floats -> fixed decimal, dict keys sorted)
    if isinstance(obj, bool):       return obj
    if isinstance(obj, float):      return format(obj, ".12g")
    if isinstance(obj, dict):       return {k: _canon(obj[k]) for k in sorted(obj)}
    if isinstance(obj, (list, tuple)): return [_canon(x) for x in obj]
    return obj


def canonical_bytes(obj):
    return json.dumps(_canon(obj), sort_keys=True, separators=(",", ":")).encode("utf-8")


def state_hash(obj):
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def ruleset_hash(*fns):
    """Bind the ACTUAL decision + invariant logic by source. Any edit to a rule changes this hash, so the
    court can prove the logic it runs is the logic that was recorded (closes the 'rules didn't change' gap)."""
    src = "\n--\n".join(inspect.getsource(f) for f in fns)
    return hashlib.sha256(src.encode("utf-8")).hexdigest()[:16]


class Recorder:
    """Append-only, hash-chained decision recorder."""

    def __init__(self, secret, ruleset_h, prev_hash=GENESIS, seq=0):
        self.secret = secret if isinstance(secret, bytes) else secret.encode()
        self.ruleset_h = ruleset_h
        self.prev = prev_hash
        self.seq = seq

    def record(self, decision_id, inputs, outputs, invariant_fn):
        if not invariant_fn(inputs, outputs):                     # fail-closed: refuse to log an unsafe decision
            raise InvariantViolation("decision %s breaches a precommitted invariant" % decision_id)
        frame = {"seq": self.seq, "decision_id": decision_id, "inputs": inputs, "outputs": outputs,
                 "ruleset_hash": self.ruleset_h, "prev": self.prev}
        sh = state_hash(frame)                                    # content address of this decision
        committed = hashlib.sha256(("%s|%s" % (sh, self.prev)).encode()).hexdigest()   # chain link
        sig = hmac.new(self.secret, committed.encode(), hashlib.sha256).hexdigest()    # attestation
        receipt = {"frame": frame, "state_hash": sh, "committed_hash": committed, "signature": sig}
        self.prev = committed; self.seq += 1
        return receipt
