# SPDX-License-Identifier: AGPL-3.0-only
"""
AetherPulse/demo_aetherpulse.py — Stage-1 reference kernel: two cubes collide, provably, the same everywhere.

  A. TWO CUBES        — a head-on collision resolves on an exact tick; equal-mass elastic swap.
  B. SAME EVERYWHERE  — re-runs are bit-for-bit identical (Python bigint == architecture-independent).
  C. GRAVITY + BOUNCE — a dropped box rests on the floor and bounces with integer restitution.
  D. CONFORMANCE      — a vector binds world+ticks to exact hashes; a native port is correct iff it matches.
  E. STRESS           — 1,000 bodies, deterministic (reference perf — NOT the 240fps target).

Run:  PYTHONHASHSEED=0 python3 demo_aetherpulse.py
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chronicle"))
import kernel as K
import conformance as C
from _cores import SCALE
from signing import Ed25519Signer, ed25519_available


def main():
    print("A) TWO CUBES (head-on along x, no gravity, in a box):")
    A = K.body(1, [-5, 5, 0], [4, 0, 0], [1, 1, 1])
    B = K.body(2, [5, 5, 0], [-4, 0, 0], [1, 1, 1])

    def fresh():
        return K.make_world([A, B], bounds=((-10, 0, -10), (10, 10, 10)), gravity=0, dt_ms=16)

    w = fresh(); hit = None
    for t in range(1, 200):
        pv = [b["vel"][0] for b in sorted(w["bodies"], key=lambda b: b["id"])]
        w = K.step(w)
        if hit is None and [b["vel"][0] for b in sorted(w["bodies"], key=lambda b: b["id"])] != pv:
            hit = t
    print("   collision at tick %d; velocities swap (elastic)\n" % hit)

    print("B) SAME EVERYWHERE (bit-for-bit determinism):")
    _, h1 = K.run(fresh(), 150); _, h2 = K.run(fresh(), 150)
    print("   identical final hash across runs: %s  (%s)\n" % (h1 == h2, h1[-1][:16]))

    print("C) GRAVITY + FLOOR BOUNCE (restitution 0.8):")
    D = K.body(7, [0, 9, 0], [0, 0, 0], [1, 1, 1])
    wd = K.make_world([D], bounds=((-10, 0, -10), (10, 10, 10)), gravity=10, dt_ms=16)
    ys = []
    for _ in range(120):
        wd = K.step(wd); ys.append(sorted(wd["bodies"], key=lambda b: b["id"])[0]["pos"][1] / SCALE)
    print("   floor rest y=%.2f, bounce-back peak y=%.2f\n" % (min(ys), max(ys[40:])))

    print("D) CONFORMANCE VECTOR (the native-port oracle):")
    signer = Ed25519Signer() if ed25519_available() else None
    vec = C.make_vector(fresh(), 150, signer=signer)
    print("   vector: ticks=%d final_hash=%s merkle=%s -> verify=%s"
          % (vec["ticks"], vec["final_hash"][:12], vec["merkle_root"][:12], C.verify_vector(vec)))
    bad = dict(vec, final_hash="0" * 64)
    print("   a port that diverges -> verify=%s\n" % (C.verify_vector(bad),))

    print("E) STRESS (1,000 bodies — reference speed, NOT the target):")
    bodies = [K.body(i, [(i % 20) - 10, 5 + (i // 20) % 5, (i * 7 % 20) - 10],
                     [(i % 5) - 2, 0, (i % 3) - 1], [1, 1, 1]) for i in range(1000)]
    w = K.make_world(bodies, bounds=((-30, 0, -30), (30, 40, 30)), gravity=10, dt_ms=16)
    t0 = time.time()
    for _ in range(20):
        w = K.step(w)
    print("   1,000 bodies × 20 ticks in %.2fs -> hash %s\n" % (time.time() - t0, K.state_hash(w)[:12]))
    print("   This Python is the deterministic *reference* (the conformance oracle). The 240fps engine is a")
    print("   native SIMD port that must reproduce these hashes. Determinism makes exploits detectable and")
    print("   runs replayable — it does not make state 'immutable' or eliminate lag. integrity != truth.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[AetherPulse] set PYTHONHASHSEED=0 (state hashes must match across machines).\n\n")
        raise SystemExit(2)
    main()
