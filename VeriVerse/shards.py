# SPDX-License-Identifier: AGPL-3.0-only
"""
VeriVerse/shards.py — content-addressed, signed chunk shards + a world Merkle root (lazy verification).

A chunk shard says: "chunk(seed, coord) hashes to exactly this, with this feature provenance" — signed. A
stranger regenerates the chunk from the seed and confirms it bit-for-bit, trusting no producer. The world
shard is a Merkle root over all chunk hashes, so any single chunk is provable in O(log n) on demand.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cores import canon, merkle
import core as chcore                                        # chronicle/core.py (canonical_bytes)
from signing import Ed25519Verifier
import world as W

_BODY_KEYS = ("schema", "seed", "coord", "size", "chunk_hash", "feature")


def mint_chunk_shard(seed, cx, cz, size=16, signer=None):
    ch = W.generate_chunk(seed, cx, cz, size)
    body = {"schema": "veriverse-chunk/1", "seed": seed, "coord": [cx, cz], "size": size,
            "chunk_hash": W.chunk_hash(ch), "feature": ch["feature"]}
    sig = signer.sign(chcore.canonical_bytes(body)) if signer is not None else None
    return {**body, "signature": sig, "algo": getattr(signer, "algo", None),
            "public_material": (signer.public_material() if signer is not None and signer.algo == "ed25519" else None)}


def verify_chunk_shard(shard, verifier=None):
    """Regenerate the chunk from the seed and confirm hash + feature provenance + signature. (ok, detail)."""
    ch = W.generate_chunk(shard["seed"], shard["coord"][0], shard["coord"][1], shard["size"])
    if W.chunk_hash(ch) != shard["chunk_hash"]:
        return False, "CHUNK mismatch (regenerated chunk differs from claim)"
    fok, _ = W.verify_feature(shard["feature"])
    if not fok:
        return False, "FEATURE provenance mismatch (stopping time recomputes differently)"
    if shard.get("signature") is not None:
        v = verifier
        if v is None and shard.get("algo") == "ed25519" and shard.get("public_material"):
            v = Ed25519Verifier(shard["public_material"])
        if v is None:
            return False, "SIGNATURE present but no verifier key"
        body = {k: shard[k] for k in _BODY_KEYS}
        if not v.verify(chcore.canonical_bytes(body), shard["signature"]):
            return False, "SIGNATURE invalid (forged / wrong key)"
    return True, "VERIFIED"


def world_shard(seed, coords, size=16):
    """A content address of a whole region: the Merkle root over its chunk hashes."""
    leaves = [W.chunk_hash(W.generate_chunk(seed, cx, cz, size)) for (cx, cz) in coords]
    return {"schema": "veriverse-world/1", "seed": seed,
            "coords": [list(c) for c in coords], "root": merkle.merkle_root(leaves)}, leaves


def chunk_inclusion(seed, coords, index, size=16):
    """An O(log n) proof that the chunk at `index` is part of the world root (lazy verification)."""
    _, leaves = world_shard(seed, coords, size)
    return merkle.inclusion_proof(leaves, index), leaves[index]
