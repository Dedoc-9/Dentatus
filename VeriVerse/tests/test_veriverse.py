"""VeriVerse/tests/test_veriverse.py — deterministic world, chunk shards, provenance, physics."""
import os, sys, unittest
_V = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _V)
sys.path.insert(0, os.path.join(os.path.dirname(_V), "chronicle"))
import world as W
import physics as P
import shards as S
from _cores import merkle

SEED = 98247
COORDS = [(cx, cz) for cx in range(2) for cz in range(2)]


class World(unittest.TestCase):
    def test_chunk_deterministic(self):
        self.assertEqual(W.chunk_hash(W.generate_chunk(SEED, 0, 0)), W.chunk_hash(W.generate_chunk(SEED, 0, 0)))

    def test_world_root_reproducible(self):
        self.assertEqual(S.world_shard(SEED, COORDS)[0]["root"], S.world_shard(SEED, COORDS)[0]["root"])

    def test_different_seed_differs(self):
        self.assertNotEqual(S.world_shard(SEED, COORDS)[0]["root"], S.world_shard(SEED + 1, COORDS)[0]["root"])

    def test_different_chunk_differs(self):
        self.assertNotEqual(W.chunk_hash(W.generate_chunk(SEED, 0, 0)), W.chunk_hash(W.generate_chunk(SEED, 5, 5)))


class Provenance(unittest.TestCase):
    def test_feature_verifies(self):
        feat = W.generate_chunk(SEED, 0, 0)["feature"]
        ok, s = W.verify_feature(feat)
        self.assertTrue(ok); self.assertEqual(s, feat["stopping_time"])

    def test_tampered_feature_caught(self):
        feat = dict(W.generate_chunk(SEED, 0, 0)["feature"], stopping_time=99999)
        self.assertFalse(W.verify_feature(feat)[0])

    def test_forge_legendary(self):
        n, s = W.forge_legendary_chunk_seed()
        self.assertGreaterEqual(s, W.LEGENDARY_STOPPING_TIME)
        self.assertTrue(W.verify_feature({"seed_n": n, "stopping_time": s})[0])


class Shards(unittest.TestCase):
    def test_mint_and_verify(self):
        self.assertTrue(S.verify_chunk_shard(S.mint_chunk_shard(SEED, 1, 1))[0])

    def test_tampered_hash_fails(self):
        bad = dict(S.mint_chunk_shard(SEED, 1, 1), chunk_hash="0" * 64)
        self.assertFalse(S.verify_chunk_shard(bad)[0])

    def test_tampered_feature_fails(self):
        sh = S.mint_chunk_shard(SEED, 1, 1)
        sh = dict(sh, feature=dict(sh["feature"], stopping_time=sh["feature"]["stopping_time"] + 1))
        self.assertFalse(S.verify_chunk_shard(sh)[0])

    def test_inclusion_proof(self):
        wshard, _ = S.world_shard(SEED, COORDS)
        proof, leaf = S.chunk_inclusion(SEED, COORDS, 2)
        self.assertTrue(merkle.verify_inclusion(leaf, proof, wshard["root"]))


class Physics(unittest.TestCase):
    def test_sand_settles_deterministically(self):
        def fresh():
            g = [[0] * 5 for _ in range(6)]
            g[0][2] = P.SAND; g[1][2] = P.SAND
            return g
        a = P.settle(fresh()); b = P.settle(fresh())
        self.assertEqual(a[2], b[2])                          # identical settled hash
        self.assertEqual(a[0][-1][2], P.SAND)                # grain reached the bottom

    def test_bounded(self):
        g = [[P.SAND] * 4 for _ in range(4)]                 # full of sand, nowhere to fall
        _, steps, _ = P.settle(g, max_steps=50)
        self.assertLessEqual(steps, 50)


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("set PYTHONHASHSEED=0\n"); raise SystemExit(2)
    unittest.main(verbosity=2)
