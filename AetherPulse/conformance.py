"""
AetherPulse/conformance.py — conformance vectors: the contract a native (Rust/C++ SIMD) port must satisfy.

A conformance vector binds an initial world + a tick count to the exact outputs the REFERENCE kernel
produces: the final state hash and the Merkle root over per-tick hashes. A native engine is "AetherPulse-
conformant" iff, starting from the same world, it reproduces those hashes bit-for-bit. This is how you build
a fast engine without losing determinism: optimize freely, but the hashes must match the reference oracle.

Optionally signed (Ed25519) for authorship. The authority of a vector is the re-run, not the signature.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cores import merkle
import core as chcore                                        # chronicle/core.py
from signing import Ed25519Verifier
import kernel as K

_BODY_KEYS = ("schema", "init_hash", "ticks", "final_hash", "merkle_root")


def make_vector(world, ticks, signer=None):
    final, hashes = K.run(world, ticks)
    body = {"schema": "aetherpulse-conformance/1", "init_hash": K.state_hash(world), "ticks": ticks,
            "final_hash": K.state_hash(final), "merkle_root": merkle.merkle_root(hashes)}
    vec = {**body, "world0": world}
    if signer is not None:
        vec["signature"] = signer.sign(chcore.canonical_bytes(body))
        vec["algo"] = signer.algo
        vec["public_material"] = signer.public_material() if signer.algo == "ed25519" else None
    return vec


def verify_vector(vec, verifier=None):
    """Re-run the reference from the vector's world and confirm the outputs. (ok, detail). This is exactly
    the check a native port must pass."""
    w = vec["world0"]
    if K.state_hash(w) != vec["init_hash"]:
        return False, "INIT mismatch (world0 does not hash to init_hash)"
    final, hashes = K.run(w, vec["ticks"])
    if K.state_hash(final) != vec["final_hash"]:
        return False, "FINAL mismatch (reference re-run diverged)"
    if merkle.merkle_root(hashes) != vec["merkle_root"]:
        return False, "MERKLE mismatch (per-tick history differs)"
    if vec.get("signature") is not None:
        v = verifier
        if v is None and vec.get("algo") == "ed25519" and vec.get("public_material"):
            v = Ed25519Verifier(vec["public_material"])
        if v is None:
            return False, "SIGNATURE present but no verifier key"
        body = {k: vec[k] for k in _BODY_KEYS}
        if not v.verify(chcore.canonical_bytes(body), vec["signature"]):
            return False, "SIGNATURE invalid"
    return True, "CONFORMANT"
