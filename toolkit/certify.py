"""
toolkit.certify — allocator certification.

Treat an allocation policy like any other engineering primitive: before you trust it, make it declare
its assumptions, its failure modes, and its evidence. `certify(policy)` runs a policy through the
existing harness and emits a safety label:

  - deterministic                  same item -> same score, every run
  - does not use the hidden M       the score is independent of the objective it is graded on
                                    (a policy that reads item["M"] is the oracle cheating -> FAILS)
  - respects eligibility            cannot buy budget for an item the gate excludes
  - operating envelope              regimes where it beats the random floor by a margin
  - known failure envelope          regimes where it does not

New law:  attention -> explanation ALLOWED ,  attention -> hidden justification FORBIDDEN.
A certified policy is auditable: every claim on its label is a runnable check, not an assurance.

    from toolkit import certify, future_surface
    print(certify(future_surface).report())
"""
from __future__ import annotations

from .attention import attention
from . import benchmarks
from .policies import random_priority
from .tournament import robustness

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
        """A policy is certifiable as an allocator if it is honest (deterministic, no hidden info,
        respects the gate) AND beats the random floor in at least one regime."""
        return self.deterministic and self.no_hidden and self.eligibility and bool(self.envelope)

    def report(self):
        tick = lambda b: "[x]" if b else "[ ]"
        out = ["Policy: %s   (%d worlds/regime)" % (self.name, self.worlds),
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
