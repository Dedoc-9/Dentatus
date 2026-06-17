"""
llm_toolkit/agent_core.py — a deterministic, content-addressed Agent State Machine.

Part of the Dentatus/Chronicle workbench. Philosophy: "build for extraction, not just execution." This
module is standalone — Python standard library only — and contains the content-addressing, hash-chaining,
attestation, profiling, and replay-court primitives that the rest of the toolkit composes.

WHAT THIS GUARANTEES (and what it does not)
  An LLM-driven workflow is a sequence of state transitions. Each transition is identified by the SHA-256
  hash of its full contents and linked to its predecessor, so the *record* of what happened is unforgeable,
  ordered, and reproducible bit-for-bit on any host. It does NOT guarantee the LLM's output was correct,
  smart, or safe in any absolute sense — only that the transition (the exact prompt in, the exact tokens
  out, the guardrails enforced at that instant) is 100% untampered and cryptographically replayable.
  Integrity is not truth.

DETERMINISM HAZARDS THIS CLOSES
  * Randomized iteration order  -> sorted-key canonical serialization + PYTHONHASHSEED=0 guard.
  * Float reassociation drift   -> token logprobs / eval scores canonicalized to a fixed decimal string.
  * Non-deterministic I/O       -> handled by the capture seam (see agent_capture.py), not here.
"""
import hashlib
import hmac
import inspect
import json
import os
import sys
import time

GENESIS = "0" * 64


# ----------------------------------------------------------------------------- determinism guard
def require_deterministic_hashing(component="llm_toolkit"):
    """Fail fast unless launched with PYTHONHASHSEED=0. Bit-identical hashing across processes/machines is
    the entire premise of the replay court; refuse to produce a ledger under a randomized seed so a user
    never trusts a chain they cannot reproduce elsewhere."""
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write(
            "\n[%s] REFUSING TO RUN: PYTHONHASHSEED is not 0.\n"
            "  Reproducible hashing is required for the replay court.\n"
            "  Re-run as:  PYTHONHASHSEED=0 python3 <script>.py\n\n" % component)
        raise SystemExit(2)


# ----------------------------------------------------------------------------- canonicalization
def _canon(obj):
    """Recursive, platform-stable canonicalization. Floats (logprobs, alignment scores) collapse to a
    fixed 12-significant-digit decimal so GPU/SIMD reassociation drift cannot fork the hash; dict keys are
    sorted so iteration order is irrelevant."""
    if isinstance(obj, bool):           return obj
    if isinstance(obj, float):          return format(obj, ".12g")
    if isinstance(obj, dict):           return {k: _canon(obj[k]) for k in sorted(obj)}
    if isinstance(obj, (list, tuple)):  return [_canon(x) for x in obj]
    return obj


def canonical_bytes(obj):
    return json.dumps(_canon(obj), sort_keys=True, separators=(",", ":")).encode("utf-8")


def state_hash(obj):
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def source_hash(*fns):
    """Bind the ACTUAL transition / guard logic by source text. Any edit to a rule changes this hash, so an
    auditor can prove the logic they run is the logic that produced the record ('rules didn't change')."""
    src = "\n--\n".join(inspect.getsource(f) for f in fns)
    return hashlib.sha256(src.encode("utf-8")).hexdigest()[:16]


# ----------------------------------------------------------------------------- attestation (stdlib)
class HmacSigner:
    """Symmetric attestation. Zero dependencies; the key-holder signs and verifies. For third-party,
    verify-without-forge attestation use the Ed25519 backend in agent_guard.py."""
    algo = "hmac-sha256"

    def __init__(self, secret):
        self._secret = secret if isinstance(secret, bytes) else secret.encode()

    def _mac(self, message):
        return hmac.new(self._secret, message, hashlib.sha256).hexdigest()

    def sign(self, message):
        return self._mac(message)

    def verify(self, message, sig):
        try:
            return hmac.compare_digest(self._mac(message), sig)
        except Exception:
            return False


# ----------------------------------------------------------------------------- profiling
class Profiler:
    """Minimal wall-clock profiler. The toolkit's selling point is that the canonical-hashing layer is
    negligible next to LLM network/inference flight time; this makes that measurable rather than asserted."""
    def __init__(self):
        self.spans = {}

    def time(self, label, fn, *a, **k):
        t0 = time.perf_counter()
        out = fn(*a, **k)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        self.spans.setdefault(label, []).append(dt_ms)
        return out, dt_ms

    def total_ms(self, label):
        return sum(self.spans.get(label, []))

    def report(self):
        return {k: round(sum(v), 4) for k, v in self.spans.items()}


def profiled(label, profiler):
    """Decorator form of Profiler.time for a fixed label/profiler."""
    def deco(fn):
        def wrap(*a, **k):
            out, _ = profiler.time(label, fn, *a, **k)
            return out
        return wrap
    return deco


# ----------------------------------------------------------------------------- the state machine
class TransitionRefused(Exception):
    """Raised when a guard refuses a transition — the machine fails closed and does not commit."""


class AgentStateMachine:
    """Append-only, hash-chained agent ledger. Stateless transition logic in, content-addressed receipts
    out. `signer` is any object with .sign(bytes)->hex and .algo (HmacSigner here, Ed25519Signer from
    agent_guard.py for third-party audit). `guard_fn(inputs, outputs) -> bool` is a precommitted clamp:
    if it returns False the transition is REFUSED and nothing is appended (fail-closed rollback)."""

    def __init__(self, signer, ruleset_h, prev_hash=GENESIS, seq=0):
        self.signer = signer if hasattr(signer, "sign") else HmacSigner(signer)
        self.ruleset_h = ruleset_h
        self.prev = prev_hash
        self.seq = seq

    def commit(self, step_id, inputs, outputs, guard_fn):
        if not guard_fn(inputs, outputs):
            raise TransitionRefused("step %s violates a precommitted guardrail; state NOT committed" % step_id)
        frame = {"seq": self.seq, "step_id": step_id, "inputs": inputs, "outputs": outputs,
                 "ruleset_hash": self.ruleset_h, "prev": self.prev}
        sh = state_hash(frame)
        committed = hashlib.sha256(("%s|%s" % (sh, self.prev)).encode()).hexdigest()
        sig = self.signer.sign(committed.encode())
        receipt = {"frame": frame, "state_hash": sh, "committed_hash": committed,
                   "signature": sig, "algo": self.signer.algo}
        self.prev = committed
        self.seq += 1
        return receipt


# ----------------------------------------------------------------------------- the replay court
class Verdict:
    def __init__(self): self.ok = True; self.reason = None; self.at = None
    def fail(self, reason, at): self.ok = False; self.reason = reason; self.at = at; return self


def audit_chain(ledger, verifier, transition_fn, guard_fn):
    """Re-derive every transition on a separate machine. For each receipt, in order, prove: chain link,
    seq continuity, ruleset binding, bit-exact replay of transition_fn(inputs), guard re-check, and the
    re-derived committed-hash + signature. Names the exact step on first failure.

    `transition_fn(inputs) -> outputs` MUST be deterministic; route any LLM/clock/IO through the capture
    seam (agent_capture.py) so replay returns captured values instead of hitting the live model."""
    v = Verdict()
    verifier = verifier if hasattr(verifier, "verify") else HmacSigner(verifier)
    running = source_hash(transition_fn, guard_fn)
    prev = GENESIS
    seq = 0
    for r in ledger:
        f = r["frame"]
        if f["prev"] != prev or f["seq"] != seq:
            return v.fail("CHAIN broken (insertion/deletion/reorder)", seq)
        if f["ruleset_hash"] != running:
            return v.fail("RULESET changed (transition/guard logic differs from record)", f["seq"])
        actual = transition_fn(f["inputs"])
        if canonical_bytes(actual) != canonical_bytes(f["outputs"]):
            return v.fail("REPLAY drift (outputs not reproducible from inputs)", f["seq"])
        if not guard_fn(f["inputs"], actual):
            return v.fail("GUARDRAIL breach on replay", f["seq"])
        sh = state_hash({"seq": f["seq"], "step_id": f["step_id"], "inputs": f["inputs"],
                         "outputs": actual, "ruleset_hash": running, "prev": prev})
        committed = hashlib.sha256(("%s|%s" % (sh, prev)).encode()).hexdigest()
        if committed != r["committed_hash"]:
            return v.fail("TAMPER (content hash mismatch)", f["seq"])
        if not verifier.verify(committed.encode(), r["signature"]):
            return v.fail("TAMPER (signature mismatch / wrong key)", f["seq"])
        prev = r["committed_hash"]
        seq += 1
    return v


def print_verdict(v, n):
    if v.ok:
        print("  VERIFIED -- %d transitions replayed bit-for-bit, chain intact, rules unchanged, untampered." % n)
    else:
        print("  REJECTED: %s  (at step seq %s)" % (v.reason, v.at))
    return 0 if v.ok else 1
