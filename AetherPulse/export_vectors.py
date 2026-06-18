"""
AetherPulse/export_vectors.py — emit conformance vectors as language-agnostic JSON for a native (C++/Rust) port.

Each fixture is the input world + the exact outputs the Python reference produces: a native engine is
conformant for that fixture iff, starting from `world0`, it reproduces `final_hash` and `merkle_root`. The
hashing format the native side must match is pinned in STAGE1_SPEC.md §7 (chronicle canonical_bytes + SHA256).

Run:  PYTHONHASHSEED=0 python3 export_vectors.py      # writes fixtures/*.json and re-verifies each
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chronicle"))
import kernel as K
import conformance as C

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def scenarios():
    A = K.body(1, [-5, 5, 0], [4, 0, 0], [1, 1, 1])
    B = K.body(2, [5, 5, 0], [-4, 0, 0], [1, 1, 1])
    drop = K.body(7, [0, 9, 0], [0, 0, 0], [1, 1, 1])
    nbody = [K.body(i, [(i % 8) - 4, 5, 0], [(i % 3) - 1, 0, 0], [1, 1, 1]) for i in range(12)]
    return {
        "two_cubes": (K.make_world([A, B], ((-10, 0, -10), (10, 10, 10)), gravity=0, dt_ms=16), 150),
        "gravity_bounce": (K.make_world([drop], ((-10, 0, -10), (10, 10, 10)), gravity=10, dt_ms=16), 200),
        "nbody12": (K.make_world(nbody, ((-20, 0, -20), (20, 20, 20)), gravity=10, dt_ms=16), 100),
    }


def export():
    os.makedirs(FIXTURES, exist_ok=True)
    written = []
    for name, (world, ticks) in scenarios().items():
        vec = C.make_vector(world, ticks)                    # unsigned: the authority is the re-run, not a key
        payload = {"schema": vec["schema"], "name": name, "scale_bits": 32,
                   "init_hash": vec["init_hash"], "ticks": vec["ticks"],
                   "final_hash": vec["final_hash"], "merkle_root": vec["merkle_root"],
                   "world0": vec["world0"]}
        path = os.path.join(FIXTURES, name + ".json")
        with open(path, "w") as fh:
            json.dump(payload, fh, indent=2)
        # round-trip self-check: reload and verify against the reference
        loaded = json.load(open(path))
        ok, detail = C.verify_vector({"schema": loaded["schema"], "init_hash": loaded["init_hash"],
                                      "ticks": loaded["ticks"], "final_hash": loaded["final_hash"],
                                      "merkle_root": loaded["merkle_root"], "world0": loaded["world0"]})
        written.append((name, ok, detail, vec["final_hash"][:16]))
    return written


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("set PYTHONHASHSEED=0\n"); raise SystemExit(2)
    for name, ok, detail, fh in export():
        print("  fixtures/%-16s ok=%s  final_hash=%s  (%s)" % (name + ".json", ok, fh, detail))
    print("\nWrote %d conformance fixtures. A C++/Rust port passes iff it reproduces final_hash + merkle_root." % 3)
