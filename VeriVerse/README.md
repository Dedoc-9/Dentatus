# VeriVerse — the verifiable universe engine (voxel prototype)

> **Don't just render the world. Prove it exists.**
> *Same seed → identical world + identical hashes on any machine.*

VeriVerse is a deterministic procedural world engine built on the Dentatus/Chronicle workbench. The world is
a **pure function of its seed**: generate the same chunk on a phone and a server and the voxel data — and its
hash — are bit-for-bit identical. Every chunk is content-addressed, every region has a Merkle root, and rare
features carry **provable provenance**. This is the first prototype (a voxel/heightmap engine + a stdlib
viewer); it is the verifiable *engine* a GPU renderer would consume, not the renderer itself.

## The honest bound (read first)

A clean replay proves the world is **deterministic and replayable**, and that a feature's provenance is the
declared math. It does **not** prove:

- that the world models **real physics** (the fixed-point falling-sand is a toy cellular automaton),
- that a "legendary" item has any **real-world value** (its *rarity* is a provable Collatz stopping time — its
  *worth* is not),
- or that exploits are **"mathematically impossible"** — server/quorum authority makes them *detectable and
  rejectable*, which is a different, honest claim.

`integrity ≠ truth`, made tangible: a verifiable world is not a true world.

## Run it

```
PYTHONHASHSEED=0 python3 demo_veriverse.py                 # generate · same-seed proof · shard · provenance · physics · lazy-verify
PYTHONHASHSEED=0 python3 tests/test_veriverse.py           # 13 unit tests
PYTHONHASHSEED=0 python3 viewer/server.py                  # http://127.0.0.1:8799/  (top-down viewer + live shard verify)
```

## How it works — and which workbench piece does what

VeriVerse is a **standalone** product that imports the workbench read-only (the Sibling Law); `_cores.py`
puts the sibling directories on the path and never edits or vendors them.

| layer | piece | role |
|---|---|---|
| terrain | integer value-noise (`noise.py`) | deterministic height field — hash-seeded lattice corners + integer bilinear interp, no floats |
| world | content-addressing + `stasis` | each chunk is canonically hashed; a region has a Merkle **world root** (O(log n) per-chunk proofs) |
| provenance | `syracuse` / `crucible` | a feature's rarity *is* a Collatz **stopping time**; a "legendary" seed is forged to clear a provable bar |
| physics | `aether` fixed-point discipline (`physics.py`) | a deterministic integer falling-sand CA, bounded by a step budget so it always terminates |
| proof | `tessera` + chronicle signing (`shards.py`) | a signed **chunk shard** a stranger regenerates and verifies, trusting no producer |

**Determinism is the headline.** `demo_veriverse.py` regenerates the world ("another machine") and shows the
world root is bit-for-bit identical — and a tampered chunk hash fails verification, while a different seed
yields a different world.

## What's built vs. proposed

**Built (this prototype):** deterministic terrain + voxel chunks, content-addressed world root, provable
feature provenance, integer falling-sand physics, signed chunk shards + Merkle lazy-verification, and a
stdlib top-down viewer with a live "verify this chunk" inspector and integrity bar.

**Proposed / not yet built (honest):** the GPU/WASM renderer and browser `fuel` replay, the `quorum`/`polity`
P2P multiplayer consensus mesh, and 3-D voxel meshing. The current viewer is a 2-D heightmap served by a
local Python server — it makes the verifiability visible, but it is not the real-time 3-D client.

## Files

| File | Role |
|---|---|
| `_cores.py` | Sibling-Law shim — imports `stasis`/`crucible`/`syracuse`/`aether`/`tessera` read-only |
| `noise.py` | deterministic integer value-noise terrain height field |
| `world.py` | voxel chunk generation, content-addressed chunk/world hashes, provable feature provenance |
| `physics.py` | deterministic integer falling-sand cellular automaton (bounded) |
| `shards.py` | signed chunk shards + world Merkle root + on-demand inclusion proofs |
| `demo_veriverse.py` | generate · same-seed proof · shard · provenance · physics · lazy-verify |
| `viewer/server.py` + `viewer/index.html` | minimal stdlib top-down viewer + live chunk-shard verify |
| `tests/test_veriverse.py` | 13 unit tests |
