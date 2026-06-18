"""
VeriVerse/physics.py — deterministic integer "falling sand" cellular automaton (a 2-D cross-section toy).

Grid cells: AIR=0, SOLID=1, SAND=2. Each step, sand falls straight down if empty, else diagonally; the scan
order is fixed, so evolution is bit-for-bit deterministic. Bounded by a step budget (the `fuel` discipline)
so it always terminates. This is a TOY physics for demonstrating replayable simulation, not a real solver.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cores import canon

AIR, SOLID, SAND = 0, 1, 2


def step(grid):
    """One deterministic update. Bottom-up scan so a grain moves at most once per step. Returns (grid, moved)."""
    h = len(grid)
    w = len(grid[0])
    new = [row[:] for row in grid]
    moved = False
    for y in range(h - 2, -1, -1):                          # skip bottom row
        for x in range(w):
            if new[y][x] != SAND:
                continue
            if new[y + 1][x] == AIR:
                new[y + 1][x] = SAND; new[y][x] = AIR; moved = True
            elif x > 0 and new[y + 1][x - 1] == AIR:
                new[y + 1][x - 1] = SAND; new[y][x] = AIR; moved = True
            elif x < w - 1 and new[y + 1][x + 1] == AIR:
                new[y + 1][x + 1] = SAND; new[y][x] = AIR; moved = True
    return new, moved


def settle(grid, max_steps=10000):
    """Run until stable or the step budget is spent. Returns (grid, steps, hash). Deterministic."""
    steps = 0
    while steps < max_steps:
        grid, moved = step(grid)
        steps += 1
        if not moved:
            break
    return grid, steps, canon.canon_hash(grid)
