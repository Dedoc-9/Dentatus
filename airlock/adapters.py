"""
airlock/adapters.py — the AetherPulse world adapter for the membrane.

The membrane is kernel-agnostic; this adapter teaches it the AetherPulse world's TYPED, BOUNDED transitions
and how to apply/measure/validate them. Transitions are a small declared set — never free-form code:

    spawn   {op:"spawn",   body:{id,pos,vel,half}}          add a box body
    impulse {op:"impulse", id, dv:[3]}                       add a velocity delta to a body
    advance {op:"advance", ticks:n}                          step the deterministic kernel n ticks

All coordinates are ints or (num,den) rationals — floats are refused at the kernel boundary (determinism).
The kernel is loaded by path so the membrane never imports a module named `kernel` ambiguously.
"""
import os
import sys
import math
import importlib.util

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)

# Load AetherPulse/kernel.py by explicit path (its own _cores resolves fixedpoint/tessera/stasis).
sys.path.insert(0, os.path.join(ROOT, "AetherPulse"))
_spec = importlib.util.spec_from_file_location("aetherpulse_kernel", os.path.join(ROOT, "AetherPulse", "kernel.py"))
K = importlib.util.module_from_spec(_spec)
sys.modules["aetherpulse_kernel"] = K
_spec.loader.exec_module(K)

ALLOWED_OPS = ("spawn", "impulse", "advance")
SCALE = None  # set from kernel's fixedpoint on first use


class ApplyError(Exception):
    pass


def _scale():
    global SCALE
    if SCALE is None:
        SCALE = K.SCALE if hasattr(K, "SCALE") else (1 << 32)
    return SCALE


def _copy_world(w):
    return {**w, "bodies": [K._copy_body(b) for b in w["bodies"]]}


def cost(txn):
    op = txn["op"]
    if op == "spawn":
        return 1
    if op == "impulse":
        return 1
    if op == "advance":
        return int(txn.get("ticks", 0))
    return 1


def apply(world, txn):
    """Pure Apply(p, state) → state'. Never mutates `world`."""
    op = txn["op"]
    if op == "spawn":
        b = txn["body"]
        if any(x["id"] == b["id"] for x in world["bodies"]):
            raise ApplyError("duplicate body id %r" % b["id"])
        try:
            nb = K.body(b["id"], b["pos"], b["vel"], b["half"], tuple(b.get("restitution", (8, 10))))
        except TypeError as e:
            raise ApplyError("bad body coordinate: %s" % e)
        w = _copy_world(world)
        w["bodies"].append(nb)
        return w
    if op == "impulse":
        w = _copy_world(world)
        tgt = next((x for x in w["bodies"] if x["id"] == txn["id"]), None)
        if tgt is None:
            raise ApplyError("no body id %r" % txn["id"])
        dv = txn["dv"]
        if len(dv) != 3:
            raise ApplyError("dv must be length 3")
        try:
            for ax in range(3):
                tgt["vel"][ax] += K._fp(dv[ax])
        except TypeError as e:
            raise ApplyError("bad dv coordinate: %s" % e)
        return w
    if op == "advance":
        n = int(txn.get("ticks", 0))
        if n < 0:
            raise ApplyError("ticks must be >= 0")
        w = world
        for _ in range(n):
            w = K.step(w)
        return w
    raise ApplyError("unknown op %r" % op)


def _vecs(world):
    out = []
    for b in sorted(world["bodies"], key=lambda b: b["id"]):
        out.append((b["id"], list(b["pos"]), list(b["vel"])))
    return {bid: (p, v) for bid, p, v in out}


def delta_norm(world, world2):
    """Exact integer ‖Δ‖_F over matched bodies' (pos,vel); added/removed bodies contribute their own norm."""
    a, b = _vecs(world), _vecs(world2)
    s = 0
    for bid in set(a) | set(b):
        pa, va = a.get(bid, ([0, 0, 0], [0, 0, 0]))
        pb, vb = b.get(bid, ([0, 0, 0], [0, 0, 0]))
        for i in range(3):
            s += (pb[i] - pa[i]) ** 2 + (vb[i] - va[i]) ** 2
    return math.isqrt(s)


def state_hash(world):
    return K.state_hash(world)


def _in_bounds(world):
    for b in world["bodies"]:
        for ax in range(3):
            lo = world["min"][ax] + b["half"][ax]
            hi = world["max"][ax] - b["half"][ax]
            if b["pos"][ax] < lo or b["pos"][ax] > hi:
                return False
    return True


def validate(world2, constraints):
    """Hard admissibility on the candidate (mechanical only)."""
    if "max_bodies" in constraints and len(world2["bodies"]) > constraints["max_bodies"]:
        return False, "body count %d > max_bodies %d" % (len(world2["bodies"]), constraints["max_bodies"])
    if constraints.get("in_bounds") and not _in_bounds(world2):
        return False, "a body lies outside declared bounds"
    return True, "ok"


def residual(world2, claims):
    """R_p — the proposal residual (the LLM's 'ghost'): mismatch between the proposal's DECLARED expectations
    and the kernel's ACTUAL result. Verified-not-trusted; TELEMETRY ONLY — never gates. None if no claims."""
    if not claims:
        return None
    r = 0
    if "expect_body_count" in claims:
        r += abs(len(world2["bodies"]) - int(claims["expect_body_count"]))
    if "expect_state_hash" in claims:
        r += 0 if claims["expect_state_hash"] == state_hash(world2) else 1
    if "expect_tick" in claims:
        r += abs(world2.get("tick", 0) - int(claims["expect_tick"]))
    return r

def validate_strict(world2, constraints):
    """STRICT-tier (severity='strict' or audit) — a toy CAUSAL constraint standing in for the future GR
    layer: no body may exceed a declared speed limit `c_limit` (a light-speed analog). 'causality ≠
    convenience'. Heavy enough to keep off the game hot path; runs inline only at strict severity or via the
    physics court. (Future: Einstein constraint residuals, causal-graph checks, invariant hashing.)"""
    c = constraints.get("c_limit")
    if c is None:
        return True, "no c_limit declared"
    c2 = c * c
    for b in world2["bodies"]:
        speed2 = sum(v * v for v in b["vel"])
        if speed2 > c2:
            return False, "body %r exceeds c_limit (causal violation)" % b["id"]
    return True, "causal"
