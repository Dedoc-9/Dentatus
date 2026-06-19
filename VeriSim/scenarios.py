# SPDX-License-Identifier: AGPL-3.0-only
"""
VeriSim/scenarios.py — deterministic fixed-point physics scenarios (toy models, clearly labelled).

Each scenario is a pure integer step function + a done predicate, so it is bit-for-bit replayable and can be
proven with a `tessera` shard. These are TOY KINEMATIC MODELS for demonstrating verifiable simulation — they
are NOT validated vehicle/medical/financial models, and a clean replay says nothing about real-world safety.

Registered scenarios:
  * "brake_1d"  — a point mass decelerating to rest (an emergency-brake stopping-distance toy).
  * "projectile_1d" — vertical throw under constant gravity until it returns to ground.
All state is fixed-point integers (see aether.fixedpoint); positions/velocities scaled by SCALE.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cores import to_fp, fp_mul


# ----------------------------------------------------------------- brake_1d
def brake_step(state):
    if state["halted"]:
        return state
    v = state["v"] - fp_mul(state["a"], state["dt"])         # decelerate
    if v < 0:
        v = 0
    p = state["p"] + fp_mul(v, state["dt"])
    t = state["t"] + 1
    halted = (v == 0) or (t >= state["max_steps"])
    return {**state, "v": v, "p": p, "t": t, "halted": halted}


def brake_done(state):
    return bool(state["halted"])


def brake_seed(v0_mps, a_mps2, dt_ms, max_steps=100000):
    """A braking scenario seed in fixed point. v0 m/s, deceleration a m/s^2, timestep dt ms."""
    return {"p": 0, "v": to_fp(v0_mps), "a": to_fp(a_mps2), "dt": to_fp(dt_ms, 1000),
            "t": 0, "max_steps": max_steps, "halted": False}


# ----------------------------------------------------------------- projectile_1d
def projectile_step(state):
    if state["halted"]:
        return state
    v = state["v"] - fp_mul(state["g"], state["dt"])         # gravity
    p = state["p"] + fp_mul(v, state["dt"])
    t = state["t"] + 1
    halted = (p <= 0 and t > 1) or (t >= state["max_steps"])  # back to ground
    if p < 0:
        p = 0
    return {**state, "v": v, "p": p, "t": t, "halted": halted}


def projectile_done(state):
    return bool(state["halted"])


def projectile_seed(v0_mps, g_mps2, dt_ms, max_steps=100000):
    return {"p": 0, "v": to_fp(v0_mps), "g": to_fp(g_mps2), "dt": to_fp(dt_ms, 1000),
            "t": 0, "max_steps": max_steps, "halted": False}


REGISTRY = {
    "brake_1d": (brake_step, brake_done),
    "projectile_1d": (projectile_step, projectile_done),
}
