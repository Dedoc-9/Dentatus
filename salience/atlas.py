"""
salience/atlas.py — the Possibility Atlas: possibility treated as TERRAIN, not a per-frame quantity.

You do not recompute terrain every frame; you build it, cache it, and refresh it incrementally. Likewise the
Atlas caches a possibility estimate per region. The runtime SAMPLES it O(1); a bounded maintenance budget
refreshes the dirtiest/most-stale regions each frame. This is what dissolves the 56x measurement paradox:
the expensive signal is amortized into a cached field, and the per-frame cost becomes a lookup.

Pure, deterministic, stdlib. The Atlas holds only ESTIMATES (telemetry) — it never gates physics.
"""


class PossibilityAtlas:
    def __init__(self):
        self.cell = {}          # region -> estimate
        self.age = {}           # region -> frames since refresh

    def build(self, regions, estimate_fn):
        """Initial fill: estimate every region once."""
        for r in regions:
            self.cell[r] = estimate_fn(r)
            self.age[r] = 0
        return self

    def sample(self, region):
        """O(1) lookup — what the 240 Hz allocator uses."""
        return self.cell.get(region, 0.0)

    def tick(self):
        for r in self.age:
            self.age[r] += 1

    def refresh(self, regions, estimate_fn, budget):
        """Re-estimate up to `budget` regions, oldest-first (deterministic, key-ordered ties). Returns the
        regions refreshed. A cheap estimate_fn ⇒ large budget ⇒ the atlas stays fresh; an expensive one ⇒
        small budget ⇒ staleness."""
        order = sorted(regions, key=lambda r: (-self.age.get(r, 0), r))
        done = []
        for r in order[:max(budget, 0)]:
            self.cell[r] = estimate_fn(r)
            self.age[r] = 0
            done.append(r)
        return done

    def staleness(self, regions):
        """Mean age over regions — how out-of-date the atlas is (frames)."""
        ages = [self.age.get(r, 0) for r in regions]
        return sum(ages) // len(ages) if ages else 0
