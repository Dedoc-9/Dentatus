"""
airlock/adapters_kv.py — a SECOND reality for the membrane: deterministic config / repo state.

This proves the airlock is the GENERAL reality-transition membrane, not "an LLM physics feature." Reality
here is a key-value store (config, flags, repo metadata, deployment knobs) — not physics — yet it crosses
the EXACT same membrane (`membrane.propose`) through the EXACT same pipeline. Only the adapter differs.

World:  { "kv": {str: canonical}, "frozen": [str], "epoch": int }
Typed, bounded ops:
    set    {op:"set",    key, value}     set/overwrite a key            (reject if frozen)
    delete {op:"delete", key}            remove a key                   (reject if frozen/absent)
    bump   {op:"bump",   key, by}        add integer `by` to an int key (bounded by budget ‖Δ‖)
    freeze {op:"freeze", key}            make a key immutable            (irreversible)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _wb as C

canon = C.canon
ALLOWED_OPS = ("set", "delete", "bump", "freeze")


class ApplyError(Exception):
    pass


def empty_world():
    return {"kv": {}, "frozen": [], "epoch": 0}


def _copy(w):
    return {"kv": dict(w["kv"]), "frozen": list(w["frozen"]), "epoch": w["epoch"]}


def cost(txn):
    return 1


def apply(world, txn):
    """Pure Apply(p, state) → state'. Never mutates `world`."""
    op = txn["op"]
    w = _copy(world)
    key = txn.get("key")
    if op in ("set", "delete", "bump", "freeze") and (not isinstance(key, str) or not key):
        raise ApplyError("key must be a non-empty string")
    if op in ("set", "delete", "bump") and key in w["frozen"]:
        raise ApplyError("key %r is frozen" % key)
    if op == "set":
        w["kv"][key] = txn["value"]
    elif op == "delete":
        if key not in w["kv"]:
            raise ApplyError("no key %r" % key)
        del w["kv"][key]
    elif op == "bump":
        cur = w["kv"].get(key, 0)
        by = txn.get("by", 1)
        if not isinstance(cur, int) or isinstance(cur, bool) or not isinstance(by, int) or isinstance(by, bool):
            raise ApplyError("bump requires integer key and `by`")
        w["kv"][key] = cur + by
    elif op == "freeze":
        if key not in w["frozen"]:
            w["frozen"] = sorted(w["frozen"] + [key])
    else:
        raise ApplyError("unknown op %r" % op)
    w["epoch"] += 1
    return w


def delta_norm(world, world2):
    """Exact integer ‖Δ‖: count of keys added/removed/changed + |int change| on numeric keys."""
    a, b = world["kv"], world2["kv"]
    n = 0
    for k in set(a) | set(b):
        va, vb = a.get(k), b.get(k)
        if va != vb:
            if isinstance(va, int) and isinstance(vb, int) and not isinstance(va, bool) and not isinstance(vb, bool):
                n += abs(vb - va)
            else:
                n += 1
    return n


def state_hash(world):
    return canon.canon_hash({"kv": world["kv"], "frozen": sorted(world["frozen"]), "epoch": world["epoch"]})


def validate(world2, constraints):
    if "max_keys" in constraints and len(world2["kv"]) > constraints["max_keys"]:
        return False, "key count %d > max_keys %d" % (len(world2["kv"]), constraints["max_keys"])
    for req in constraints.get("require_keys", []):
        if req not in world2["kv"]:
            return False, "required key %r absent" % req
    return True, "ok"


def residual(world2, claims):
    """R_p — proposal residual (telemetry only, never gates)."""
    if not claims:
        return None
    r = 0
    if "expect_key_count" in claims:
        r += abs(len(world2["kv"]) - int(claims["expect_key_count"]))
    if "expect_value" in claims:
        for k, v in claims["expect_value"].items():
            if world2["kv"].get(k) != v:
                r += 1
    return r
