"""
forge/menger_klein_proof.py — Non-orientable boundary + fractal substrate CALIBRATION (measured, UN-LICENSED).

A design-compass measurement, NOT a sealed experiment and NOT wired to the live game (the 48-tile duel has
~7x frame-time headroom, EXP-532, and needs neither wraparound nor fractal maps). Two corrections of record
versus an earlier draft, both verified here:

  1. FAITHFUL FRACTAL. The draft computed a Sierpinski carpet on a 64-grid (64 != 3^k), so its porosity was a
     grid-misalignment artifact (its own code yields 28.15%, NOT the pasted 40.62% — that figure was fabricated).
     A faithful carpet needs a 3^k grid; on 81 = 3^4 the level-4 solid count is EXACTLY 8^4 and porosity equals
     the analytic 1-(8/9)^4 = 37.57%. (A planar central slice of a 3-D Menger sponge IS a Sierpinski carpet; the
     "infinite cross-tunnels / sub-quantum" prose is inflation — the substrate is a static 2-D opacity mask.)

  2. CORRECT KLEIN INVOLUTION. The non-orientable horizontal identification is (x,y) ~ (x+GX, GY-1-y); its
     monodromy is an INVOLUTION, so the y-flip must follow the PARITY of horizontal laps. The draft flipped y on
     every wrap event, so two laps wrongly stayed flipped. Fixed: flip by lap parity (one lap flips, two laps
     return identity), which is the only topologically consistent rule for teleports / fast projectiles.
"""
import math


def klein_wrap(x, y, GX, GY):
    laps = math.floor(x / GX)
    xx = x - laps * GX
    yy = y % GY
    if laps % 2 != 0:               # horizontal monodromy is an involution -> flip by lap parity
        yy = GY - 1 - yy
    return int(xx), int(yy)


def carpet_solid(x, y, levels, size):
    # faithful Sierpinski carpet on a 3^levels grid: remove the center of every 3x3 subdivision.
    for l in range(levels):
        s = size // (3 ** (l + 1))
        if (x // s) % 3 == 1 and (y // s) % 3 == 1:
            return False
    return True


def run():
    fails = []
    GX = GY = 81; LEVELS = 4

    # --- KLEIN: invariants of a true non-orientable boundary ---
    one = klein_wrap(GX + 0, 5, GX, GY)            # one lap right -> flip y
    two = klein_wrap(2 * GX + 0, 5, GX, GY)        # two laps -> identity (involution)
    left = klein_wrap(-1, 5, GX, GY)               # off the left edge -> emerge right, flipped
    if one != (0, GY - 1 - 5): fails.append("one-lap wrap did not flip y")
    if two != (0, 5): fails.append("two-lap wrap is not the identity (involution broken)")
    if left != (GX - 1, GY - 1 - 5): fails.append("left-edge wrap incorrect")

    # --- MENGER/CARPET: faithful fractal on a 3^k grid, porosity == analytic ---
    solid = sum(1 for y in range(GY) for x in range(GX) if carpet_solid(x, y, LEVELS, GX))
    total = GX * GY
    analytic_solid = 8 ** LEVELS                    # exact on a 3^LEVELS grid
    if solid != analytic_solid:
        fails.append("carpet solid=%d != analytic 8^%d=%d (grid not faithful)" % (solid, LEVELS, analytic_solid))
    porosity = 100.0 * (total - solid) / total

    # --- RAYCAST across the non-orientable fractal manifold (2 full horizontal laps) ---
    rx, ry = 0, 40; opaque = 0; steps = 2 * GX
    for _ in range(steps):
        rx, ry = klein_wrap(rx + 1, ry, GX, GY)
        if carpet_solid(rx, ry, LEVELS, GX): opaque += 1

    print("DENTATUS FORGE · Menger-Klein topology calibration (81x81 = 3^4 faithful grid)")
    print("  KLEIN boundary (non-orientable, involution):")
    print("    1 lap  -> %s   (y flipped)" % (one,))
    print("    2 laps -> %s   (identity — involution holds)" % (two,))
    print("    off left edge -> %s" % (left,))
    print("  MENGER/Sierpinski carpet (level %d):" % LEVELS)
    print("    solid %d / %d  ==  analytic 8^%d=%d  ->  porosity %.2f%% (analytic %.2f%%)"
          % (solid, total, LEVELS, analytic_solid, porosity, 100 * (1 - (8 / 9) ** LEVELS)))
    print("  RAYCAST %d steps (2 laps) -> opaque %d / clear %d" % (steps, opaque, steps - opaque))
    print("  VIOLATIONS:", len(fails))
    for f in fails: print("   !", f)
    return fails


if __name__ == "__main__":
    import sys
    sys.exit(1 if run() else 0)
