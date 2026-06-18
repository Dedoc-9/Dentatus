"""
VeriVerse/world.py — deterministic voxel world generation + content-addressed chunks + provable provenance.

A world is a pure function of its seed: generate the same chunk on a phone and a server and the voxel data —
and its hash — are bit-for-bit identical. Each chunk is content-addressed (stasis Iron Canon); the world has
a Merkle root over all chunk hashes. Rare features carry *provable provenance*: an item exists because a
specific Collatz seed has a specific stopping time, which anyone can recompute and verify.

HONEST BOUND: this proves the world is deterministic and replayable, and that a feature's provenance is the
declared math — NOT that the world models real physics, and NOT that a "rare" item has any real-world value.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cores import canon, merkle, syracuse, crucible
import noise

# voxel block ids (small integer palette)
AIR, STONE, DIRT, GRASS, WATER, ORE = 0, 1, 2, 3, 4, 5
SEA_LEVEL = 14


def column(seed, x, z, height_amp=24):
    """The block id at each y for a column, bottom-up to a fixed sky height. Pure integer."""
    h = noise.height2d(seed, x, z, amp=height_amp)
    sky = 48
    col = []
    for y in range(sky):
        if y < h - 3:
            col.append(STONE)
        elif y < h - 1:
            col.append(DIRT)
        elif y < h:
            col.append(GRASS if h >= SEA_LEVEL else DIRT)
        elif y < SEA_LEVEL and y >= h:
            col.append(WATER)
        else:
            col.append(AIR)
    return col, h


def generate_chunk(seed, cx, cz, size=16, height_amp=24):
    """A size×size chunk of height columns at chunk-grid (cx, cz). Returns a canonical dict."""
    heights = [[0] * size for _ in range(size)]
    surface = [[0] * size for _ in range(size)]
    for lx in range(size):
        for lz in range(size):
            x, z = cx * size + lx, cz * size + lz
            _, h = column(seed, x, z, height_amp)
            heights[lz][lx] = h
            surface[lz][lx] = GRASS if h >= SEA_LEVEL else WATER
    feat = feature(seed, cx, cz)
    return {"seed": seed, "coord": [cx, cz], "size": size, "heights": heights,
            "surface": surface, "feature": feat}


def chunk_hash(chunk):
    return canon.canon_hash(chunk)


def world_root(seed, coords, size=16):
    """Merkle root over the chunk hashes of a set of chunk coordinates — the content address of the world."""
    leaves = [chunk_hash(generate_chunk(seed, cx, cz, size)) for (cx, cz) in coords]
    return merkle.merkle_root(leaves)


# ----------------------------------------------------------------- provable feature provenance
LEGENDARY_STOPPING_TIME = 120


def feature(seed, cx, cz):
    """A chunk's rare feature, derived deterministically. Its 'rarity' is the Collatz stopping time of a
    seed bound to the chunk — provable: anyone recomputes syracuse.gates(n)['stopping_time']."""
    n = 2 + (noise._hash_int(seed, "feat", cx, cz) % 100000)
    g = syracuse.gates(n)
    s = g["stopping_time"]
    kind = "legendary" if s >= LEGENDARY_STOPPING_TIME else ("rare" if s >= 80 else "common")
    return {"seed_n": n, "stopping_time": s, "kind": kind,
            "pos": [noise._hash_int(seed, "fx", cx, cz) % 16, noise._hash_int(seed, "fz", cx, cz) % 16]}


def verify_feature(feat):
    """Recompute the feature's provenance from its seed. (ok, recomputed_stopping_time)."""
    g = syracuse.gates(feat["seed_n"])
    return (g["stopping_time"] == feat["stopping_time"]), g["stopping_time"]


def forge_legendary_chunk_seed(min_stopping_time=LEGENDARY_STOPPING_TIME, search_cap=200000):
    """FORGE a feature seed with a provable stopping_time >= the legendary bar (provable rarity by
    construction, not lucky RNG). Scans the Collatz difficulty landscape for the first qualifying seed;
    anyone re-verifies with syracuse.gates(n)['stopping_time']."""
    n = 2
    while n < search_cap:
        s = syracuse.gates(n)["stopping_time"]
        if s >= min_stopping_time:
            return n, s
        n += 1
    raise RuntimeError("no seed within search cap (raise the cap)")
