"""
causal_runtime/adversary.py — try to BREAK the field, not prove it. Where does future_surface stop being valid?

Every other benchmark tests future_surface when future-relevance is *already correctly represented*. The
high-value result is the opposite: the exact condition under which the field STOPS being a valid allocator.
Three adversaries — the field being **late, wrong, or incomplete** — each shows the naive field LOSING, and
each implies a specific repair (recorded as a boundary, not hidden):

  LATE      stale-field latency : a correct-but-OLD field loses to fresh distance past a staleness boundary.
            Repair: refresh within the importance coherence time (cf. `fallback.py`'s reliability signal).
  WRONG     improbable futures  : RAW consequence overspends on high-consequence / LOW-probability branches.
            Repair: expected value `consequence × probability`. (possibility ≠ likelihood — the composite's
            possibility axis is not a probability, so it does not substitute for likelihood weighting.)
  GAMEABLE  anti-gaming         : an actor can inflate its OWN consequence to attract budget. Self-generated
            consequence is exploitable. Repair: `impact × independent_evidence` (proposal ≠ authority, for
            allocation).

Deterministic integer math. Stdlib only.
"""
import random

from allocation import allocate, captured

# ---------------- LATE: stale-field latency ----------------------------------

def _evolving_world(t, n=40, seed=1, coherence=12):
    """Item importance M drifts; it is re-randomised every `coherence` ticks (the importance coherence time).
    `future_surface` is a faithful estimate of the CURRENT M; `distance` is a stable, moderate estimate."""
    items = []
    for i in range(n):
        r = random.Random(seed * 100000 + (t // coherence) * 1000 + i)   # changes each coherence window
        M = r.randint(1, 1000)
        items.append({"id": "o%d" % i, "M": M, "cost": (i % 9) + 1,
                      "future_surface": max(1, M + r.randint(-30, 30)),   # faithful to CURRENT M
                      "distance": max(1, M + r.randint(-450, 450))})       # stable moderate floor
    return items


def stale_latency(staleness, frames=48, coherence=12, budget_frac=0.3):
    """A field computed `staleness` ticks ago vs a FRESH distance allocator. Returns captured-M for each.
    When staleness exceeds the coherence time the stale field allocates to yesterday's importances."""
    fut = dist = 0
    for t in range(staleness, frames):
        live = _evolving_world(t, coherence=coherence)
        old = _evolving_world(t - staleness, coherence=coherence)          # the field the runtime is still holding
        budget = int(sum(o["cost"] for o in live) * budget_frac)
        # allocate by the STALE future_surface, but score on LIVE M:
        old_scores = {o["id"]: o["future_surface"] for o in old}
        for o in live:
            o["stale_future"] = old_scores.get(o["id"], 1)
        fut += captured(live, allocate(live, budget, "stale_future"))
        dist += captured(live, allocate(live, budget, "distance"))
    return {"stale_future": fut, "fresh_distance": dist}


def stale_boundary(frames=48, coherence=12):
    """The breaking point: the largest staleness at which the (stale) field still beats fresh distance."""
    last_good = 0
    for s in range(0, 24):
        r = stale_latency(s, frames=frames, coherence=coherence)
        if r["stale_future"] >= r["fresh_distance"]:
            last_good = s
        else:
            break
    return last_good


# ---------------- WRONG: improbable futures ----------------------------------

def improbable_world(n=60, seed=2):
    """High consequence is ANTI-correlated with probability. True importance is EXPECTED consequence M = C·p.
    `raw` = consequence alone (the naive field); `expected` = C·p (the repair); `distance` = moderate floor."""
    rng = random.Random(seed)
    items = []
    for _ in range(n):
        C = rng.randint(50, 1000)
        p = max(1, 1000 - C + rng.randint(-100, 100))                      # permille; high C -> low p
        M = C * p // 1000                                                   # expected consequence
        items.append({"id": "o%d" % len(items), "M": M, "cost": rng.randint(1, 10),
                      "raw": C, "expected": C * p // 1000,
                      "distance": max(1, M + rng.randint(-150, 150))})
    return items


def improbable_test(budget_frac=0.3):
    items = improbable_world()
    b = int(sum(o["cost"] for o in items) * budget_frac)
    return {k: captured(items, allocate(items, b, k)) for k in ("raw", "expected", "distance", "M")}


# ---------------- GAMEABLE: anti-gaming --------------------------------------

def gamed_world(n=50, manipulators=8, seed=3):
    """Genuine items: consequence backed by independent evidence, and they truly matter (M>0). Manipulators:
    huge SELF-generated consequence, ~0 independent evidence, and they do NOT matter (M≈0). `raw` scores by
    consequence (funds the manipulators); `guarded` = consequence × independent_evidence (ignores them)."""
    rng = random.Random(seed)
    items = []
    for i in range(n):
        genuine = i >= manipulators
        if genuine:
            cons = rng.randint(50, 500); ev = rng.randint(600, 1000); M = cons
        else:
            cons = rng.randint(800, 1000); ev = rng.randint(0, 50); M = 0   # loud but worthless
        items.append({"id": "o%d" % i, "M": M, "cost": rng.randint(1, 10),
                      "raw": cons, "guarded": cons * ev // 1000,
                      "distance": rng.randint(1, 1000)})
    return items


def gamed_test(budget_frac=0.3):
    items = gamed_world()
    b = int(sum(o["cost"] for o in items) * budget_frac)
    return {k: captured(items, allocate(items, b, k)) for k in ("raw", "guarded", "distance", "M")}


def verdict():
    sb = stale_boundary()
    imp = improbable_test()
    gam = gamed_test()
    late_breaks = sb < 24                                   # there IS a staleness past which the field loses
    wrong_breaks = imp["raw"] < imp["distance"] and imp["expected"] > imp["raw"]   # raw loses; ×p repairs
    gameable_breaks = gam["raw"] < gam["guarded"] and gam["raw"] < gam["M"]        # raw funds manipulators
    ok = late_breaks and wrong_breaks and gameable_breaks
    return ("field-has-measured-boundaries-late-wrong-gameable" if ok else "inconclusive"), {
        "stale_boundary": sb, "improbable": imp, "gamed": gam}


if __name__ == "__main__":
    sb = stale_boundary()
    imp = improbable_test(); gam = gamed_test()
    iN = max(1, imp["M"]); gN = max(1, gam["M"])
    print("Adversarial boundaries — where future_surface STOPS being valid:\n")
    print("  LATE      stale field beats fresh distance up to staleness = %d ticks (coherence time = 12);" % sb)
    print("            past that the correct-but-old field allocates to yesterday's importances and LOSES.")
    print("  WRONG     improbable futures (high consequence ⟂ low probability), captured of oracle:")
    print("            raw consequence=%3d%%   expected (C×p)=%3d%%   distance=%3d%%   -> RAW loses to distance; ×p repairs it"
          % (100 * imp["raw"] // iN, 100 * imp["expected"] // iN, 100 * imp["distance"] // iN))
    print("  GAMEABLE  self-inflated consequence, captured of oracle:")
    print("            raw consequence=%3d%%   guarded (×independent evidence)=%3d%%   -> RAW funds the manipulators"
          % (100 * gam["raw"] // gN, 100 * gam["guarded"] // gN))
    label, _ = verdict()
    print("\nVERDICT:", label)
    print("REPAIRS IMPLIED:  late→refresh within coherence (cf. fallback.py) ; wrong→expected value C×p"
          " (possibility ≠ likelihood) ; gameable→impact × independent_evidence (proposal ≠ authority).")
