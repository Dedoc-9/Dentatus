"""
chronicle/signing.py — pluggable attestation backends.

Two answers to "who can verify, and who can forge":

  HmacSigner    (symmetric, stdlib)  — the key-holder signs AND verifies. Anyone who can verify can also
                                       forge. Fine for a single trust domain; needs secrets infra (KMS,
                                       Vault) and gives an auditor no independent guarantee.

  Ed25519Signer (asymmetric, libsodium via `cryptography`) — the PRIVATE key signs; the PUBLIC key only
                                       verifies. A third-party auditor holds the public key, can prove the
                                       log is authentic, and CANNOT forge an entry. This is the
                                       commercially-viable mode. Falls back gracefully if `cryptography`
                                       is not installed (import is lazy and isolated to this module).

Common interface (so core.Recorder / court.verify_chain are backend-agnostic):

    signer.sign(message: bytes) -> hex str
    verifier.verify(message: bytes, sig: hex str) -> bool
    signer.algo -> str    ("hmac-sha256" | "ed25519")
    signer.public_material() -> str | None   (what an auditor needs; None for HMAC)

The signed `message` is the committed_hash bytes — identical across backends — so a ledger can be
re-signed under a stronger backend without changing its content addresses or chain.
"""
import hmac
import hashlib
import sys

ALGO_HMAC = "hmac-sha256"
ALGO_ED25519 = "ed25519"


# ----------------------------------------------------------------------------- symmetric (stdlib)
class HmacSigner:
    algo = ALGO_HMAC

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

    def public_material(self):
        return None  # symmetric: there is nothing safe to publish; the verifier IS the forger


# A verify-only handle that still holds the secret (HMAC has no separable public half). verify() uses
# _mac directly, so blocking the public sign() does not break verification.
class HmacVerifier(HmacSigner):
    def sign(self, message):
        raise PermissionError("HmacVerifier is verify-only by convention")


# ----------------------------------------------------------------------------- asymmetric (optional)
def _load_ed25519():
    """Lazy import so the rest of the library stays stdlib-only when ed25519 isn't needed/installed."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey, Ed25519PublicKey)
        from cryptography.exceptions import InvalidSignature
        return Ed25519PrivateKey, Ed25519PublicKey, InvalidSignature
    except Exception as e:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "Ed25519 backend requires the 'cryptography' package (pip install cryptography). "
            "Use HmacSigner for a dependency-free symmetric fallback.") from e


def ed25519_available():
    try:
        _load_ed25519(); return True
    except Exception:
        return False


class Ed25519Signer:
    """Holds the PRIVATE key. Distribute the matching public key (public_material) to auditors."""
    algo = ALGO_ED25519

    def __init__(self, private_key_hex=None):
        Priv, _, _ = _load_ed25519()
        if private_key_hex is None:
            self._sk = Priv.generate()
        else:
            self._sk = Priv.from_private_bytes(bytes.fromhex(private_key_hex))

    @classmethod
    def generate(cls):
        return cls()

    def private_key_hex(self):
        from cryptography.hazmat.primitives import serialization
        raw = self._sk.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption())
        return raw.hex()

    def public_material(self):
        from cryptography.hazmat.primitives import serialization
        raw = self._sk.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        return raw.hex()

    def sign(self, message):
        return self._sk.sign(message).hex()

    def verify(self, message, sig):
        return Ed25519Verifier(self.public_material()).verify(message, sig)


class Ed25519Verifier:
    """Holds ONLY the public key. Can prove authenticity; cannot forge. Give this to third-party auditors."""
    algo = ALGO_ED25519

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


# ----------------------------------------------------------------------------- factory
def _warn(msg):
    sys.stderr.write("[chronicle.signing] %s\n" % msg)


def make_signer(spec, allow_fallback=True):
    """Build a signer from a small spec dict, e.g.
        {"algo": "hmac-sha256", "secret": "..."}
        {"algo": "ed25519", "private_key_hex": "..."}   (sign + verify)
        {"algo": "ed25519", "public_key_hex": "..."}    (verify only)

    Graceful degradation: if Ed25519 is requested but the `cryptography` package is unavailable, and a
    `secret` is present in the spec, this prints a gentle warning and falls back to the stdlib HMAC
    backend rather than raising an unhandled ImportError. The warning is loud about the consequence:
    HMAC is SYMMETRIC, so the fallback gives up third-party non-repudiation (the verifier can forge).
    Set allow_fallback=False to require Ed25519 and fail closed instead.
    """
    algo = spec.get("algo", ALGO_HMAC)
    if algo == ALGO_HMAC:
        return HmacSigner(spec["secret"])
    if algo == ALGO_ED25519:
        if not ed25519_available():
            if allow_fallback and spec.get("secret") is not None:
                _warn("Ed25519 requested but 'cryptography' is not installed; falling back to HMAC. "
                      "NOTE: HMAC is symmetric -- the verifier can forge, so third-party "
                      "non-repudiation is LOST. Install 'cryptography' to restore asymmetric audit.")
                return HmacSigner(spec["secret"])
            raise RuntimeError(
                "Ed25519 backend requires the 'cryptography' package (pip install cryptography), and no "
                "HMAC `secret` was provided to fall back to. Either install cryptography or pass a secret.")
        if spec.get("private_key_hex"):
            return Ed25519Signer(spec["private_key_hex"])
        if spec.get("public_key_hex"):
            return Ed25519Verifier(spec["public_key_hex"])
        return Ed25519Signer()  # fresh keypair
    raise ValueError("unknown algo %r" % algo)
