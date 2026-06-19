"""
toolkit.evaluate — external allocator onboarding.

The milestone: a stranger brings their own allocation policy, and the toolkit tells them -- without
the author's help -- what it assumes, where it fails, whether it is cheating, and whether its evidence
reproduces. `evaluate(policy)` composes the whole harness into one report.

It is a JUDGE, never an optimizer. It never modifies the policy or proposes a better one; crossing
that line would turn an attention engine into a truth engine. The toolkit reports where a system should
be trusted; it does not decide what is true.

    from toolkit import evaluate, future_surface
    print(evaluate(future_surface).report())
"""
from __future__ import annotations

from .certify import certify, replay
from .mutate import mutate


class AllocatorReport:
    def __init__(self, name, certificate, reproduced, suite_strength):
        self.name = name
        self.certificate = certificate
        self.reproduced = reproduced
        self.suite_detected, self.suite_total = suite_strength

    def to_dict(self):
        c = self.certificate
        return {
            "allocator": self.name,
            "verdict": "CERTIFIED" if c.certified() else "NOT CERTIFIED",
            "operating_envelope": [r for r, _, _ in c.envelope],
            "failure_envelope": [r for r, _, _ in c.failures],
            "forbidden_access": "PASS" if c.no_hidden else "FAIL",
            "forbidden_channels_read": c.channels_used(),
            "deterministic": c.deterministic,
            "respects_eligibility": c.eligibility,
            "replay": "PASS" if self.reproduced else "FAIL",
            "suite_strength": "%d/%d mutations detected" % (self.suite_detected, self.suite_total),
            "certificate": c.to_dict(),
            "note": "judge, not optimizer: the toolkit reports trust boundaries; it does not improve policies",
        }

    def report(self):
        c = self.certificate
        out = ["Allocator Report: %s" % self.name,
               "  Verdict:            %s" % ("CERTIFIED" if c.certified() else "NOT CERTIFIED"),
               "  Operating envelope: %s" % (", ".join(r for r, _, _ in c.envelope) or "(none)"),
               "  Failure envelope:   %s" % (", ".join(r for r, _, _ in c.failures) or "(none)"),
               "  Forbidden access:   %s%s" % ("PASS" if c.no_hidden else "FAIL",
                                               "" if c.no_hidden else " (reads: %s)" % ", ".join(c.channels_used())),
               "  Deterministic:      %s" % ("PASS" if c.deterministic else "FAIL"),
               "  Respects eligibility:%s" % (" PASS" if c.eligibility else " FAIL"),
               "  Replay:             %s" % ("PASS" if self.reproduced else "FAIL"),
               "  Suite strength:     %d/%d mutations detected (test_quality != test_count)"
               % (self.suite_detected, self.suite_total),
               "  Scope:              certified under tested regimes; never a claim of correctness"]
        return "\n".join(out)

    def __repr__(self):
        return "AllocatorReport(%r, verdict=%s)" % (self.name, self.certificate.certified())


def evaluate(policy, worlds=120):
    """Onboard an external allocator: certify it, check evidence reproduces, and report suite strength.
    Pure judgement -- the policy is never modified."""
    cert = certify(policy, worlds=worlds)
    reproduced, _ = replay(policy, cert)
    suite = mutate(worlds=80)
    detected = sum(1 for _, d, _ in suite if d)
    return AllocatorReport(getattr(policy, "__name__", "policy"), cert, reproduced, (detected, len(suite)))
