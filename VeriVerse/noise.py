# SPDX-License-Identifier: AGPL-3.0-only
"""
VeriVerse/noise.py — deterministic INTEGER value-noise terrain. No floats, no language-dependent RNG.

Lattice corners get a hash-derived integer height; interior points are integer bilinear interpolations.
Identical on any machine for a given seed — that is the whole point.
"""
import hashlib


def _hash_int(seed, *coords):
    b = ("%d|" % seed) + "|".join(str(c) for c in coords)
    return int.from_bytes(hashlib.sha256(b.encode()).digest()[:8], "big")


def _corner(seed, gx, gz, amp):
    return _hash_int(seed, "c", gx, gz) % amp


def height2d(seed, x, z, spacing=8, amp=24, base=8):
    """Integer bilinear value noise: terrain height at (x,z). Deterministic, smooth, float-free."""
    gx, gz = x // spacing, z // spacing
    tx, tz = x - gx * spacing, z - gz * spacing
    h00 = _corner(seed, gx, gz, amp); h10 = _corner(seed, gx + 1, gz, amp)
    h01 = _corner(seed, gx, gz + 1, amp); h11 = _corner(seed, gx + 1, gz + 1, amp)
    a = h00 + (h10 - h00) * tx // spacing
    b = h01 + (h11 - h01) * tx // spacing
    return base + a + (b - a) * tz // spacing
