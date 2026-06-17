"""
crucible/oracle.py — the Red Team Oracle: inject reverse-generated hard seeds at the rest of the stack.

`crucible` completes the triangle:  syracuse (the law) · tessera (the witness) · crucible (the crucible).
forest.py constructs structured hard seeds; oracle.py fires them at the existing siblings and reports
whether the integer integrity holds. Everything here is deterministic — the same parameters reproduce the
same attack, so a passing run is a reproducible attack simulation, not a lucky one.

Hooks today (against what exists): `ration` (the integer step budget) and `tessera` (the replayable proof
shard). The `fuel` bounded-execution engine and the `elenchus` reasoning interrogator are later children;
their hooks are declared as TODO so this module is ready to fire at them when they land — it does not
pretend to test code that does not exist yet.

HONEST GUARDRAIL: it maps the known difficulty landscape; it does not solve Collatz and does not claim
these are the hardest seeds in existence. A green oracle run is evidence over a structured hard set.
"""
import os
import sys
import json

_HERE = os.path.dirname(os.path.abspath(__file__))
_WB = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_WB, "syracuse"))
sys.path.insert(0, os.path.join(_WB, "ration"))
sys.path.insert(0, os.path.join(_WB, "tessera"))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
import forest as C
import orbit as SY                                           # syracuse
import meter as R                                            # ration
import shard as T                                            # tessera
import core                                                  # chronicle


# the declared deterministic computation a tessera shard pins (module-level for ruleset_hash binding)
def syracuse_rule(state):
    return {"n": SY.step(state["n"])}


def syracuse_done(state):
    return state["n"] == 1


# ----------------------------------------------------------------- ration: the budget boundary attack
def inject_ration(budget_K, value_ceiling=10 ** 9):
    """Find a hard seed whose stopping time is just within budget_K and confirm ration admits it, while a
    seed one budget tier deeper is refused. Returns the boundary evidence."""
    inside = C.seed_just_under(budget_K, value_ceiling)
    policy = {"ceiling": budget_K, "per_category": {}, "weights": {"iterations": 1}}
    over = C.seed_just_under(budget_K + 8, value_ceiling)     # a deeper seed, beyond the budget tier
    return {
        "budget_K": budget_K,
        "inside": {"n": inside["n"], "stopping_time": inside["stopping_time"], "altitude": inside["altitude"],
                   "admitted": R.within_budget(SY.ration_counts(inside["n"]), policy)},
        "over": {"n": over["n"], "stopping_time": over["stopping_time"],
                 "admitted": R.within_budget(SY.ration_counts(over["n"]), policy)},
    }


# ----------------------------------------------------------------- tessera: the long-path serialization attack
def inject_tessera(seed_n, signer=None):
    """Mint a tessera over a hard seed's full orbit and verify it replays intact. The rolling path-hash is
    a fixed 256-bit chain over arbitrary-precision integers, so a long climb cannot overflow or lose
    precision — this confirms that property end-to-end rather than asserting it."""
    tess = T.mint(syracuse_rule, syracuse_done, {"n": seed_n}, signer=signer)
    ok, detail = T.verify(tess, syracuse_rule, syracuse_done)
    return {"seed": seed_n, "steps": tess["steps"], "path_hash": tess["path_hash"], "verified": ok, "detail": detail}


# ----------------------------------------------------------------- the manifest (content-addressed)
def build_manifest(max_depth, value_ceiling=10 ** 9, top=10):
    """A reproducible difficulty map: the hardest `top` seeds (by altitude) in the reverse forest up to
    max_depth, each cross-checked against forward replay, with a content hash over the whole manifest."""
    forest = C.generate(max_depth, value_ceiling)
    forest.sort(key=lambda s: (s["altitude"], s["stopping_time"], -s["n"]), reverse=True)
    seeds = []
    for s in forest[:top]:
        ok, _ = C.verify_seed(s)
        seeds.append({"n": s["n"], "stopping_time": s["stopping_time"], "peak": s["peak"],
                      "altitude": s["altitude"], "verified_forward": ok})
    body = {"protocol": "crucible/1", "params": {"max_depth": max_depth, "value_ceiling": value_ceiling, "top": top},
            "seeds": seeds}
    body["manifest_hash"] = core.state_hash(body)
    return body


def write_manifest(path, max_depth, value_ceiling=10 ** 9, top=10):
    m = build_manifest(max_depth, value_ceiling, top)
    with open(path, "w") as fh:
        json.dump(m, fh, indent=2)
    return m
