"""
forge/registry_signing.py — EXP-531 Cryptographic Registry Signing (boot airlock).

The fingerprint guard in EXP-530 proves a registry entry is INTERNALLY consistent (its bound matches its
licensed fingerprint). It does NOT prove the registry was AUTHORIZED: an attacker with write access could
replace constitution/INVARIANT_REGISTRY.json wholesale with malicious bounds AND recompute matching
fingerprints — every entry would self-verify. This module closes that hole with an asymmetric signature.

  • A detached Ed25519 signature (`INVARIANT_REGISTRY.sig`) is produced over the EXACT bytes of the
    registry by a holder of an authorized PRIVATE key. (Ed25519 per RFC 8032 is deterministic — same key
    + same bytes → same signature — consistent with the engine's determinism discipline.)
  • The server holds only PUBLIC keys, listed in `constitution/AUTHORIZED_KEYS.json`. At boot it verifies
    the signature against that allowlist BEFORE compiling a single clamp; failure raises
    RegistryCryptographicBreach and the server refuses to start (fail-closed boot).

HONEST TRUST-ROOT NOTE (stated, not buried): signing relocates the trust root from "anyone who can write
the registry file" to "a holder of a listed private key OR anyone who can also rewrite the public-key
allowlist." It is a real, meaningful narrowing — NOT absolute. The allowlist itself must be protected by
out-of-band means (committed under version control, read-only at deploy, ideally pinned in a signed
release). This module secures the registry against unauthorized content; it cannot secure a host whose
entire constitution/ directory is attacker-writable. Defense in depth, not a silver bullet.

Requires the `cryptography` package (vetted Ed25519). No hand-rolled crypto in a security airlock.
"""
import os, json, hashlib
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption

ALGO = "ed25519"
AUTHORITY_PROTOCOL = "mcl-authority-v1"


class RegistryCryptographicBreach(Exception):
    """Raised at the boot airlock when the registry's signature is missing, invalid, or unauthorized."""


# ── key material (raw 32-byte Ed25519, hex-encoded for JSON) ──────────────────────────────────────────
def generate_keypair():
    sk = Ed25519PrivateKey.generate()
    sk_hex = sk.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()).hex()
    pk_hex = sk.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    return sk_hex, pk_hex


def _sk(h): return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(h))
def _pk(h): return Ed25519PublicKey.from_public_bytes(bytes.fromhex(h))
def pubkey_of(sk_hex): return _sk(sk_hex).public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


# ── sign / verify over the EXACT registry bytes ───────────────────────────────────────────────────────
def sign_registry(registry_path, sk_hex, sig_path=None):
    data = open(registry_path, "rb").read()
    sig = _sk(sk_hex).sign(data)                      # raw 64-byte Ed25519 signature, deterministic
    block = {"algo": ALGO, "pubkey": pubkey_of(sk_hex), "signature": sig.hex(),
             "registry_sha256": hashlib.sha256(data).hexdigest()}
    if sig_path:
        json.dump(block, open(sig_path, "w"), indent=2, sort_keys=True); open(sig_path, "a").write("\n")
    return block


def load_authorized_keys(keys_path):
    if not os.path.exists(keys_path):
        raise RegistryCryptographicBreach("authorized-keys file missing: %s" % keys_path)
    doc = json.load(open(keys_path))
    if doc.get("protocol") != AUTHORITY_PROTOCOL:
        raise RegistryCryptographicBreach("authorized-keys protocol mismatch")
    return {k["pubkey"]: k.get("holder", "?") for k in doc.get("keys", [])}


def verify_registry(registry_path, sig_path, authorized):
    """Return (True, holder) iff the detached signature over the registry bytes is valid AND signed by a
    key in `authorized` (pubkey_hex -> holder). Otherwise raise RegistryCryptographicBreach. Fail-closed."""
    if not os.path.exists(sig_path):
        raise RegistryCryptographicBreach("signature file missing: %s" % sig_path)
    try:
        block = json.load(open(sig_path))
    except Exception as e:
        raise RegistryCryptographicBreach("signature file unreadable: %r" % e)
    if block.get("algo") != ALGO:
        raise RegistryCryptographicBreach("unexpected signature algorithm: %r" % block.get("algo"))
    pk_hex = block.get("pubkey", "")
    if pk_hex not in authorized:
        raise RegistryCryptographicBreach("UNAUTHORIZED signer (pubkey not in allowlist): %s" % pk_hex[:16])
    data = open(registry_path, "rb").read()
    if block.get("registry_sha256") != hashlib.sha256(data).hexdigest():
        raise RegistryCryptographicBreach("registry digest mismatch (content changed after signing)")
    try:
        _pk(pk_hex).verify(bytes.fromhex(block["signature"]), data)
    except Exception:
        raise RegistryCryptographicBreach("Ed25519 signature does not verify over registry bytes")
    return True, authorized[pk_hex]


def airlock(registry_path, sig_path, keys_path, require=True):
    """Boot gate. require=True -> a valid signature is mandatory. require=False -> if a .sig exists it MUST
    verify (a present-but-bad signature always fails closed), but an absent .sig is permitted (dev mode)."""
    if not require and not os.path.exists(sig_path):
        return {"signed": False, "mode": "dev-unsigned"}
    authorized = load_authorized_keys(keys_path)
    ok, holder = verify_registry(registry_path, sig_path, authorized)
    return {"signed": True, "holder": holder, "mode": "verified"}
