"""
elenchus/interrogate.py — a verifier for constraint-checked, replayable REASONING TRACES.

Named for the Socratic elenchus: the cross-examination that tests a claim step by step. A producer (an LLM,
or any agent) emits a derivation — premises plus a sequence of steps, each citing a PINNED exact rule —
and elenchus replays it, recomputes every step, and names the exact failing step.

WHAT IT CHECKS (the form / footprints):
  * each step cites a rule in the pinned RULESET (else UNKNOWN_RULE);
  * the step's inputs are already established (else GAP — a skipped premise / missing prior step);
  * re-applying the rule reproduces the step's asserted claim (else FABRICATED — claim != rule output);
  * (optionally) the declared conclusion is actually derived (else INCOMPLETE).
The whole verification is deterministic and replayable, so it mints a `tessera` shard (a stranger
re-runs the interrogation and gets the identical verdict).

WHAT IT DOES **NOT** DO — read this, because the temptation to overclaim here is the strongest in the stack:
  * It does NOT verify the model's INTERNAL reasoning. It checks the emitted trace; a model can emit a
    faithful-looking trace it did not actually use. These are footprints, not the mind.
  * It does NOT prove the reasoning is "valid" or "correct" in general, and it is NOT a logic oracle. It
    enforces exactly the PINNED rules; it cannot judge whether those rules are the right logic, nor whether
    the conclusion is TRUE in the world. (integrity != truth, applied to reasoning.)
  * It does NOT "solve the Halting Problem." Like `fuel`, it SIDESTEPS non-termination by bounding the trace
    (a finite step list); it does not predict halting. And it does NOT escape Gödel: it never claims its own
    consistency — only that a given trace replays under the declared rules.

Pinned rules are inlined into `step_trace` so any change to a rule changes the source-bound ruleset hash —
a verifier proves it ran the SAME rules the shard declares. Imports chronicle/tessera read-only (Sibling Law).
"""
import os
import sys

_WB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
sys.path.insert(0, os.path.join(_WB, "tessera"))
import core                                                  # chronicle/core.py
import shard as TESS                                         # tessera/shard.py

RULES = ("premise", "collatz", "add", "sub", "mul", "compare", "transitivity")


def make_seed(premises, steps):
    """Initial interrogation state. Premises seed the established values; steps are the claimed derivation."""
    vals = {}
    for p in premises:
        vals[p["var"]] = int(p["val"])
    return {"steps": [dict(s) for s in steps], "idx": 0, "vals": vals, "rels": [],
            "fault": None, "halted": False}


def _resolve(x, vals):
    """An operand is an immediate int or a register name; missing names resolve to None (-> GAP)."""
    if isinstance(x, int) and not isinstance(x, bool):
        return x
    return vals.get(x)


def step_trace(state):
    """Apply ONE claimed reasoning step. Pure: returns a new state. Halts (with fault) on the first
    UNKNOWN_RULE / GAP / FABRICATED. The pinned rules live HERE so the source binds the ruleset hash."""
    if state["halted"]:
        return state
    idx = state["idx"]
    steps = state["steps"]
    if idx >= len(steps):
        return {**state, "halted": True}
    vals = dict(state["vals"])
    rels = [list(r) for r in state["rels"]]
    s = steps[idx]
    rule, a, claim = s.get("rule"), s.get("args", {}), s.get("claim")
    fault, produced = None, None

    if rule == "premise":
        produced = {"kind": "val", "var": a["var"], "val": int(a["val"])}      # an explicitly introduced fact
    elif rule == "collatz":
        v = _resolve(a["src"], vals)
        if v is None:
            fault = "GAP: collatz cites unestablished var %r" % a["src"]
        else:                                                                  # mirrors syracuse.step (compressed)
            nxt = v // 2 if v % 2 == 0 else (3 * v + 1) // 2
            produced = {"kind": "val", "var": a["dst"], "val": nxt}
    elif rule in ("add", "sub", "mul"):
        x, y = _resolve(a["a"], vals), _resolve(a["b"], vals)
        if x is None or y is None:
            fault = "GAP: %s operand not established" % rule
        else:
            produced = {"kind": "val", "var": a["dst"],
                        "val": x + y if rule == "add" else x - y if rule == "sub" else x * y}
    elif rule == "compare":
        x, y, op = _resolve(a["lhs"], vals), _resolve(a["rhs"], vals), a["op"]
        if x is None or y is None:
            fault = "GAP: comparison operand not established"
        elif not ((op == "<" and x < y) or (op == "=" and x == y) or (op == ">" and x > y)):
            fault = "FABRICATED: asserted %r %s %r does not hold" % (a["lhs"], op, a["rhs"])
        else:
            produced = {"kind": "rel", "lhs": a["lhs"], "op": op, "rhs": a["rhs"]}
    elif rule == "transitivity":
        op, A, B, C = a["op"], a["a"], a["b"], a["c"]
        if [A, op, B] not in rels or [B, op, C] not in rels:
            fault = "GAP: transitivity premise (%s %s %s) or (%s %s %s) not established" % (A, op, B, B, op, C)
        else:
            produced = {"kind": "rel", "lhs": A, "op": op, "rhs": C}
    else:
        fault = "UNKNOWN_RULE %r" % rule

    if fault is None and core.canonical_bytes(produced) != core.canonical_bytes(claim):
        fault = "FABRICATED: asserted claim does not equal the rule's output"

    if fault is not None:
        return {**state, "halted": True, "fault": {"step": idx, "rule": rule, "reason": fault}}

    if produced["kind"] == "val":
        vals[produced["var"]] = produced["val"]
    else:
        rels.append([produced["lhs"], produced["op"], produced["rhs"]])
    return {"steps": steps, "idx": idx + 1, "vals": vals, "rels": rels, "fault": None, "halted": False}


def done(state):
    return bool(state["halted"])


def _established(state, claim):
    if claim["kind"] == "val":
        return state["vals"].get(claim["var"]) == claim["val"]
    return [claim["lhs"], claim["op"], claim["rhs"]] in state["rels"]


def verify_trace(premises, steps, conclusion=None):
    """Replay a claimed derivation. Returns (ok, fault). fault names the exact step + reason, or None."""
    state = make_seed(premises, steps)
    while not done(state):
        state = step_trace(state)
    if state["fault"] is not None:
        return False, state["fault"]
    if conclusion is not None and not _established(state, conclusion):
        return False, {"step": len(steps), "rule": None, "reason": "INCOMPLETE: declared conclusion not derived"}
    return True, None


# ----------------------------------------------------------------- the verdict is itself a tessera shard
def prove_trace(premises, steps, signer=None, meta=None):
    """Mint a tessera over the interrogation walk: a portable, replayable proof of the verdict."""
    return TESS.mint(step_trace, done, make_seed(premises, steps), max_steps=len(steps) + 2, signer=signer, meta=meta)


def verify_proof(shard, verifier=None):
    return TESS.verify(shard, step_trace, done, verifier=verifier)
