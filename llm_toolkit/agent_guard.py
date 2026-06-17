"""
llm_toolkit/agent_guard.py — asymmetric, precommitted guardrails with a fail-closed execution clamp.

WHAT A GUARDRAIL IS HERE
  A set of hard safety/fairness constraints decided BEFORE deployment, e.g.
      * the output text must never match a forbidden-PII regex,
      * an alignment / safety score must stay >= a precommitted threshold.
  The constraint logic is SOURCE-HASHED into a `guardrail_hash` and that hash is signed with Ed25519, so
  a third-party auditor (holding only the public key) can prove which guardrails were in force at the time
  a transition was committed — and cannot forge a different set. (HMAC fallback keeps it stdlib-only when
  `cryptography` is unavailable; the fallback is loud that it gives up third-party non-repudiation.)

THE CLAMP
  At live time, `Guardrail.clamp(inputs, outputs)` is the fail-closed gate handed to the state machine.
  If the model output violates any precommitted constraint, the clamp returns False, the state machine
  REFUSES to commit, and the attempted transition is rolled back (never written to the ledger).

HONEST BOUNDARY
  A passing guardrail proves the output did not trip the precommitted constraints that were actually
  signed and enforced at that instant. It does not prove the output is wise or true. Integrity is not truth.
"""
import hashlib
import hmac
import re
import sys

import agent_core as core


# ----------------------------------------------------------------------------- Ed25519 (optional, graceful)
def _load_ed25519():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    return Ed25519PrivateKey, Ed25519PublicKey, InvalidSignature


def ed25519_available():
    try:
        _load_ed25519(); return True
    except Exception:
        return False


class Ed25519Signer:
    """Holds the PRIVATE key; distribute public_material() to auditors."""
    algo = "ed25519"

    def __init__(self, private_key_hex=None):
        Priv, _, _ = _load_ed25519()
        self._sk = Priv.generate() if private_key_hex is None else Priv.from_private_bytes(bytes.fromhex(private_key_hex))

    @classmethod
    def generate(cls):
        return cls()

    def public_material(self):
        from cryptography.hazmat.primitives import serialization
        return self._sk.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw).hex()

    def sign(self, message):
        return self._sk.sign(message).hex()

    def verify(self, message, sig):
        return Ed25519Verifier(self.public_material()).verify(message, sig)


class Ed25519Verifier:
    """Holds ONLY the public key. Proves authenticity; cannot forge. Give to third-party auditors."""
    algo = "ed25519"

    def __init__(self, public_key_hex):
        _, Pub, _ = _load_ed25519()
        self._pk = Pub.from_public_bytes(bytes.fromhex(public_key_hex))
        self._public_hex = public_key_hex

    def public_material(self):
        return self._public_hex

    def verify(self, message, sig):
        _, _, InvalidSignature = _load_ed25519()
        try:
            self._pk.verify(bytes.fromhex(sig), message)
            return True
        except InvalidSignature:
            return False
        except Exception:
            return False


def make_guard_signer(secret=None, private_key_hex=None, prefer_ed25519=True):
    """Pick the strongest available attestation. Prefers Ed25519 (third-party verify-without-forge); if
    `cryptography` is missing and a `secret` is given, degrades to HMAC with a loud warning rather than an
    unhandled ImportError."""
    if prefer_ed25519 and ed25519_available():
        return Ed25519Signer(private_key_hex)
    if secret is not None:
        if prefer_ed25519:
            sys.stderr.write("[llm_toolkit.guard] Ed25519 unavailable; falling back to HMAC. NOTE: HMAC is "
                             "symmetric -- third-party non-repudiation is LOST.\n")
        return core.HmacSigner(secret)
    raise RuntimeError("No Ed25519 backend and no HMAC secret provided. Install 'cryptography' or pass secret=.")


# ----------------------------------------------------------------------------- the guardrail
DEFAULT_PII_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",                                   # US SSN
    r"\b\d{16}\b",                                              # 16-digit card number
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",     # email address
]


class GuardrailViolation(Exception):
    def __init__(self, reasons):
        self.reasons = reasons
        super().__init__("; ".join(reasons))


def pii_clean(text, patterns=DEFAULT_PII_PATTERNS):
    """True iff `text` contains none of the forbidden-PII patterns."""
    return not any(re.search(p, text or "") for p in patterns)


def score_ok(score, threshold):
    return float(score) >= float(threshold)


class Guardrail:
    """A precommitted, signed bundle of constraints. `guardrail_hash` binds the constraint SOURCE so the
    set enforced at commit time is provable later; `signature` attests that hash under make_guard_signer."""

    def __init__(self, alignment_threshold=0.85, pii_patterns=None, signer=None):
        self.alignment_threshold = alignment_threshold
        self.pii_patterns = list(pii_patterns) if pii_patterns is not None else list(DEFAULT_PII_PATTERNS)
        # bind the actual constraint logic + the configured threshold/patterns by hash
        self.guardrail_hash = hashlib.sha256(
            core.canonical_bytes({
                "logic": core.source_hash(pii_clean, score_ok, Guardrail.check),
                "alignment_threshold": float(alignment_threshold),
                "pii_patterns": self.pii_patterns,
            })).hexdigest()[:16]
        self.signer = signer
        self.signature = signer.sign(self.guardrail_hash.encode()) if signer is not None else None

    def check(self, inputs, outputs):
        """Return (ok, reasons). Pure; usable both at live time and on replay."""
        reasons = []
        text = outputs.get("response_text", "")
        if not pii_clean(text, self.pii_patterns):
            reasons.append("output contains forbidden PII")
        if not score_ok(outputs.get("alignment_score", 0.0), self.alignment_threshold):
            reasons.append("alignment_score %.3f below precommitted threshold %.2f"
                           % (float(outputs.get("alignment_score", 0.0)), self.alignment_threshold))
        return (len(reasons) == 0), reasons

    def clamp(self, inputs, outputs):
        """Fail-closed boolean gate for AgentStateMachine.commit(...). False -> refuse + roll back."""
        ok, _ = self.check(inputs, outputs)
        return ok

    def enforce(self, inputs, outputs):
        """Raising form, for callers that want the reasons surfaced explicitly."""
        ok, reasons = self.check(inputs, outputs)
        if not ok:
            raise GuardrailViolation(reasons)
        return True

    def attest_record(self):
        """The portable, signed statement of which guardrails were in force (store alongside the ledger)."""
        return {"guardrail_hash": self.guardrail_hash, "algo": getattr(self.signer, "algo", None),
                "signature": self.signature,
                "public_material": getattr(self.signer, "public_material", lambda: None)()}

    @staticmethod
    def verify_attestation(record, verifier):
        """Third-party check: does `signature` attest `guardrail_hash` under the given public verifier?"""
        if record.get("signature") is None:
            return False
        return verifier.verify(record["guardrail_hash"].encode(), record["signature"])
