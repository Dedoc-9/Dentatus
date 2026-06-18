"""
AetherPulse/kernel.py — the deterministic 3-D fixed-point rigid-body reference kernel.

Bodies are axis-aligned boxes with fixed-point position/velocity (no float anywhere). One tick: integrate
gravity, integrate motion, resolve wall collisions, resolve pairwise AABB overlaps — all in a FIXED,
id-sorted order, so the evolution is bit-for-bit identical on any machine and in any language that
implements the same integer ops. This Python is the CONFORMANCE ORACLE: a native SIMD port is correct iff
it reproduces these state hashes.

HONEST BOUND: this is the deterministic *semantics*, not the *performance* engine — Python is the reference,
not the 240fps target. Determinism + verification make exploits DETECTABLE and runs REPLAYABLE; they do not
make state "immutable" or eliminate network lag. integrity != truth: it proves the sim ran exactly so, never
that it models real physics.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cores import to_fp, fp_mul, canon

AXES = (0, 1, 2)


def _copy_body(b):
    """Deep-copy a body INCLUDING its vectors -- a shallow dict() would share pos/vel lists and let one
    run mutate another (a determinism leak)."""
    return {**b, "pos": list(b["pos"]), "vel": list(b["vel"]), "half": list(b["half"])}


def vadd(a, b):
    return [a[i] + b[i] for i in AXES]


def vscale(s_fp, v):
    return [fp_mul(s_fp, v[i]) for i in AXES]


def _fp(x):
    """Coerce a coordinate to fixed-point. Accepts an int (whole units) or a (num, den) rational. Floats are
    refused on purpose -- they are exactly what determinism forbids."""
    if isinstance(x, tuple):
        return to_fp(x[0], x[1])
    if isinstance(x, int) and not isinstance(x, bool):
        return to_fp(x)
    raise TypeError("coordinate must be int or (num, den) rational, not %r" % type(x).__name__)


def body(bid, pos, vel, half, restitution=(8, 10)):
    """A box body. pos/vel/half as ints (whole units) or (num,den) rationals -- never floats; restitution e/d."""
    return {"id": bid, "pos": [_fp(p) for p in pos], "vel": [_fp(v) for v in vel],
            "half": [_fp(h) for h in half], "e_num": restitution[0], "e_den": restitution[1]}


def make_world(bodies, bounds, gravity=10, dt_ms=8):
    """bounds = ((minx,miny,minz),(maxx,maxy,maxz)) in display units; gravity m/s^2 (down +y? no, -y)."""
    return {"bodies": [_copy_body(b) for b in bodies],
            "min": [_fp(c) for c in bounds[0]], "max": [_fp(c) for c in bounds[1]],
            "g": _fp(gravity), "dt": to_fp(dt_ms, 1000), "tick": 0}


def _restitute(v, b):
    return -(fp_mul(v, to_fp(b["e_num"], b["e_den"])))      # reflect with restitution e (fixed-point)


def step(world):
    """Advance one tick. Pure: returns a new world. Deterministic, integer-only."""
    w = {**world, "bodies": [_copy_body(b) for b in world["bodies"]], "tick": world["tick"] + 1}
    bodies = sorted(w["bodies"], key=lambda b: b["id"])      # fixed order -> determinism
    dt = w["dt"]
    # integrate gravity (-y) + motion
    for b in bodies:
        b["vel"][1] -= fp_mul(w["g"], dt)
        b["pos"] = vadd(b["pos"], vscale(dt, b["vel"]))
    # wall collisions (clamp + reflect)
    for b in bodies:
        for ax in AXES:
            lo = w["min"][ax] + b["half"][ax]
            hi = w["max"][ax] - b["half"][ax]
            if b["pos"][ax] < lo:
                b["pos"][ax] = lo; b["vel"][ax] = _restitute(b["vel"][ax], b)
            elif b["pos"][ax] > hi:
                b["pos"][ax] = hi; b["vel"][ax] = _restitute(b["vel"][ax], b)
    # pairwise AABB overlap resolution (equal-mass elastic along min-penetration axis)
    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            a, c = bodies[i], bodies[j]
            pen = []
            overlap = True
            for ax in AXES:
                d = abs(a["pos"][ax] - c["pos"][ax])
                reach = a["half"][ax] + c["half"][ax]
                if d >= reach:
                    overlap = False; break
                pen.append((reach - d, ax))
            if not overlap:
                continue
            _, ax = min(pen)                                  # separate along least-penetrating axis
            push = (min(pen)[0]) // 2 + 1
            if a["pos"][ax] <= c["pos"][ax]:
                a["pos"][ax] -= push; c["pos"][ax] += push
            else:
                a["pos"][ax] += push; c["pos"][ax] -= push
            a["vel"][ax], c["vel"][ax] = c["vel"][ax], a["vel"][ax]   # equal-mass elastic: swap axis velocity
    w["bodies"] = bodies
    return w


def state_hash(world):
    """Content address of the world state (positions/velocities are integers -> bit-stable)."""
    canon_bodies = [{"id": b["id"], "pos": b["pos"], "vel": b["vel"], "half": b["half"]}
                    for b in sorted(world["bodies"], key=lambda b: b["id"])]
    return canon.canon_hash({"tick": world["tick"], "bodies": canon_bodies,
                             "bounds": [world["min"], world["max"]]})


def run(world, ticks):
    """Run `ticks` steps; return (final_world, per-tick state hashes)."""
    hashes = [state_hash(world)]
    for _ in range(ticks):
        world = step(world)
        hashes.append(state_hash(world))
    return world, hashes
