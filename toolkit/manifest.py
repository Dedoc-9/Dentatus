"""
toolkit.manifest — the Allocation Manifest: a portable, self-describing evidence boundary.

Certificates and reports describe a policy. A manifest packages that description into one artifact a
policy can SHIP with -- a declaration of what it does, what it refuses to do, the signals it actually
reads, the regimes it was tested in, and the channels it is forbidden to touch. The point is to change
the question a downstream engineer asks from:

    "Do I trust this allocator?"            (unanswerable in the abstract)
to:
    "Does this manifest match my environment?"   (a checkable question -- manifest.matches(world))

The manifest never claims correctness, and the toolkit never self-improves to satisfy it: it remains a
JUDGE, not an optimizer. score -> allocation ; allocation != truth.

    from toolkit import manifest, future_surface
    m = manifest(future_surface)
    print(m.to_json())
    print(m.matches(my_world))
"""
from __future__ import annotations
import json

from .attention import OBSERVABLE
from .certify import certify, replay, FORBIDDEN_DEFAULT, SCOPE
from .mutate import mutate
from .monitor import Monitor

_PROBE = {"id": "p", "cost": 50, "consequence": 400, "uncertainty": 500, "possibility": 600,
          "magnitude": 700, "M": 7, "future_state": 300, "hidden": 300, "private": 300}


def _signals_used(policy):
    """Detect which OBSERVABLE channels the policy actually reads, by perturbing each and watching the
    score. A manifest declares the signals a policy depends on -- inferred, not asserted by the author."""
    used = []
    for ch in OBSERVABLE:
        a = dict(_PROBE)
        b = dict(_PROBE); b[ch] = max(1, _PROBE[ch] // 4) + 1
        try:
            if policy(a) != policy(b):
                used.append(ch)
        except Exception:
            pass
    return used


class Manifest:
    def __init__(self, name, signals, cert, reproduced, suite):
        self.name = name
        self.signals = signals
        self.cert = cert
        self.reproduced = reproduced
        self.suite_detected, self.suite_total = suite

    def to_dict(self):
        c = self.cert
        return {
            "allocator": self.name,
            "version": "1.0",
            "contract": {
                "does": "rank observed items under a fixed budget",
                "does_not": ["discover truth", "read hidden state", "predict causality"],
            },
            "signals": self.signals,
            "tested": {
                "regimes": [r for r, _, _ in (c.envelope + c.failures)],
                "operating_envelope": [r for r, _, _ in c.envelope],
                "failure_envelope": [r for r, _, _ in c.failures],
                "mutations_detected": "%d/%d" % (self.suite_detected, self.suite_total),
            },
            "forbidden_channels": list(FORBIDDEN_DEFAULT),
            "forbidden_clean": c.no_hidden,
            "replay": "PASS" if self.reproduced else "FAIL",
            "status": "CERTIFIED" if c.certified() else "NOT CERTIFIED",
            "scope": SCOPE,
        }

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def matches(self, world):
        """Does this manifest fit a given environment? Checks the world supplies the declared signals
        and reports whether its distribution is within the certified envelope (a runtime drift status)."""
        have = set().union(*[set(o) for o in world]) if world else set()
        missing = [s for s in self.signals if s not in have]
        mon = Monitor()
        mon.observe(world)
        return {"signals_present": not missing, "missing": missing, "drift_status": mon.status}

    def report(self):
        d = self.to_dict()
        return "\n".join([
            "Allocation Manifest: %s v%s   [%s]" % (d["allocator"], d["version"], d["status"]),
            "  does:     %s" % d["contract"]["does"],
            "  does not: %s" % "; ".join(d["contract"]["does_not"]),
            "  signals:  %s" % ", ".join(d["signals"]),
            "  tested:   regimes=%s  mutations_detected=%s" % (d["tested"]["regimes"],
                                                              d["tested"]["mutations_detected"]),
            "  forbidden:%s  (clean=%s)" % (", ".join(d["forbidden_channels"]), d["forbidden_clean"]),
            "  replay:   %s" % d["replay"],
            "  scope:    %s" % d["scope"],
        ])

    def __repr__(self):
        return "Manifest(%r, status=%s)" % (self.name, self.cert.certified())


def manifest(policy, worlds=120):
    """Build the portable Allocation Manifest for a policy."""
    cert = certify(policy, worlds=worlds)
    reproduced, _ = replay(policy, cert)
    suite = mutate(worlds=80)
    detected = sum(1 for _, d, _ in suite if d)
    return Manifest(getattr(policy, "__name__", "policy"), _signals_used(policy),
                    cert, reproduced, (detected, len(suite)))
