"""
forge/hilbert_compress_proof.py — Spatial-spiral (Hilbert) calibration MEASUREMENT.

NOT a sealed experiment and NOT licensed for the live game (the 48-tile duel has ~7x frame-time headroom,
EXP-532). This is the data that would justify a Hilbert linearization IF and WHEN the world scales — banked
as the candidate EXP-507 scaling primitive. Two honest metrics on a synthetic 64x64 (4096-leaf) section:

  * COMPRESSION: gzip size of a delta-telemetry frame serialized row-major vs Hilbert order.
  * BLOCK LOCALITY (the real coherence claim): average linear-index SPAN of every k x k spatial block.
    A small span means a 2-D neighborhood occupies a tight contiguous range of the 1-D order -> contiguous
    LRU eviction / cache lines (EXP-606/518). This is what Hilbert is FOR. (The draft's "row-sweep jump"
    metric measured the opposite axis and favored row-major trivially; replaced.)
"""
import json, zlib, math

N = 64; N_TILES = N * N


def xy2d(n, x, y):
    d = 0; s = n // 2
    while s > 0:
        rx = 1 if (x & s) else 0; ry = 1 if (y & s) else 0
        d += s * s * ((3 * rx) ^ ry)
        if ry == 0:
            if rx == 1: x = s - 1 - x; y = s - 1 - y
            x, y = y, x
        s //= 2
    return d


def d2xy(n, d):
    t = d; x = y = 0; s = 1
    while s < n:
        rx = 1 & (t // 2); ry = 1 & (t ^ rx)
        if ry == 0:
            if rx == 1: x = s - 1 - x; y = s - 1 - y
            x, y = y, x
        x += s * rx; y += s * ry; t //= 4; s *= 2
    return x, y


def hardening_checks():
    seen = set()
    for y in range(N):
        for x in range(N):
            d = xy2d(N, x, y)
            if not (0 <= d < N_TILES): raise AssertionError("index out of range")
            if d2xy(N, d) != (x, y): raise AssertionError("xy2d/d2xy not inverse at (%d,%d)" % (x, y))
            seen.add(d)
    if len(seen) != N_TILES: raise AssertionError("Hilbert order is not a bijection (collisions)")
    return True


def synth_grid():
    # a localized fluid breach (disk) in a sea of solid cover — a realistic combat frame
    cx, cy, r = 32, 32, 12; g = []
    for y in range(N):
        for x in range(N):
            fluid = math.hypot(x - cx, y - cy) <= r
            g.append({"x": x, "y": y, "chi": 0.92 if fluid else 0.05,
                      "phase": "fluid" if fluid else "solid", "wi": 0.45 if fluid else 0.02,
                      "sign": (1 if x < cx else -1)})   # coherent bisection (realistic Fiedler sign), not x-parity
    return g


def payload(grid, index_of):
    out = [None] * N_TILES
    for e in grid:
        i = index_of(e["x"], e["y"])
        out[i] = {"id": i, "chi": e["chi"], "phase": e["phase"], "wi": e["wi"], "sign": e["sign"]}
    return json.dumps(out, separators=(",", ":")).encode()


def block_span(index_of, k=4):
    spans = []
    for by in range(0, N, k):
        for bx in range(0, N, k):
            idx = [index_of(bx + dx, by + dy) for dy in range(k) for dx in range(k)]
            spans.append(max(idx) - min(idx))
    return sum(spans) / len(spans)


def run():
    hardening_checks()
    g = synth_grid()
    rm = lambda x, y: y * N + x
    hb = lambda x, y: xy2d(N, x, y)
    row_b = payload(g, rm); hil_b = payload(g, hb)
    row_z = zlib.compress(row_b, 9); hil_z = zlib.compress(hil_b, 9)
    gain = (1.0 - len(hil_z) / len(row_z)) * 100.0
    rm_span = block_span(rm); hb_span = block_span(hb)
    print("DENTATUS FORGE · Hilbert spatial-spiral calibration (64x64 = 4096 leaves)")
    print("  Hilbert order bijection + inverse ............ OK")
    print("  COMPRESSION (gzip-9 of a delta frame):")
    print("    row-major  : %6d B raw -> %5d B" % (len(row_b), len(row_z)))
    print("    hilbert    : %6d B raw -> %5d B" % (len(hil_b), len(hil_z)))
    print("    bandwidth reduction (data-dependent) ....... %5.1f%%" % gain)
    print("  BLOCK LOCALITY (avg 1-D index span of a 4x4 spatial block; lower = tighter eviction):")
    print("    row-major span ............................. %7.1f" % rm_span)
    print("    hilbert span ............................... %7.1f  (%.1fx tighter)" % (hb_span, rm_span / hb_span))
    fails = []
    if hb_span >= rm_span: fails.append("Hilbert did NOT improve block locality")
    print("  VIOLATIONS:", len(fails))
    for f in fails: print("   !", f)
    return fails


if __name__ == "__main__":
    import sys
    sys.exit(1 if run() else 0)
