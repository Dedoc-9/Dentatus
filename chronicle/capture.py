"""
chronicle/capture.py — lower the "determinism tax" so adopters don't re-architect their app.

The objection: real decision code calls the clock, a random source, a database, an external API. That
code is NOT deterministic, so naive replay drifts. The usual "fix" — rewrite everything to be pure — is
the adoption killer.

The pattern here (cassette / record-replay, the same idea as VCR for HTTP) flips it: you DON'T purify
the logic. At RECORD time you let the side-effects run and you CAPTURE their results into the decision's
inputs. At REPLAY time the captured values are fed back, so the exact same logic reproduces the exact
same outputs — bit-for-bit — without ever touching the clock/DB/network again.

So the only discipline an adopter must accept is: route nondeterministic reads through a Capture handle.
Their business logic is otherwise untouched.

    cap = Capture()                          # record mode
    now = cap.clock("decision_ts", lambda: time.time())
    score = cap.external("bureau_score", lambda: bureau.get(ssn))
    coin  = cap.rand("nonce", lambda: random.random())
    inputs = cap.sealed_inputs(business_inputs)   # business inputs + every captured value, canonical

    # ... later, on the auditor's machine ...
    cap2 = Capture.replay(frame["inputs"])   # replay mode: same calls return the recorded values
    now   = cap2.clock("decision_ts", lambda: time.time())   # returns the RECORDED ts, clock untouched

`verify_determinism(fn, inputs, n=3)` is a cheap guard that runs pure logic repeatedly and reports any
nondeterminism the adopter forgot to route through Capture — a leak-detector, not a fixer.
"""
import core

_CAPTURE_KEY = "_captured"


class CaptureError(Exception):
    pass


class Capture:
    """Record nondeterministic reads at record time; return the recorded values at replay time.

    Captured values live under inputs["_captured"][label], canonicalised, so they are part of the
    content-addressed frame and the hash chain — tampering with a captured value breaks the ledger.
    """

    def __init__(self):
        self._mode = "record"
        self._cap = {}

    @classmethod
    def replay(cls, sealed_inputs):
        c = cls()
        c._mode = "replay"
        c._cap = dict(sealed_inputs.get(_CAPTURE_KEY, {}))
        return c

    def _get(self, label, producer):
        if self._mode == "replay":
            if label not in self._cap:
                raise CaptureError("no recorded value for %r (logic took an un-captured branch on replay)" % label)
            return self._cap[label]
        val = producer()
        # canonicalise immediately so what we replay == what we hashed
        canon = core._canon(val)
        self._cap[label] = canon
        return canon

    # semantic aliases — all identical mechanics, named for intent / auditability
    def clock(self, label, producer):     return self._get(label, producer)   # time.time(), datetime.now()
    def rand(self, label, producer):      return self._get(label, producer)   # random/uuid/secrets
    def external(self, label, producer):  return self._get(label, producer)   # DB read, HTTP GET, feature store
    def value(self, label, producer):     return self._get(label, producer)   # anything else nondeterministic

    def sealed_inputs(self, business_inputs):
        """Combine the caller's business inputs with everything captured, into the frame's `inputs`."""
        out = dict(business_inputs)
        out[_CAPTURE_KEY] = dict(self._cap)
        return out


def captured_view(sealed_inputs):
    """Read-only access to what was captured (for audit display)."""
    return dict(sealed_inputs.get(_CAPTURE_KEY, {}))


def verify_determinism(fn, inputs, n=3):
    """Leak detector: run `fn(inputs)` n times; return (ok, detail). If outputs differ across runs the
    logic still has an un-captured nondeterministic source. Cheap to run in CI before trusting replay."""
    first = core.canonical_bytes(fn(inputs))
    for i in range(1, n):
        if core.canonical_bytes(fn(inputs)) != first:
            return False, "nondeterministic output on run %d/%d — an external read is not routed through Capture" % (i + 1, n)
    return True, "deterministic across %d runs" % n
