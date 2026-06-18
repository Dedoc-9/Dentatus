"""
stasis/batch.py — the Lazy Lattice: amortize verification over a batch instead of paying it per leaf.

Running N independent paths and a full `quorum` check for every single message kills throughput. `stasis`
batches: many shard hashes are folded into ONE Merkle root, the expensive consensus check runs on the root,
and an individual leaf is proven on demand with an O(log M) inclusion proof when challenged.

HONEST BOUND: this is OPTIMISTIC / lazy verification, not free verification. You TRUST the root until you
challenge a leaf; the total work of fully verifying everything is unchanged — batching lets you DEFER and
amortize it, and a challenge costs O(log M), not O(1). This is a simple Merkle tree (duplicate-last for odd
levels, no RFC-6962 domain separation); it is a reference accumulator, not a hardened transparency log.

Stdlib only.
"""
import hashlib

PROTOCOL_VERSION = "stasis-batch/1"


class StasisError(Exception):
    pass


def _h(a, b):
    return hashlib.sha256(("%s|%s" % (a, b)).encode()).hexdigest()


def _level_up(nodes):
    out = []
    for i in range(0, len(nodes), 2):
        a = nodes[i]
        b = nodes[i + 1] if i + 1 < len(nodes) else nodes[i]   # duplicate last on odd count
        out.append(_h(a, b))
    return out


def merkle_root(leaves):
    if not leaves:
        raise StasisError("empty batch has no root")
    nodes = list(leaves)
    while len(nodes) > 1:
        nodes = _level_up(nodes)
    return nodes[0]


def inclusion_proof(leaves, index):
    """Return the O(log M) sibling path proving `leaves[index]` is in the tree."""
    if not (0 <= index < len(leaves)):
        raise StasisError("index out of range")
    proof = []
    nodes = list(leaves)
    idx = index
    while len(nodes) > 1:
        sib_idx = idx ^ 1
        sib = nodes[sib_idx] if sib_idx < len(nodes) else nodes[idx]   # duplicated last
        proof.append({"sib": sib, "side": "R" if idx % 2 == 0 else "L"})
        nodes = _level_up(nodes)
        idx //= 2
    return proof


def verify_inclusion(leaf, proof, root):
    """Recompute the root from a leaf + its proof. True iff it matches (the leaf is provably in the batch)."""
    h = leaf
    for step in proof:
        h = _h(h, step["sib"]) if step["side"] == "R" else _h(step["sib"], h)
    return h == root


def batch_shard(leaves):
    """A compact, content-addressed summary of a batch: trust this root, verify any leaf on demand."""
    return {"protocol": PROTOCOL_VERSION, "count": len(leaves), "root": merkle_root(leaves)}
