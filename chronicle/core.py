"""
chronicle/core.py — a verifiable decision recorder (the "flight recorder").

Stdlib-only core. Records consequential automated decisions into a hash-chained, attested ledger such
that an auditor can later REPLAY each decision bit-for-bit, prove the record was not altered, and prove
the rules that produced it are the rules that were recorded. Distilled from the Dentatus verification
discipline: deterministic content-addressing, rolling-hash chaining, precommitted invariants,
integrity-not-truth.

Attestation is PLUGGABLE (see signing.py): HMAC (symmetric, zero-dependency default) or Ed25519
(asymmetric — a third-party auditor verifies with the public key and cannot forge). The signed message
is the committed_hash, identical across backends, so the SAME ledger can be re-signed under a stronger
backend without changing any content address or chain link.

Persistence is PLUGGABLE (see store.py): pass any append-only LedgerStore and records are durably
appended as they are made; omit it to get receipts back in-process.

HONEST BOUNDARIES (stated, not hidden):
  * This proves a record is UNFORGED and EXACTLY REPRODUCIBLE and RULE-FAITHFUL. It does NOT claim the
    decision was correct or fair — only that it is honest and replayable. (Integrity is not truth.)
  * Floats are the enemy of bit-exactness. They are canonicalised to a fixed decimal string here; a real
    high-assurance deployment should keep committed decision values in integers / fixed-point.
  * Nondeterministic logic (clock/RNG/external reads) drifts on replay. Route those through capture.py
    so they become recorded inputs; verify_determinism() flags leaks before you trust a ledger.
"""
import hashlib, hmac, json, inspect

from signing import HmacSigner

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
    """Append-only, hash-chained decision recorder.

    signer : any object with .sign(bytes)->hex and .algo (see signing.py). A bytes/str is accepted as a
             shorthand for HmacSigner(secret), so existing callers keep working unchanged.
    store  : optional append-only LedgerStore (see store.py); when given, each receipt is durably
             appended, and prev/seq are initialised from the store's head/seq for safe resumption.
    """

    def __init__(self, signer, ruleset_h, prev_hash=None, seq=None, store=None):
        self.signer = signer if hasattr(signer, "sign") else HmacSigner(signer)
        self.ruleset_h = ruleset_h
        self.store = store
        if store is not None:
            self.prev = store.head() if prev_hash is None else prev_hash
            self.seq = store.seq() if seq is None else seq
        else:
            self.prev = GENESIS if prev_hash is None else prev_hash
            self.seq = 0 if seq is None else seq

    def record(self, decision_id, inputs, outputs, invariant_fn):
        if not invariant_fn(inputs, outputs):                     # fail-closed: refuse to log an unsafe decision
            raise InvariantViolation("decision %s breaches a precommitted invariant" % decision_id)
        frame = {"seq": self.seq, "decision_id": decision_id, "inputs": inputs, "outputs": outputs,
                 "ruleset_hash": self.ruleset_h, "prev": self.prev}
        sh = state_hash(frame)                                    # content address of this decision
        committed = hashlib.sha256(("%s|%s" % (sh, self.prev)).encode()).hexdigest()   # chain link
        sig = self.signer.sign(committed.encode())                # attestation (HMAC or Ed25519)
        receipt = {"frame": frame, "state_hash": sh, "committed_hash": committed,
                   "signature": sig, "algo": self.signer.algo}
        if self.store is not None:
            self.store.append(receipt)
        self.prev = committed; self.seq += 1
        return receipt
