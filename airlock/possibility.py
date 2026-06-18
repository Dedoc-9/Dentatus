"""
airlock/possibility.py — the lawful possibility space: measuring the ADMISSIBLE set.

A refinement of "notice what almost happened". The rejection ledger sees only `possible \\ admissible` (the
*inadmissible* — proposals that failed a gate). It is blind to `admissible \\ realized`: transitions that were
fully LAWFUL but simply were not chosen. That second gap is the mathematician's "arbitrary":

    possible  ⊋  admissible  ⊋  realized
       (all)      (lawful)       (chosen)

    "Let x be arbitrary"  ==  "any member of the admissible set; the choice is free within the structure."

This module evaluates a set of candidate proposals against ONE state in SHADOW (throwaway ledgers, nothing
committed, the world never advances), classifies each as admissible (would COMMIT) or inadmissible (and at
which gate), and reports the size of the lawful freedom. The admissible-but-unrealized candidates are a NEW
near-miss category — lawful continuations not taken.

PURE telemetry / analysis: it never commits, never gates the runtime, never enters identity. Honest bound:
it measures the *shape and size* of the admissible set under the DECLARED structure (the airlock + adapter +
constraints + severity) — never that the structure is the right one. The boundary that makes a possibility
admissible is the airlock, exactly as axioms bound a proof and laws bound physics. `integrity ≠ truth`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import membrane as M


def admissible_set(world, candidates, adapter, severity="game"):
    """Shadow-evaluate each candidate proposal against `world` (no commit, world unchanged). Returns the
    lawful freedom at this state.

    Returns:
      candidates       — number evaluated
      admissible       — [index] of candidates that WOULD commit (the lawful set)
      inadmissible     — {index: gate} for those filtered, with the gate that filtered them
      freedom_permille — |admissible|·1000 / candidates  (degrees of lawful freedom at this state)
      per              — [{index, admissible, gate}]
    """
    per = []
    for i, p in enumerate(candidates):
        scratch = M.Ledger()                       # throwaway: shadow only, never the real ledger
        r = M.propose(world, p, adapter, ledger=scratch, severity=severity)
        per.append({"index": i, "admissible": r["ok"], "gate": r["gate"]})
    admissible = [x["index"] for x in per if x["admissible"]]
    inadmissible = {x["index"]: x["gate"] for x in per if not x["admissible"]}
    n = len(candidates)
    return {"candidates": n, "admissible": admissible, "inadmissible": inadmissible,
            "freedom_permille": (len(admissible) * 1000 // n) if n else None, "per": per}


def unrealized_admissible(admset, chosen):
    """The lawful-but-not-chosen continuations: admissible candidates other than the realized one. This is
    the 'arbitrary' remainder — the alternatives that were every bit as admissible as the one that became
    real. (chosen = the index actually committed, or None.)"""
    return [i for i in admset["admissible"] if i != chosen]
