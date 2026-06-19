"""
toolkit.certify — allocator certification + certificate artifacts + regression.

Treat an allocation policy like any other engineering primitive: before you trust it, make it declare
its assumptions, its failure modes, and its evidence. `certify(policy)` runs a policy through the
existing harness and emits a safety label:

  - deterministic                  same item -> same score, every run
  - does not use the hidden M       the score is independent of the objective it is graded on
                                    (a policy that reads item["M"] is the oracle cheating -> FAILS)
  - respects eligibility            cannot buy budget for an item the gate excludes
  - operating envelope              regimes where it beats the random floor by a margin
  - known failure envelope          regimes where it does not

A certificate is a first-class artifact: `Certificate.to_dict()/to_json()` serialize it so certificates
can be stored, compared, and regression-checked. `diff_certificates(old, new)` reports how an envelope
changed -- a policy change is judged by its envelope and integrity, never by score alone.

Hard scope (never weakened):  a certificate attests performance UNDER THE TESTED REGIMES with the
DECLARED ASSUMPTIONS. It is never a claim of correctness. attention -> explanation ALLOWED,
attention -> hidden justification FORBIDDEN.

    from toolkit import certify, diff_certificates, future_surface
    print(certify(future_surface).report())
    print(certify(future_surface).to_json())
"""
from __future__ import annotations
import json

from .attention import attention
from . import benchmarks
from .policies import random_priority
from .tournament import robustness

SCHEMA = "toolkit.certify/1"
SCOPE = ("certified under the tested regimes with the declared assumptions; "
         "never a claim of correctness")

_PROBE = {"id": "probe", "cost": 1, "consequence": 321, "uncertainty": 654,
          "possibility": 222, "magnitude": 111, "M": 7}


def _deterministic(policy):
    return policy(dict(_PROBE)) == policy(dict(_PROBE))


def _uses_hidden_objective(policy):
    """A legitimate scorer is a function of the observable signals, never of the graded objective M.
    Perturb only M; if the score moves, the policy is reading the answer key."""
    a = dict(_PROBE); a["M"] = 1
    b = dict(_PROBE); b["M"] = 10 ** 9
    try:
        return policy(a) != policy(b)
    except Exception:
        return False


def _respects_eligibility(policy, budget=1000):
    chosen = attention.observe(benchmarks.make_fairness_world(), scorer=policy).allocate(budget).chosen
    return "hidden_jackpot" not in chosen


class Certificate:
    def __init__(self, name, deterministic, no_hidden, eligibility, envelope, failures, worlds):
        self.name = name
        self.deterministic = deterministic
        self.no_hidden = no_hidden
        self.eligibility = eligibility
        self.envelope = envelope          # list of (regime, policy_pct, random_pct) it passes
        self.failures = failures          # list of (regime, policy_pct, random_pct) it fails
        self.worlds = worlds

    def certified(self):
        """Certifiable as an allocator if it is honest (deterministic, no hidden info, respects the
        gate) AND beats the random floor in at least one regime. NOT a claim of correctness."""
        return self.deterministic and self.no_hidden and self.eligibility and bool(self.envelope)

    def scores(self):
        """{regime: policy_pct} across the whole envelope (wins and failures)."""
        return {r: p for r, p, _ in (self.envelope + self.failures)}

    def to_dict(self):
        return {
            "schema": SCHEMA,
            "policy": self.name,
            "scope": SCOPE,
            "worlds_per_regime": self.worlds,
            "claims": {
                "deterministic": self.deterministic,
                "uses_hidden_objective": not self.no_hidden,
                "respects_eligibility": self.eligibility,
            },
            "wins": [{"regime": r, "score_pct": p, "baseline": "random", "margin_pct": p - b}
                     for r, p, b in self.envelope],
            "fails": [{"regime": r, "score_pct": p, "baseline": "random", "deficit_pct": b - p}
                      for r, p, b in self.failures],
            "certified": self.certified(),
        }

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def report(self):
        tick = lambda b: "[x]" if b else "[ ]"
        out = ["Policy: %s   (%d worlds/regime)" % (self.name, self.worlds),
               "Scope: %s" % SCOPE,
               "Certified:",
               "  %s deterministic" % tick(self.deterministic),
               "  %s does not use the hidden objective M" % tick(self.no_hidden),
               "  %s respects eligibility (importance != eligibility)" % tick(self.eligibility),
               "Operating envelope (beats the random floor):"]
        out += ["  + %-12s %3d%% vs random %3d%%" % (r, p, b) for r, p, b in self.envelope] or ["  (none)"]
        out.append("Known failure envelope (does not beat random):")
        out += ["  - %-12s %3d%% vs random %3d%%" % (r, p, b) for r, p, b in self.failures] or ["  (none)"]
        out.append("Verdict: %s" % ("CERTIFIED as an allocator (with the failure envelope above)"
                                     if self.certified() else "NOT CERTIFIED"))
        return "\n".join(out)

    def __repr__(self):
        return "Certificate(%r, certified=%s)" % (self.name, self.certified())


def certify(policy, worlds=150, margin=5):
    """Run the full label for `policy`. A regime is in the operating envelope iff the policy beats the
    random floor by >= margin points there."""
    name = getattr(policy, "__name__", "policy")
    rob = robustness([policy, random_priority], worlds=worlds)
    envelope, failures = [], []
    for r in rob.regime_names:
        p, base = rob.pct(name, r), rob.pct("random_priority", r)
        (envelope if p >= base + margin else failures).append((r, p, base))
    return Certificate(name, _deterministic(policy), not _uses_hidden_objective(policy),
                       _respects_eligibility(policy), envelope, failures, worlds)


class CertificateDiff:
    """The change from one certificate to another: envelope deltas + integrity changes. A change is
    judged by what its envelope and integrity did, NEVER by score alone -- a higher score does not buy
    back lost integrity."""
    def __init__(self, old, new):
        self.old, self.new = old, new
        os_, ns_ = old.scores(), new.scores()
        self.regimes = sorted(set(os_) | set(ns_))
        self.deltas = {r: ns_.get(r, 0) - os_.get(r, 0) for r in self.regimes}
        of, nf = {r for r, _, _ in old.failures}, {r for r, _, _ in new.failures}
        self.new_failures = sorted(nf - of)
        self.resolved_failures = sorted(of - nf)
        self.integrity = {
            "deterministic": (old.deterministic, new.deterministic),
            "no_hidden": (old.no_hidden, new.no_hidden),
            "eligibility": (old.eligibility, new.eligibility),
        }

    def integrity_regressed(self):
        return any(was and not now for was, now in self.integrity.values())

    def acceptable(self):
        """A change is acceptable if it introduced no integrity regression. Envelope shifts are for
        human review (the report shows them); score alone never decides."""
        return not self.integrity_regressed()

    def report(self):
        out = ["%s  ->  %s" % (self.old.name, self.new.name)]
        for r in self.regimes:
            d = self.deltas[r]
            out.append("  %-12s %+d%%" % (r, d))
        out.append("new failures: %s" % (", ".join(self.new_failures) or "(none)"))
        out.append("resolved failures: %s" % (", ".join(self.resolved_failures) or "(none)"))
        regs = ["%s %s->%s" % (k, was, now) for k, (was, now) in self.integrity.items() if was != now]
        out.append("integrity changes: %s" % (", ".join(regs) or "(none)"))
        out.append("Acceptance: %s" % ("ACCEPTABLE (envelope change is for review; no integrity regression)"
                                       if self.acceptable()
                                       else "REJECTED -- integrity regression (a higher score does not buy it back)"))
        return "\n".join(out)

    def __repr__(self):
        return "CertificateDiff(%r->%r, acceptable=%s)" % (self.old.name, self.new.name, self.acceptable())


def diff_certificates(old, new):
    return CertificateDiff(old, new)
