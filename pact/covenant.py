"""
pact/covenant.py — multi-agent cross-attestation covenant (forensic dispute resolution, no blockchain).

When Agent A hands a state to Agent B, B does not just trust it: B verifies A's signature against a PINNED
peer registry, then signs a CROSS-ATTESTATION that cryptographically binds B's new state hash to A's prior
committed hash. Chaining these across agents yields a multi-party trail where any later injection or rule
breach is attributable to the exact agent + step.

THE EXACT GATE (fail-closed): B accepts A's payload only if (1) A is in the pinned registry, (2) A's
signature over its receipt verifies under A's pinned public key, and (3) the incoming state satisfies B's
own precommitted invariant. Then B emits a verdict binding `{a_id, a_prev_hash} -> {b_id, b_state_hash}`,
signed by B.

THE OBSERVABLE (captured, never gated): inter-agent latency, message arrival order, and per-model
confidence scores are captured at the boundary as soft metrics.

HONEST BOUND (bounded on purpose): this gives non-repudiation **under the pinned-key trust assumption** and
forensic attribution — proving who signed what, when, and what state they claimed. It does NOT force a peer
to be honest, and there is NO automatic broadcast or distributed consensus: a breach is self-evident to
anyone who verifies with the pinned public keys, not "to the whole network" by magic. Not a blockchain.
Integrity != truth.

Stdlib + optional cryptography (Ed25519) via the frozen workbench; imports chronicle/llm_toolkit read-only.
"""
import os
import sys

_WB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
sys.path.insert(0, os.path.join(_WB, "llm_toolkit"))
import core
from agent_guard import Ed25519Signer, Ed25519Verifier, ed25519_available   # asymmetric peer keys


class CovenantBreach(Exception):
    pass


def state_receipt(agent_id, state, signer, prev_hash=None):
    """An agent's signed claim about a state. `state_hash` content-addresses the state; the signature
    attests it under the agent's key."""
    core_obj = {"agent": agent_id, "state": state, "prev": prev_hash or core.GENESIS}
    sh = core.state_hash(core_obj)
    return {"agent": agent_id, "state": state, "prev": core_obj["prev"], "state_hash": sh,
            "signature": signer.sign(sh.encode())}


def verify_receipt(receipt, trusted_registry):
    """Return (ok, reason): the receipt's signer is pinned AND its signature verifies the recomputed hash."""
    verifier = trusted_registry.get(receipt["agent"])
    if verifier is None:
        return False, "unknown agent %r (not in pinned registry)" % receipt["agent"]
    sh = core.state_hash({"agent": receipt["agent"], "state": receipt["state"], "prev": receipt["prev"]})
    if sh != receipt["state_hash"]:
        return False, "state_hash mismatch (tampered state)"
    if not verifier.verify(sh.encode(), receipt["signature"]):
        return False, "signature invalid (forged / wrong key)"
    return True, "authentic"


def cross_attest(prior_receipt, b_id, b_new_state, b_signer, b_invariant, trusted_registry):
    """Agent B ingests A's receipt and emits a cross-attestation binding B's new state to A's prior hash.
    Fail-closed: raises CovenantBreach if A is untrusted/forged or the incoming state breaches B's rule."""
    ok, why = verify_receipt(prior_receipt, trusted_registry)
    if not ok:
        raise CovenantBreach("rejected upstream %s: %s" % (prior_receipt["agent"], why))
    if not b_invariant(prior_receipt["state"], b_new_state):
        raise CovenantBreach("incoming state violates %s's precommitted invariant" % b_id)
    b_receipt = state_receipt(b_id, b_new_state, b_signer, prev_hash=prior_receipt["state_hash"])
    vcore = {"from": prior_receipt["agent"], "from_hash": prior_receipt["state_hash"],
             "to": b_id, "to_hash": b_receipt["state_hash"]}
    verdict_sig = b_signer.sign(core.canonical_bytes(vcore))
    return {"verdict": vcore, "verdict_sig": verdict_sig, "receipt": b_receipt}


def audit_covenant(chain, trusted_registry, invariants):
    """Replay a multi-agent covenant chain. Each link must: have an authentic receipt, bind to the prior
    agent's hash, carry a valid verdict signature, and satisfy the receiving agent's invariant. Returns
    (ok, fault) where fault names the EXACT agent/link that deviated, or None."""
    prev = None
    for i, link in enumerate(chain):
        r = link["receipt"]
        ok, why = verify_receipt(r, trusted_registry)
        if not ok:
            return False, {"link": i, "agent": r["agent"], "reason": why}
        if prev is not None:
            v = link["verdict"]
            if v["from_hash"] != prev["state_hash"] or v["to_hash"] != r["state_hash"]:
                return False, {"link": i, "agent": r["agent"], "reason": "covenant binding broken"}
            vr = trusted_registry.get(v["to"])
            if not vr.verify(core.canonical_bytes(v), link["verdict_sig"]):
                return False, {"link": i, "agent": r["agent"], "reason": "verdict signature invalid"}
            inv = invariants.get(r["agent"])
            if inv is not None and not inv(prev["state"], r["state"]):
                return False, {"link": i, "agent": r["agent"], "reason": "invariant breached on replay"}
        prev = r
    return True, None
