"""
toolkit.monitor — runtime drift monitoring + quarantine.

A certificate attests performance under the tested regimes. After deployment the world drifts, so the
certificate must be kept honest over time. `Monitor.observe(world)` tracks how far the live input has
moved from the distribution the policy was certified on, and reports a lifecycle status:

    CERTIFIED   -> live input matches the certified distribution
    DEGRADED    -> drift is rising; re-evaluation required
    QUARANTINED -> outside the evidence boundary; the certificate no longer applies

A policy is never declared "wrong"; it is declared OUTSIDE ITS EVIDENCE BOUNDARY. This is the runtime
form of the law the toolkit already proved: stale signal -> failure.

HONEST LIMITATION (asserted in benchmarks): a distribution monitor sees only the MARGINALS of the
observable signals, never the signal -> outcome relationship. It therefore detects an input-domain
shift but is BLIND to a confidently-misleading (adversarial) world whose signals look statistically
normal while their meaning has inverted.  New bound:  observable drift != semantic drift.

Deterministic: integer means, integer EMA, stdlib only.
"""
from __future__ import annotations

from .benchmarks import make_world


def fingerprint(world):
    """Observable signature of a world: the mean of the primary signals. No truth (M) is read."""
    n = len(world) or 1
    return (sum(o["consequence"] for o in world) // n,
            sum(o["uncertainty"] for o in world) // n)


def divergence(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def baseline_fingerprint(world_fn=None, samples=8):
    """The certified-distribution fingerprint: average over several clean worlds."""
    world_fn = world_fn or make_world
    fps = [fingerprint(world_fn(seed=s)) for s in range(samples)]
    return (sum(f[0] for f in fps) // samples, sum(f[1] for f in fps) // samples)


class Monitor:
    CERTIFIED, DEGRADED, QUARANTINED = "CERTIFIED", "DEGRADED", "QUARANTINED"

    def __init__(self, baseline=None, certified_tol=130, degraded_tol=280):
        self.baseline = baseline or baseline_fingerprint()
        self.certified_tol = certified_tol
        self.degraded_tol = degraded_tol
        self.ema = 0
        self.ticks = 0
        self.status = self.CERTIFIED

    def observe(self, world):
        """Ingest one live world; update the drift EMA and the lifecycle status. Returns the status."""
        d = divergence(fingerprint(world), self.baseline)
        self.ema = d if self.ticks == 0 else (self.ema * 3 + d) // 4
        self.ticks += 1
        self.status = (self.CERTIFIED if self.ema < self.certified_tol
                       else self.DEGRADED if self.ema < self.degraded_tol
                       else self.QUARANTINED)
        return self.status

    def report(self):
        return ("monitor: status=%s  drift_ema=%d  (certified<%d<=degraded<%d<=quarantined)  ticks=%d"
                % (self.status, self.ema, self.certified_tol, self.degraded_tol, self.ticks))

    def __repr__(self):
        return "Monitor(status=%s, ema=%d, ticks=%d)" % (self.status, self.ema, self.ticks)
