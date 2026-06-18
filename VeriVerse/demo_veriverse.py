"""
VeriVerse/demo_veriverse.py — a verifiable voxel world. "Don't just render the world. Prove it exists."

  A. GENERATE        — a deterministic world from a seed; ASCII cross-section; content-addressed world root.
  B. SAME-SEED PROOF — regenerate on "another machine"; bit-for-bit identical root (the headline claim).
  C. CHUNK SHARD     — mint a signed chunk shard; a stranger regenerates + verifies; a tamper fails.
  D. PROVENANCE      — a forged "legendary" feature: it exists because a Collatz seed has stopping_time>=120.
  E. PHYSICS         — deterministic integer falling-sand settles to a content-addressed state.
  F. LAZY VERIFY     — prove one chunk is in the world root via an O(log n) Merkle proof.

Run:  PYTHONHASHSEED=0 python3 demo_veriverse.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chronicle"))
import world as W
import physics as P
import shards as S
from signing import Ed25519Signer, ed25519_available

SEED = 98247
COORDS = [(cx, cz) for cx in range(2) for cz in range(2)]
GLYPH = {W.AIR: " ", W.STONE: "#", W.DIRT: ".", W.GRASS: "\"", W.WATER: "~", W.ORE: "*"}


def main():
    print("A) GENERATE (seed=%d) — cross-section of chunk (0,0):" % SEED)
    ch = W.generate_chunk(SEED, 0, 0)
    for y in range(28, 6, -1):                               # top-down slice along z=0
        row = "".join(GLYPH[W.column(SEED, x, 0)[0][y]] for x in range(0, 16))
        print("   " + row)
    wshard, _ = S.world_shard(SEED, COORDS)
    print("   world root: %s\n" % wshard["root"][:16])

    print("B) SAME-SEED PROOF (regenerate on 'another machine'):")
    again, _ = S.world_shard(SEED, COORDS)
    print("   identical world root: %s   different seed differs: %s\n"
          % (again["root"] == wshard["root"], S.world_shard(SEED + 1, COORDS)[0]["root"] != wshard["root"]))

    print("C) CHUNK SHARD (signed; a stranger regenerates and verifies):")
    signer = Ed25519Signer() if ed25519_available() else None
    shard = S.mint_chunk_shard(SEED, 1, 1, signer=signer)
    print("   shard chunk_hash=%s signed=%s -> verify=%s"
          % (shard["chunk_hash"][:12], shard["signature"] is not None, S.verify_chunk_shard(shard)))
    bad = dict(shard, chunk_hash="0" * 64)
    print("   tampered chunk_hash -> verify=%s\n" % (S.verify_chunk_shard(bad),))

    print("D) PROVABLE PROVENANCE (a 'legendary' feature is math, not lucky RNG):")
    n, s = W.forge_legendary_chunk_seed()
    print("   legendary seed n=%d has stopping_time=%d (>=%d) — anyone recomputes syracuse.gates(n)\n"
          % (n, s, W.LEGENDARY_STOPPING_TIME))

    print("E) PHYSICS (deterministic integer falling sand):")
    grid = [[0] * 7 for _ in range(8)]
    for y in range(3):
        grid[y][3] = P.SAND
    settled, steps, h = P.settle(grid)
    print("   settled in %d steps -> state hash %s (deterministic across machines)\n" % (steps, h[:12]))

    print("F) LAZY VERIFY (one chunk proven in the world root, O(log n)):")
    proof, leaf = S.chunk_inclusion(SEED, COORDS, 2)
    print("   chunk index 2 inclusion proof len=%d verifies: %s"
          % (len(proof), __import__("_cores").merkle.verify_inclusion(leaf, proof, wshard["root"])))
    print("\n   Same seed -> identical world + identical hashes on any machine. We prove the world is")
    print("   deterministic and replayable — not that it models real physics. integrity != truth.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[VeriVerse] set PYTHONHASHSEED=0 (world hashes must match across machines).\n\n")
        raise SystemExit(2)
    main()
