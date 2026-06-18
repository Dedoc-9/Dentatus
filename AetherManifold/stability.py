"""
AetherManifold/stability.py — stability as a measured OBSERVABLE of the trace, never a derived truth.

Two deterministic, exact diagnostics:
  * shadowing distance — run the SAME optimizer from X0 and from a 1-ulp perturbation; the exact integer
    distance between the two trajectories per step is the discrete sensitivity. Because both runs are
    integer-deterministic, this isolates *algorithmic* sensitivity from hardware noise entirely.
  * Lyapunov estimate — the mean log-growth of that distance (a float OBSERVABLE): > 0 ≈ locally diverging
    (sensitive / chaotic-leaning), ≤ 0 ≈ contracting. It is read out alongside the trajectory; it never
    gates a step.

HONEST BOUND: a bounded trajectory over N steps is *computational evidence* of stability within the
simulation bounds — it is an observed property of the trace, NOT a proof the modelled system is stable
outside those bounds or for all initial conditions.
"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cores import F
import riemann as R


def shadowing_distance(Xa, Xb):
    return max(abs(Xa[i][j] - Xb[i][j]) for i in range(len(Xa)) for j in range(len(Xa[0])))


def perturb(X0, ulp=1):
    Y = [row[:] for row in X0]
    Y[0][0] += ulp
    return Y


def co_run(X0, grad_fn, eta_fp, steps, ulp=1):
    """Run two trajectories (X0 and a 1-ulp perturbation) in lockstep; return per-step shadowing distances."""
    Xa = R.retract([r[:] for r in X0])
    Xb = R.retract(perturb(X0, ulp))
    dist = [shadowing_distance(Xa, Xb)]
    for _ in range(steps):
        Xa = R.retract(F.sub(Xa, F.scalar(eta_fp, R.proj_tangent(Xa, grad_fn(Xa)))))
        Xb = R.retract(F.sub(Xb, F.scalar(eta_fp, R.proj_tangent(Xb, grad_fn(Xb)))))
        dist.append(shadowing_distance(Xa, Xb))
    return dist


def lyapunov_estimate(distances):
    """Mean log-growth of the shadowing distance (float observable). >0 sensitive, <=0 contracting."""
    rates = [math.log(distances[i] / distances[i - 1])
             for i in range(1, len(distances)) if distances[i] > 0 and distances[i - 1] > 0]
    return sum(rates) / len(rates) if rates else 0.0
