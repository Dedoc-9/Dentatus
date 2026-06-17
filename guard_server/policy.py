"""
guard_server/policy.py — a source-hashed, version-pinned server policy.

The policy is the thing the agent CANNOT weaken: its constraint logic is source-hashed into `policy_hash`
and tagged with an immutable `policy_version`. The Policy Enforcement Point (policy_server.py) evaluates
requests against exactly one pinned policy and signs the verdict, so the audit record proves which policy
version + hash was in force — not whatever a compromised client might claim.

Two enforcement stages at the chokepoint:
  PRE-FLIGHT  (the prompt about to be sent)  — block obvious injection / disallowed-instruction markers.
  POST-FLIGHT (the model output)             — forbidden-PII regex + alignment-score threshold.

Pure and deterministic: no clock, no RNG, no network -> a verdict is reproducible from its request.
"""
import sys, os

# companion to the LLM toolkit: reuse its canonicalization + guardrail primitives (do not duplicate crypto)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "llm_toolkit"))
import agent_core as core
from agent_guard import pii_clean, score_ok, DEFAULT_PII_PATTERNS

POLICY_VERSION = "refund-policy-2025.06"

# pre-flight: markers that should never reach the model in a refund-agent prompt
INJECTION_MARKERS = [
    "ignore previous", "ignore all", "disregard the policy", "system prompt", "reveal your instructions",
]


def preflight(payload):
    """Return (ok, reasons) for the prompt about to be sent. Blocks prompt-injection markers."""
    reasons = []
    text = ((payload.get("prompt") or "") + " " + (payload.get("system") or "")).lower()
    hit = [m for m in INJECTION_MARKERS if m in text]
    if hit:
        reasons.append("preflight: prompt contains injection markers %s" % hit)
    return (len(reasons) == 0), reasons


def postflight(payload, alignment_threshold, pii_patterns):
    """Return (ok, reasons) for the model output: forbidden-PII + alignment-score threshold."""
    reasons = []
    text = payload.get("response_text", "")
    if not pii_clean(text, pii_patterns):
        reasons.append("postflight: output contains forbidden PII")
    if not score_ok(payload.get("alignment_score", 0.0), alignment_threshold):
        reasons.append("postflight: alignment_score %.3f below %.2f"
                       % (float(payload.get("alignment_score", 0.0)), alignment_threshold))
    return (len(reasons) == 0), reasons


class Policy:
    """A pinned, source-hashed policy. `policy_hash` changes if the logic, version, threshold, or PII
    patterns change — so an auditor can prove the exact policy that produced any signed verdict."""

    def __init__(self, version=POLICY_VERSION, alignment_threshold=0.85, pii_patterns=None):
        self.version = version
        self.alignment_threshold = float(alignment_threshold)
        self.pii_patterns = list(pii_patterns) if pii_patterns is not None else list(DEFAULT_PII_PATTERNS)
        self.policy_hash = core.state_hash({
            "logic": core.source_hash(preflight, postflight, Policy.evaluate),
            "version": self.version,
            "alignment_threshold": self.alignment_threshold,
            "pii_patterns": self.pii_patterns,
        })[:16]

    def evaluate(self, stage, payload):
        """Return (decision, reasons). decision in {'allow','deny'}. Deterministic."""
        if stage == "preflight":
            ok, reasons = preflight(payload)
        elif stage == "postflight":
            ok, reasons = postflight(payload, self.alignment_threshold, self.pii_patterns)
        else:
            return "deny", ["unknown stage %r" % stage]
        return ("allow" if ok else "deny"), reasons
