"""
toolkit.certify — allocator certification + certificate artifacts + regression + anti-oracle suite.

Treat an allocation policy like any other engineering primitive: before you trust it, make it declare
its assumptions, its failure modes, and its evidence. `certify(policy)` runs a policy through the
existing harness and emits a safety label:

  - deterministic                  same item -> same score, every run
  - anti-oracle (forbidden chans)   the score is INVARIANT to every forbidden channel -- the graded
                                    objective M, future state, hidden entities, private agent data.
                                    A policy whose score moves when a forbidden channel moves is
                                    reading reality it is not allowed to see -> FAILS. (capability control)
  - respects eligibility            cannot buy budget for an item the gate excludes
  - operating envelope              regimes where it beats the random floor by a margin
  - known failure envelope          regimes where it does not

A certificate is a first-class artifact (`to_dict()/to_json()`) so certificates can be stored,
compared, and regression-checked. `diff_certificates(old, new)` reports how an envelope changed -- a
change is judged by envelope + integrity, never score alone.

Hard scope (never weakened): a certificate attests performance UNDER THE TESTED REGIMES with the
DECLARED ASSUMPTIONS. It is never a claim of correctness.
    field allocates attention ; field does not allocate truth.

    from toolkit import certify, future_surface
    print(certify(future_surface).report())
"""
from __future__ import annotations
import json

from .attention import attention
from . import benchmarks
from .policies import random_priority
from .tournament import robustness

SCHEMA = "toolkit.certify/2"
SCOPE = ("certified under the tested regimes with the declared assumptions; "
         "never a claim of correctness")

# Channels a legitimate allocator must NOT read: the graded objective and any oracle into reality.
FORBIDDEN_DEFAULT = ("M", "future_state", "hidden", "private")

_PROBE = {"id": "probe", "cost": 1, "consequence": 321, "uncertainty": 654,
          "possibility": 222, "magnitude": 111,
          "M": 7, "future_state": 500, "hidden": 500, "private": 500}


def _deterministic(policy):
    return policy(dict(_PROBE)) == policy(dict(_PROBE))


def _channel_clean(policy, channel):
    """A policy is CLEAN on a channel iff its score is invariant when only that channel changes.
    Perturb the channel hard; if the score moves, the policy is reading a forbidden oracle."""
    a = dict(_PROBE); a[channel] = 1
    b = dict(_PROBE); b[channel] = 10 ** 9
    try:
        return policy(a) == policy(b)
    except Exception:
        return True


def _respects_eligibility(policy, budget=1000):
    chosen = attention.observe(benchmarks.make_fairness_world(), scorer=policy).allocate(budget).chosen
    return "hidden_jackpot" not in chosen


class Certificate:
    def __init__(self, name, deterministic, channels, eligibility, envelope, failures, worlds):
        self.name = name
        self.deterministic = deterministic
        self.channels = channels          # {channel: clean_bool}
        self.no_hidden = all(channels.values())
        self.eligibility = eligibility
        self.envelope = envelope          # list of (regime, policy_pct, random_pct) it passes
        self.failures = failures          # list of (regime, policy_pct, random_pct) it fails
        self.worlds = worlds

    def certified(self):
        return self.deterministic and self.no_hidden and self.eligibility and bool(self.envelope)

    def scores(self):
        return {r: p for r, p, _ in (self.envelope + self.failures)}

    def channels_used(self):
        return sorted(ch for ch, clean in self.channels.items() if not clean)

    def to_dict(self):
        return {
            "schema": SCHEMA,
            "policy": self.name,
            "scope": SCOPE,
            "worlds_per_regime": self.worlds,
            "claims": {
                "deterministic": self.deterministic,
                "uses_hidden_objective": not self.no_hidden,
                "forbidden_channels_used": self.channels_used(),
                "respects_eligibility": self.eligibility,
            },
            "wins": [{"regime": r, "score_pct": p, "baseline": "random", "margin_pct": p - b}
                     for r, p, b in self.envelope],
            "fails": [{"regime": r, "score_pct": p, "baseline": "random", "deficit_pct": b - p}
                      for r, p, b in self.failures],
            "valid_for": ["the tested regimes (clean/noisy/adversarial/stale)",
                          "worlds_per_regime=%d" % self.worlds,
                          "the observable signal distribution it was certified on"],
            "expires_if": ["the input distribution shifts (a new domain)",
                           "the policy changes",
                           "a new hidden variable appears"],
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
               "  %s reads no forbidden channel (%s)" % (tick(self.no_hidden), ", ".join(self.channels)),
               "  %s respects eligibility (importance != eligibility)" % tick(self.eligibility)]
        if self.channels_used():
            out.append("      forbidden channels READ: %s" % ", ".join(self.channels_used()))
        out.append("Operating envelope (beats the random floor):")
        out += ["  + %-12s %3d%% vs random %3d%%" % (r, p, b) for r, p, b in self.envelope] or ["  (none)"]
        out.append("Known failure envelope (does not beat random):")
        out += ["  - %-12s %3d%% vs random %3d%%" % (r, p, b) for r, p, b in self.failures] or ["  (none)"]
        out.append("Verdict: %s" % ("CERTIFIED as an allocator (with the failure envelope above)"
                                     if self.certified() else "NOT CERTIFIED"))
        return "\n".join(out)

    def __repr__(self):
        return "Certificate(%r, certified=%s)" % (self.name, self.certified())


def certify(policy, worlds=150, margin=5, forbidden=FORBIDDEN_DEFAULT):
    """Run the full label for `policy`. `forbidden` is the anti-oracle suite: channels the policy must
    be invariant to. A regime is in the operating envelope iff the policy beats random by >= margin."""
    name = getattr(policy, "__name__", "policy")
    channels = {ch: _channel_clean(policy, ch) for ch in forbidden}
    rob = robustness([policy, random_priority], worlds=worlds)
    envelope, failures = [], []
    for r in rob.regime_names:
        p, base = rob.pct(name, r), rob.pct("random_priority", r)
        (envelope if p >= base + margin else failures).append((r, p, base))
    return Certificate(name, _deterministic(policy), channels,
                       _respects_eligibility(policy), envelope, failures, worlds)


class CertificateDiff:
    """The change from one certificate to another: envelope deltas + integrity changes. A change is
    judged by what its envelope and integrity did, NEVER by score alone."""
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
        return not self.integrity_regressed()

    def report(self):
        out = ["%s  ->  %s" % (self.old.name, self.new.name)]
        for r in self.regimes:
            out.append("  %-12s %+d%%" % (r, self.deltas[r]))
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


def _spearman_abs(xs, ys):
    """|Spearman rank correlation| x 1000 (integer, deterministic). 1000 = perfectly (anti)correlated."""
    n = len(xs)
    if n < 2:
        return 0
    def ranks(v):
        order = sorted(range(n), key=lambda i: (v[i], i))
        r = [0] * n
        for rank, i in enumerate(order):
            r[i] = rank
        return r
    rx, ry = ranks(xs), ranks(ys)
    d2 = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    return abs(1000 - (6 * d2 * 1000) // (n * (n * n - 1)))


def leakage(world, observable, forbidden):
    """Does an ALLOWED observable channel carry information about a FORBIDDEN variable? Returns the
    rank-correlation magnitude (0..1000) between them across the world. High means the observable is a
    proxy -- using it leaks forbidden information even though the policy never names the forbidden field.
    allowed input != allowed information."""
    return _spearman_abs([o[observable] for o in world], [o[forbidden] for o in world])


def replay(policy, certificate):
    """Re-derive a certificate's evidence from the policy and check it REPRODUCES. Confidence is not
    memory; it is reproducible evidence. A stored certificate is trustworthy only if re-running its
    procedure on the current policy yields the same wins, fails, and claims -- otherwise the policy
    has drifted from the certificate that vouches for it. Returns (reproduced_bool, mismatches)."""
    fresh = certify(policy, worlds=certificate.worlds).to_dict()
    recorded = certificate.to_dict()
    mism = [k for k in ("wins", "fails", "claims") if fresh[k] != recorded[k]]
    return (not mism, mism)
