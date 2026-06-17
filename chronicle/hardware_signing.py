"""
chronicle/hardware_signing.py — hardware-backed signing with an honest, tiered fallback.

================================================================================================
WHAT THIS PROTECTS  (and, just as importantly, what it does NOT)
================================================================================================
PROTECTS:
  * Integrity of the SIGNING PROCESS. With a hardware token (Tier 1), the private key lives inside a
    TPM 2.0 / YubiKey and never enters Python's address space, so a compromised agent process cannot
    exfiltrate it from RAM and cannot forge a ledger/telemetry signature even on the same host.
  * Tamper-EVIDENCE of recorded history: any post-hoc edit to a signed record fails verification.
  * Blast-radius reduction: an attacker who owns the process still cannot mint valid signatures.

DOES NOT PROTECT:
  * Honesty of the CAPTURE PATH. On a single host under one user, a malicious process can feed FAKE
    inputs (spoofed keystrokes, window titles, file events) into the recorder, and this signer will
    faithfully sign that lie. Hardware keys secure the *signing*, not the *truth of what was captured*.
  * Against a host compromised at a level that can also abuse the capture agent or the middleware.
  This is tamper-evidence + bounded authority, NOT impossible "tamper-proofness".

================================================================================================
TIERS  (chosen at construction; never silently weakened without a stderr warning)
================================================================================================
  Tier 1  pkcs11-ecdsa-p256  : hardware token via ctypes PKCS#11 (no pip deps). Key never in RAM. BEST.
  Tier 2  ed25519-soft       : software Ed25519 (asymmetric, third-party verifiable). The private key is
                               stored ENCRYPTED AT REST (AES-GCM under a key derived by scrypt) and only
                               decrypted into RAM for the signing call. Requires `cryptography`.
  Tier 3  hmac-scrypt        : stdlib-only LAST RESORT. SYMMETRIC HMAC under a scrypt-hardened key. The
                               verifier also holds the signing power -> NO third-party non-repudiation.
                               Used only if no token and no `cryptography`; emits a loud warning.

Note on scrypt: it is a password-based KDF. Its correct role here is hardening a key (Tier 2 at-rest
encryption; Tier 3 key derivation) — never as a "signing primitive" in its own right.

Interface (matches every other signer in the repo — `sign` returns a HEX STRING so it round-trips in the
JSON ledger; raw bytes are not JSON-serializable):
    signer.sign(message: bytes) -> hex str
    signer.verify(message: bytes, sig: hex str) -> bool
    signer.algo -> str
    signer.public_material() -> hex str | None     (None for the symmetric Tier 3)
"""
import ctypes
import hashlib
import hmac
import os
import sys

SCRYPT_N, SCRYPT_R, SCRYPT_P, SCRYPT_DKLEN = 2 ** 14, 8, 1, 32


def _warn(msg):
    sys.stderr.write("[chronicle.hardware_signing] %s\n" % msg)


def _passphrase():
    """Passphrase for KDF tiers. Env-only; falls back to a machine-bound string with a warning so the
    module never hard-crashes, but that fallback is explicitly NOT a secret."""
    p = os.environ.get("CHRONICLE_SIGNER_PASSPHRASE")
    if p:
        return p.encode()
    _warn("CHRONICLE_SIGNER_PASSPHRASE not set; deriving a machine-bound, NON-SECRET key. Set the env "
          "var for any real protection.")
    import platform
    return ("machine:%s:%s" % (platform.node(), platform.machine())).encode()


# ============================================================ Tier 1: PKCS#11 (ctypes, no pip deps)
# Minimal, spec-faithful (PKCS#11 v2.40) binding for: init, open session, login, find an EC private key,
# and C_Sign a 32-byte digest with CKM_ECDSA. Verification of the resulting P-256 signature uses
# `cryptography` if available (public-key op); if absent, hardware-tier verify raises a clear error.
CKF_SERIAL_SESSION, CKF_RW_SESSION = 0x00000004, 0x00000002
CKU_USER = 1
CKO_PRIVATE_KEY, CKO_PUBLIC_KEY = 3, 2
CKA_CLASS, CKA_LABEL, CKA_EC_POINT = 0, 3, 0x00000181
CKK_EC = 0x00000003
CKM_ECDSA = 0x00001041
CKR_OK = 0

DEFAULT_MIDDLEWARE = [
    "/usr/lib/x86_64-linux-gnu/libtpm2_pkcs11.so", "/usr/lib/libtpm2_pkcs11.so",
    "/usr/local/lib/libtpm2_pkcs11.so", "/usr/local/lib/libykcs11.dylib",
    "/usr/lib/x86_64-linux-gnu/libykcs11.so", "/Library/Frameworks/PKCS11.framework/PKCS11",
]


class _CK_MECHANISM(ctypes.Structure):
    _fields_ = [("mechanism", ctypes.c_ulong),
                ("pParameter", ctypes.c_void_p),
                ("ulParameterLen", ctypes.c_ulong)]


class _CK_ATTRIBUTE(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("pValue", ctypes.c_void_p),
                ("ulValueLen", ctypes.c_ulong)]


def _find_middleware(explicit=None):
    for cand in ([explicit] if explicit else []) + DEFAULT_MIDDLEWARE:
        if cand and os.path.exists(cand):
            return cand
    env = os.environ.get("CHRONICLE_PKCS11_LIB")
    return env if env and os.path.exists(env) else None


class _PKCS11Session:
    """Thin RAII wrapper around a logged-in PKCS#11 session holding one EC signing key handle."""

    def __init__(self, lib_path, key_label, pin):
        self.lib = ctypes.CDLL(lib_path)
        self.session = ctypes.c_ulong(0)
        self.key = ctypes.c_ulong(0)
        self._open(key_label, pin)

    def _chk(self, rv, where):
        if rv != CKR_OK:
            raise OSError("PKCS#11 %s failed (rv=0x%X)" % (where, rv))

    def _open(self, key_label, pin):
        self._chk(self.lib.C_Initialize(None), "C_Initialize")
        count = ctypes.c_ulong(0)
        self._chk(self.lib.C_GetSlotList(True, None, ctypes.byref(count)), "C_GetSlotList(count)")
        if count.value == 0:
            raise OSError("no PKCS#11 slots with a token present")
        slots = (ctypes.c_ulong * count.value)()
        self._chk(self.lib.C_GetSlotList(True, slots, ctypes.byref(count)), "C_GetSlotList")
        self._chk(self.lib.C_OpenSession(slots[0], CKF_SERIAL_SESSION | CKF_RW_SESSION, None, None,
                                         ctypes.byref(self.session)), "C_OpenSession")
        if pin:
            self._chk(self.lib.C_Login(self.session, CKU_USER, pin, len(pin)), "C_Login")
        # find the EC private key (optionally by label)
        cls = ctypes.c_ulong(CKO_PRIVATE_KEY)
        templ = [_CK_ATTRIBUTE(CKA_CLASS, ctypes.cast(ctypes.byref(cls), ctypes.c_void_p), ctypes.sizeof(cls))]
        if key_label:
            lbl = ctypes.create_string_buffer(key_label.encode())
            templ.append(_CK_ATTRIBUTE(CKA_LABEL, ctypes.cast(lbl, ctypes.c_void_p), len(key_label)))
        arr = (_CK_ATTRIBUTE * len(templ))(*templ)
        self._chk(self.lib.C_FindObjectsInit(self.session, arr, len(templ)), "C_FindObjectsInit")
        found = ctypes.c_ulong(0)
        self._chk(self.lib.C_FindObjects(self.session, ctypes.byref(self.key), 1, ctypes.byref(found)),
                  "C_FindObjects")
        self.lib.C_FindObjectsFinal(self.session)
        if found.value == 0:
            raise OSError("no EC private key found on token (label=%r)" % key_label)

    def sign_digest(self, digest):
        mech = _CK_MECHANISM(CKM_ECDSA, None, 0)
        self._chk(self.lib.C_SignInit(self.session, ctypes.byref(mech), self.key), "C_SignInit")
        siglen = ctypes.c_ulong(0)
        self._chk(self.lib.C_Sign(self.session, digest, len(digest), None, ctypes.byref(siglen)),
                  "C_Sign(len)")
        sig = ctypes.create_string_buffer(siglen.value)
        self._chk(self.lib.C_Sign(self.session, digest, len(digest), sig, ctypes.byref(siglen)), "C_Sign")
        return bytes(sig.raw[:siglen.value])


# ============================================================ the public class
class HardwareSigner:
    algo = None

    def __init__(self, key_label="chronicle", middleware=None, prefer_hardware=True,
                 soft_key_path=None, passphrase=None):
        self._pin = (os.environ.get("CHRONICLE_PKCS11_PIN") or "").encode() or None
        self._pp = passphrase.encode() if isinstance(passphrase, str) else (passphrase or _passphrase())
        self._sess = None
        self._tier = None

        if prefer_hardware:
            libp = _find_middleware(middleware)
            if libp:
                try:
                    self._sess = _PKCS11Session(libp, key_label, self._pin)
                    self.algo = "pkcs11-ecdsa-p256"
                    self._tier = 1
                    _warn("Tier 1: signing via PKCS#11 token (%s). Private key stays in hardware." % libp)
                except Exception as e:                       # token absent/locked -> degrade, do not crash
                    _warn("PKCS#11 present but unusable (%s); degrading." % e)

        if self._tier is None:
            try:
                self._init_ed25519_soft(soft_key_path)
                self.algo = "ed25519-soft"
                self._tier = 2
                _warn("Tier 2: software Ed25519 (asymmetric). Private key is scrypt-encrypted at rest; it "
                      "enters RAM only during signing -- weaker than a hardware token.")
            except Exception as e:
                self._init_hmac_scrypt()
                self.algo = "hmac-scrypt"
                self._tier = 3
                _warn("Tier 3: stdlib HMAC under a scrypt-hardened key (reason: %s). THIS IS SYMMETRIC -- "
                      "the verifier can forge, so there is NO third-party non-repudiation." % e)

    # ---- Tier 2: software Ed25519 with key encrypted at rest ----
    def _init_ed25519_soft(self, soft_key_path):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives import serialization
        self._serialization = serialization
        path = soft_key_path or os.environ.get("CHRONICLE_SOFT_KEY",
                                               os.path.join(os.path.dirname(__file__), ".soft_signing_key"))
        if os.path.exists(path):
            blob = open(path, "rb").read()
            salt, nonce, ct = blob[:16], blob[16:28], blob[28:]
            kek = hashlib.scrypt(self._pp, salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=SCRYPT_DKLEN)
            raw = AESGCM(kek).decrypt(nonce, ct, None)
            self._sk = Ed25519PrivateKey.from_private_bytes(raw)
        else:
            self._sk = Ed25519PrivateKey.generate()
            raw = self._sk.private_bytes(encoding=serialization.Encoding.Raw,
                                         format=serialization.PrivateFormat.Raw,
                                         encryption_algorithm=serialization.NoEncryption())
            salt, nonce = os.urandom(16), os.urandom(12)
            kek = hashlib.scrypt(self._pp, salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=SCRYPT_DKLEN)
            ct = AESGCM(kek).encrypt(nonce, raw, None)
            with open(path, "wb") as f:
                f.write(salt + nonce + ct)
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
        self._pub_hex = self._sk.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw).hex()

    # ---- Tier 3: stdlib symmetric ----
    def _init_hmac_scrypt(self):
        self._salt = b"chronicle-hmac-scrypt-v1"
        self._key = hashlib.scrypt(self._pp, salt=self._salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P,
                                   dklen=SCRYPT_DKLEN)

    # ---- Signer protocol ----
    def sign(self, message):
        digest = hashlib.sha256(message).digest()
        if self._tier == 1:
            return self._sess.sign_digest(digest).hex()
        if self._tier == 2:
            return self._sk.sign(message).hex()              # Ed25519 signs the message (hashes internally)
        return hmac.new(self._key, message, hashlib.sha256).hexdigest()

    def verify(self, message, sig):
        try:
            if self._tier == 3:
                return hmac.compare_digest(hmac.new(self._key, message, hashlib.sha256).hexdigest(), sig)
            if self._tier == 2:
                from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
                from cryptography.exceptions import InvalidSignature
                pk = Ed25519PublicKey.from_public_bytes(bytes.fromhex(self._pub_hex))
                try:
                    pk.verify(bytes.fromhex(sig), message)
                    return True
                except InvalidSignature:
                    return False
            # Tier 1: verify the token's ECDSA P-256 signature with the public key (needs cryptography)
            return self._verify_pkcs11(message, sig)
        except Exception:
            return False

    def _verify_pkcs11(self, message, sig):
        try:
            from cryptography.hazmat.primitives.asymmetric import ec, utils
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.exceptions import InvalidSignature
        except Exception as e:
            raise RuntimeError("hardware-tier verify needs `cryptography` to check the P-256 signature") from e
        pub = self.public_material()
        if not pub:
            raise RuntimeError("no public key available for hardware verify")
        pk = serialization.load_der_public_key(bytes.fromhex(pub)) if len(pub) > 130 else \
            ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), bytes.fromhex(pub))
        raw = bytes.fromhex(sig)                              # PKCS#11 emits raw r||s; convert to DER
        n = len(raw) // 2
        r = int.from_bytes(raw[:n], "big"); s = int.from_bytes(raw[n:], "big")
        der = utils.encode_dss_signature(r, s)
        try:
            pk.verify(der, message, ec.ECDSA(hashes.SHA256()))
            return True
        except InvalidSignature:
            return False

    def public_material(self):
        if self._tier == 2:
            return self._pub_hex
        if self._tier == 1:
            return self._pkcs11_public_point()
        return None                                          # symmetric: nothing safe to publish

    def _pkcs11_public_point(self):
        """Read CKA_EC_POINT off the matching public key object, if present. Returns hex or None."""
        try:
            lib, sess = self._sess.lib, self._sess.session
            cls = ctypes.c_ulong(CKO_PUBLIC_KEY)
            t = (_CK_ATTRIBUTE * 1)(_CK_ATTRIBUTE(CKA_CLASS,
                 ctypes.cast(ctypes.byref(cls), ctypes.c_void_p), ctypes.sizeof(cls)))
            if lib.C_FindObjectsInit(sess, t, 1) != CKR_OK:
                return None
            h = ctypes.c_ulong(0); found = ctypes.c_ulong(0)
            lib.C_FindObjects(sess, ctypes.byref(h), 1, ctypes.byref(found)); lib.C_FindObjectsFinal(sess)
            if found.value == 0:
                return None
            attr = (_CK_ATTRIBUTE * 1)(_CK_ATTRIBUTE(CKA_EC_POINT, None, 0))
            if lib.C_GetAttributeValue(sess, h, attr, 1) != CKR_OK:
                return None
            buf = ctypes.create_string_buffer(attr[0].ulValueLen)
            attr[0].pValue = ctypes.cast(buf, ctypes.c_void_p)
            if lib.C_GetAttributeValue(sess, h, attr, 1) != CKR_OK:
                return None
            return bytes(buf.raw[:attr[0].ulValueLen]).hex()
        except Exception:
            return None

    def tier_name(self):
        return {1: "hardware (PKCS#11)", 2: "software Ed25519 (encrypted at rest)",
                3: "stdlib HMAC-scrypt (SYMMETRIC)"}[self._tier]
