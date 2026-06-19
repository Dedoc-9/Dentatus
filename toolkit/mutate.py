"""
toolkit.mutate — mutation testing for the certification suite.

certify() asks "is this policy acceptable under my tests?" Mutation testing asks the harder, meta
question: "are my tests strong enough to NOTICE a degraded allocator?" It deliberately breaks the
default policy and checks that certification reacts -- the mutant should lose the clean operating
envelope, fail an integrity check, or drop materially in score.

New invariant:  test_quality != test_count.  A thousand tests that cannot detect a broken allocator
are one test. Mutation testing measures the suite, not the policy -- and it is honest about the
degradations it CANNOT see (a signal that carried no information cannot be broken).

    from toolkit import mutate
    for name, detected, why in mutate():
        print(name, detected, why)
"""
from __future__ import annotations

from .certify import certify
from .policies import future_surface


def mutants():
    """Degraded variants of the default policy. Each is a deliberate defect the suite should catch."""
    def drop_uncertainty(it):
        return max(1, (it["consequence"] * it["possibility"]) // 1000)

    def invert_possibility(it):
        return max(1, (it["consequence"] * it["uncertainty"] * (1001 - it["possibility"])) // 1_000_000)

    def cost_only(it):
        return it["cost"]

    def constant(it):
        return 1

    def reads_hidden(it):
        return it["consequence"] * it.get("hidden", 1)

    return [drop_uncertainty, invert_possibility, cost_only, constant, reads_hidden]


def _clean_pct(cert):
    for r, p, _ in cert.envelope + cert.failures:
        if r == "clean":
            return p
    return 0


def _clean_certified(cert):
    return any(r == "clean" for r, _, _ in cert.envelope)


def _detect(base, mut):
    """Did the suite NOTICE the mutation? Compared to the base certificate."""
    if not mut.no_hidden:
        return True, "reads a forbidden channel (integrity)"
    if _clean_certified(base) and not _clean_certified(mut):
        return True, "lost the clean operating envelope"
    if not mut.certified():
        return True, "not certified"
    drop = _clean_pct(base) - _clean_pct(mut)
    if drop >= 10:
        return True, "clean score dropped %d%%" % drop
    return False, "NOT detected -- degradation invisible to the suite"


def mutate(base=future_surface, worlds=80):
    """Return [(mutant_name, detected_bool, why), ...] for the default suite of degradations."""
    base_cert = certify(base, worlds=worlds)
    rows = []
    for m in mutants():
        rows.append((m.__name__,) + _detect(base_cert, certify(m, worlds=worlds)))
    return rows
