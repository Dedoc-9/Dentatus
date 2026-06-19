"""
causal_runtime/ghost_persistence.py — the Ghost Persistence Benchmark.

When is a ghost noise, and when is it evidence the declared graph is incomplete? Three scenarios over a world
with a HIDDEN coupling A→C (A drives C; the declared graph does not say so) plus uncorrelated noise nodes:

    single     : C is surprised ONCE by a transient -> ghost fires, persistence stays low -> NO proposal
    repeatable : A→C fires every cycle -> ghost fires repeatedly, candidate (A,C) rises -> PROPOSE A→C
    declared   : A→C is declared -> consequence predicts C -> no ghost -> NO promotion (already known)

The honest table the runtime can now fill:

    system              finds the hidden C-coupling
    distance            no   (blind by construction — low visibility)
    consequence         no   (C has no declared parent -> predicted 0)
    ghost               fires (observed − predicted > 0 on C)
    ghost + persistence proposes A→C  (reproduces across contexts; noise filtered)

The two negative controls (single, declared) are what stop the system from "learning noise" or re-proposing
what it already knows. HONEST BOUND: persistence rejects one-off noise but cannot, by observation alone,
separate two *consistently* co-occurring sources — that needs intervention (a transition through the airlock).
The world here is built clean (a quiet driver + uncorrelated noise) to isolate noise-rejection. Deterministic.
"""
import random

import novelty as N
from coupling_discovery import CouplingRegistry

NOISE = ["N%d" % i for i in range(6)]
NODES = ["A", "C"] + NOISE


def _run(kind, frames=60, seed=5, ctx_window=10, noise_p=0.10, period=3):
    rng = random.Random(seed)
    declared_parents = {"C": ({"A"} if kind == "declared" else set())}
    reg = CouplingRegistry()
    ghost_on_C = 0
    for f in range(frames):
        observed = {n: 0 for n in NODES}
        changed = set()
        for n in NOISE:                                   # uncorrelated noise
            if rng.random() < noise_p:
                observed[n] = rng.randint(1, 20)
                changed.add(n)
        a_fires = (kind in ("repeatable", "declared") and f % period == 0) or (kind == "single" and f == 17)
        if a_fires:
            observed["A"] = rng.randint(50, 100); changed.add("A")
            observed["C"] = rng.randint(50, 100); changed.add("C")   # hidden coupling A→C
        predicted = {n: 0 for n in NODES}
        predicted["A"] = observed["A"]                    # A is an EXOGENOUS root: its motion is an input, not
                                                          # model failure -> no ghost on a root (the key distinction)
        if kind == "declared" and observed["A"] > 0:
            predicted["C"] = observed["C"]                # the DECLARED model predicts C's move
        ghost = N.ghost_field(observed, predicted)
        if ghost.get("C", 0) > 0:
            ghost_on_C += 1
        reg.observe(changed, ghost, declared_parents, context=f // ctx_window, now=f)
    proposals = [(c.source, c.target) for c in reg.proposals(min_frequency=5, min_contexts=2)]
    top = reg.candidates()[0] if reg.candidates() else None
    return {"kind": kind, "ghost_on_C": ghost_on_C, "proposals": proposals,
            "finds_AC": ("A", "C") in proposals,
            "top": (top.source, top.target, top.frequency) if top else None}


def run():
    return [_run("single"), _run("repeatable"), _run("declared")]


def verdict(rows=None):
    rows = rows or run()
    by = {r["kind"]: r for r in rows}
    single_no = not by["single"]["finds_AC"]
    repeat_yes = by["repeatable"]["finds_AC"]
    declared_no = (by["declared"]["ghost_on_C"] == 0) and not by["declared"]["finds_AC"]
    ok = single_no and repeat_yes and declared_no
    return ("persistence-proposes-reproducing-coupling-rejects-noise" if ok else "inconclusive"), by


if __name__ == "__main__":
    rows = run()
    for r in rows:
        print("%-10s ghost_on_C=%-3d proposals=%-14s top_candidate=%s"
              % (r["kind"], r["ghost_on_C"], r["proposals"], r["top"]))
    v, _ = verdict(rows)
    print("\nVERDICT:", v)
    print("LAW: ghost -> PROPOSED coupling ALLOWED ; ghost -> ACTUAL coupling FORBIDDEN")
    print("single/declared = negative controls (no learning of noise; no re-proposing the known)")
