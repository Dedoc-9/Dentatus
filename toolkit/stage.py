"""
toolkit.stage — the staged-action buffer: propose-then-consent, never auto-execute.

This is the "one-click boundary" done honestly. A policy does not act on the world; it stages a
*candidate* allocation that a human (or an authority) must explicitly authorize. Two laws from the
wider project govern it:

    telemetry != control     a staged proposal is information, not an instruction
    intent    != authority   the policy's proposal is never authority; the authorization is

`stage(world, scorer)` checks the environment against the policy's manifest (`manifest.matches`) and
either STAGES an *attested*, refusable record or REFUSES with a reason (a declared signal is missing, or
the environment has drifted outside the certified envelope). The staged record cites ONLY observable
provenance (never the graded objective M) and carries a SHA-256 content digest, so the one click signs
off on a perfectly auditable, content-addressed record -- not a vibe.

Hard scope: this stages an *allocation decision* in the constructed/allocation domain. It does not
execute any real-world action, and it certifies the integrity of the record, never the correctness of
the decision (`integrity != truth`). High-stakes actuation needs a domain-validated model behind the
buffer; this provides the buffer, the audit trail, and the consent gate -- not the model.

    from toolkit import stage
    action = stage(my_world)
    print(action.report())
    if action.staged:
        committed = action.authorize(by="operator")   # the one explicit click
"""
from __future__ import annotations
import hashlib
import json

from .attention import attention
from .policies import future_surface
from .manifest import manifest as build_manifest

# The attestation boundary, carried as DATA on every record so "verified" cannot drift to "correct".
ATTESTS = (
    "manifest compatibility (matches)",
    "declared signals present",
    "certification status of the policy",
    "provenance integrity (observable signals only)",
    "content identity (sha256 of the record)",
)
DOES_NOT_ATTEST = (
    "correctness of the allocation",
    "correctness of the objective M",
    "correctness of the environment model",
    "correctness of downstream consequences",
)


def _digest(record):
    """Content address of a staged record: SHA-256 over canonical bytes (sorted keys). Deterministic."""
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class StagedAction:
    STAGED, REFUSED = "STAGED", "REFUSED"

    def __init__(self, status, reason, record):
        self.status = status
        self.reason = reason
        self.record = record
        self.digest = _digest(record)
        self.staged = status == self.STAGED

    def authorize(self, by="human"):
        """The one explicit click. Returns a committed, content-addressed record. Refuses to authorize a
        REFUSED proposal -- a high enough score never buys authority an ineligible environment denies."""
        if not self.staged:
            return {"authorized": False, "reason": self.reason, "digest": self.digest}
        return {"authorized": True, "authorized_by": by, "consent": "explicit",
                "digest": self.digest, "record": self.record,
                "law": "intent != authority -- this click, not the proposal, is the authority"}

    def report(self):
        r = self.record
        out = ["Staged action: %s   [%s]" % (r["policy"], self.status),
               "  env fit:   signals_present=%s  drift=%s%s"
               % (r["env_fit"]["signals_present"], r["env_fit"]["drift_status"],
                  "" if not r["env_fit"]["missing"] else "  missing=%s" % r["env_fit"]["missing"]),
               "  decision:  %s (%s)" % (self.status, self.reason),
               "  attests:   " + "; ".join(r["attestation"]["checks"]),
               "  NOT attested (integrity != truth): " + "; ".join(r["attestation"]["never_certifies"])]
        if self.staged:
            p = r["proposal"]
            out += ["  proposal:  fund %d/%d candidates, spend %d/%d"
                    % (p["funded_count"], p["candidates"], p["spent"], p["budget"]),
                    "  top item:  %s" % p["top_funded"],
                    "  bounds:    %s" % r["bounds"]["scope"],
                    "  digest:    %s" % self.digest[:16] + "  (sha256 of the record)",
                    "  >> AWAITING ONE AUTHORIZATION (intent != authority); call authorize() to commit.",
                    "     (this authorizes a content-addressed record, not a guarantee of correctness)"]
        else:
            out += ["  digest:    %s" % self.digest[:16],
                    "  >> NOT STAGED -- the environment is outside this policy's certified evidence."]
        return "\n".join(out)

    def __repr__(self):
        return "StagedAction(%s, digest=%s)" % (self.status, self.digest[:12])


def stage(world, scorer=future_surface, manifest=None, budget=1000, worlds=60):
    """Stage a candidate allocation for `world` under `scorer`, gated by the policy's manifest. Returns a
    StagedAction (STAGED with a refusable record, or REFUSED with a reason). Never executes anything."""
    man = manifest or build_manifest(scorer, worlds=worlds)
    fit = man.matches(world)
    env_fit = {"signals_present": fit["signals_present"], "missing": fit["missing"],
               "drift_status": fit["drift_status"]}
    md = man.to_dict()
    base = {"policy": md["allocator"], "manifest_status": md["status"], "env_fit": env_fit,
            "bounds": {"scope": md["scope"]},
            "attestation": {"checks": list(ATTESTS), "never_certifies": list(DOES_NOT_ATTEST)}}

    if not fit["signals_present"]:
        return StagedAction(StagedAction.REFUSED,
                            "missing declared signal(s): %s" % ", ".join(fit["missing"]), base)
    if fit["drift_status"] == "QUARANTINED":
        return StagedAction(StagedAction.REFUSED,
                            "environment drifted outside the certified envelope (quarantined)", base)

    budget_obj = attention.observe(world, scorer).allocate(budget)
    top = sorted(budget_obj.chosen)[0] if budget_obj.chosen else None
    prov = budget_obj.reason(top) if top else {}
    proposal = {
        "funded_count": len(budget_obj.chosen), "candidates": len(world),
        "budget": budget, "spent": budget_obj.spent,
        "top_funded": ("%s rank #%s/%s signals=%s"
                       % (top, prov.get("rank"), prov.get("of_eligible"), prov.get("signals"))
                       if top else "(none funded)"),
    }
    rec = dict(base); rec["proposal"] = proposal
    return StagedAction(StagedAction.STAGED, "admissible: signals present, within envelope", rec)
