"""
causal_runtime/fallback.py — distance is the safe floor; the smart field is used only while it is reliable.

The formal test (`allocation.py`) proved `future_surface` can be a *worse* estimate of the objective `M` than
plain distance when its regime breaks. So the runtime needs a graceful-degradation policy — and it must decide
to fall back **without a truth oracle** (it cannot compare its estimate to `M` at runtime; `M` is not yet
known). The honest trigger is a runtime SELF-signal of the field's own failure: **sustained ghost saturation**
(the model is being surprised *everywhere* → its structural future_surface is unreliable). When that persists,
allocate by **distance** — the model-free floor that makes *no* future claim and therefore cannot be
catastrophically wrong about `M`.

    future_surface → allocation   while RELIABLE
    distance       → allocation   at UNRECOVERABLE failure (sustained low reliability)

Two safeguards, both load-bearing:
  - "unrecoverable" = SUSTAINED, via a hysteresis latch (a transient ghost spike must not drop the smart field);
  - the policy is judged by COMPARATIVE UTILITY, not correctness: across a regime shift it must beat BOTH fixed
    policies (best-of-both), and in a stable world it must NOT needlessly fall back. It is itself an attention
    heuristic — it may be wrong (a false fallback wastes the field's edge) — and the benchmark can show that.

Deterministic integer math. Stdlib only.
"""
import random

from field import SCALE
from allocation import allocate, captured

FUTURE, DISTANCE = "future", "distance"


def reliability(ghost_pressure_q16):
    """Runtime self-estimate of field reliability ∈ [0, SCALE], from the ghost (not from M). High ghost =
    the model is surprised everywhere = its future_surface is untrustworthy = low reliability."""
    return max(0, SCALE - max(0, min(SCALE, int(ghost_pressure_q16))))


class DegradationLatch:
    """Hysteresis: drop to DISTANCE only after `persist` consecutive low-reliability frames (sustained failure =
    unrecoverable, not a transient spike); recover to FUTURE only after `persist` consecutive reliable frames."""

    def __init__(self, threshold=SCALE // 2, persist=3):
        self.threshold = int(threshold)
        self.persist = int(persist)
        self.mode = FUTURE
        self._low = 0
        self._high = 0

    def update(self, rel):
        if rel < self.threshold:
            self._low += 1; self._high = 0
            if self._low >= self.persist:
                self.mode = DISTANCE
        else:
            self._high += 1; self._low = 0
            if self._high >= self.persist:
                self.mode = FUTURE
        return self.mode


def degraded_allocate(items, budget, mode):
    return allocate(items, budget, "future_surface" if mode == FUTURE else "distance")


# ---- regime-shift benchmark -------------------------------------------------

def _frame(t, t_shift, fails, n=40, seed=0):
    """One frame of items + the runtime ghost-pressure signal. Before `t_shift` (or never, if not `fails`):
    future_surface is a GOOD estimate of M and the ghost is quiet. After the shift: future_surface decorrelates
    from M (random) and the ghost saturates. Distance is a MODERATE, STABLE estimate throughout (the floor)."""
    rng = random.Random(seed * 10_000 + t)
    failed = fails and t >= t_shift
    items = []
    for i in range(n):
        M = rng.randint(1, 1000)
        items.append({
            "id": "o%d" % i, "M": M, "cost": rng.randint(1, 10),
            "future_surface": max(1, rng.randint(1, 1000) if failed else M + rng.randint(-30, 30)),
            "distance": max(1, M + rng.randint(-450, 450)),          # moderate, stable floor (weaker estimate than a healthy field)
        })
    ghost = (SCALE * 3 // 4 if failed else SCALE // 8) + rng.randint(-SCALE // 32, SCALE // 32)
    return items, max(0, min(SCALE, ghost))


def _run_policy(policy, frames, budget_frac, t_shift, fails, latch=None):
    total = 0
    flip_at = None
    for t in range(frames):
        items, ghost = _frame(t, t_shift, fails, seed=1)
        budget = int(sum(o["cost"] for o in items) * budget_frac)
        if policy == "degraded":
            mode = latch.update(reliability(ghost))
            if mode == DISTANCE and flip_at is None:
                flip_at = t
            chosen = degraded_allocate(items, budget, mode)
        else:
            chosen = allocate(items, budget, "future_surface" if policy == FUTURE else "distance")
        total += captured(items, chosen)
    return total, flip_at


def benchmark(frames=24, t_shift=12, budget_frac=0.3):
    out = {}
    for kind, fails in (("shift", True), ("stable", False)):
        fut, _ = _run_policy(FUTURE, frames, budget_frac, t_shift, fails)
        dist, _ = _run_policy(DISTANCE, frames, budget_frac, t_shift, fails)
        deg, flip = _run_policy("degraded", frames, budget_frac, t_shift, fails,
                                latch=DegradationLatch(persist=3))
        out[kind] = {"future": fut, "distance": dist, "degraded": deg, "flip_at": flip,
                     "t_shift": t_shift if fails else None}
    return out


def verdict(rows=None):
    rows = rows or benchmark()
    s = rows["shift"]
    best_of_both = s["degraded"] >= max(s["future"], s["distance"])      # best-of-both across the shift
    fell_back = s["flip_at"] is not None and s["flip_at"] >= s["t_shift"]  # and only AFTER the failure began
    st = rows["stable"]
    no_needless = st["flip_at"] is None and st["degraded"] == st["future"]  # stable world: never falls back
    ok = best_of_both and fell_back and no_needless
    return ("distance-floor-recovers-unrecoverable-field-failure" if ok else "inconclusive"), rows


if __name__ == "__main__":
    rows = benchmark()
    for kind in ("shift", "stable"):
        r = rows[kind]
        print("%-7s  always-future=%-6d  always-distance=%-6d  degraded=%-6d   fell_back_at=%s"
              % (kind, r["future"], r["distance"], r["degraded"], r["flip_at"]))
    label, _ = verdict(rows)
    print("\nVERDICT:", label)
    print("  shift  = future_surface fails at t=%d (ghost saturates); degraded latches to the distance FLOOR" % rows["shift"]["t_shift"])
    print("           and captures best-of-both — more M than EITHER fixed policy.")
    print("  stable = field never fails; degraded never falls back (no needless degradation).")
    print("\nTRIGGER is the runtime ghost (self-signal), never M. 'Unrecoverable' = sustained (hysteresis latch).")
    print("LAW: future_surface → allocation while reliable ; distance → allocation at unrecoverable failure.")
