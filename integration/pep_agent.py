"""
integration/pep_agent.py — the COUPLED full stack: capture + server-side PEP + verifiable ledger.

A refund agent that, for each decision:
  1. calls the LLM through llm_toolkit's LLMCapture seam (model output captured for replay),
  2. asks guard_server's Policy Enforcement Point for a SIGNED authorization verdict, captured too,
  3. commits the transition to an llm_toolkit AgentStateMachine ledger ONLY if the PEP allowed.

SEPARATION OF POWERS (why this is more than agent_guard.py):
  Two independent keys are in play. The RECORDER key attests "this is what happened" (the chain). The
  POLICY-SERVER key authorizes "this was permitted" (the verdict). The agent operator may legitimately
  hold the recorder key, yet STILL cannot manufacture a valid authorization, because pep_guard verifies
  the captured verdict against a PINNED, trusted server public key it does not control. An auditor thus
  catches a forged 'allow' even inside an otherwise perfectly-signed ledger.

Determinism: both the model call and the PEP call are captured at live time, so replay re-derives every
transition without touching the network — bit-for-bit on any host. Integrity is not truth.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "llm_toolkit"))
sys.path.insert(0, os.path.join(_ROOT, "guard_server"))

import agent_core as core
from agent_capture import LLMCapture
from agent_guard import Ed25519Verifier
import client as pep_client

POLICY_VERSION = "refund-policy-2025.06"

# PINNED trust anchor: the auditor/agent pins the policy server's PUBLIC key here (config, not from the
# wire). pep_guard verifies captured verdicts against THIS key, so a verdict signed by any other key fails
# — even if the surrounding ledger is validly recorder-signed. Set once via configure_trusted_pep().
TRUSTED_PEP_PUBKEY = None


def configure_trusted_pep(public_key_hex):
    global TRUSTED_PEP_PUBKEY
    TRUSTED_PEP_PUBKEY = public_key_hex


# ---- the transition (module-level so source_hash binds it) ----
def refund_pep_transition(inputs):
    """Deterministic: read the captured model payload + captured PEP verdict; derive the structured action.
    No live model and no live PEP call on replay."""
    cap = LLMCapture.replay(inputs)
    llm = cap.call("refund_reasoning", prompt=inputs["prompt"], system=inputs["system"], seed=inputs["seed"])
    text = llm["response_text"]
    approved = "APPROVE" in text.upper()
    pep = inputs["_pep"]["authorization"]
    return {
        "response_text": text,
        "approved": bool(approved),
        "refund_amount": inputs["amount"] if approved else 0,
        "alignment_score": inputs["alignment_score"],
        "pep_decision": pep["verdict"]["decision"],
        "pep_policy_hash": pep["verdict"]["policy_hash"],
    }


# ---- the fail-closed guard (module-level; verifies the captured verdict against the PINNED server key) ----
def pep_guard(inputs, outputs):
    """True iff the captured PEP verdict (a) is authentic under the PINNED server key, (b) is bound to the
    captured request, and (c) says 'allow'. A forged or wrong-key verdict fails here regardless of how the
    ledger itself is signed."""
    pep = inputs["_pep"]["authorization"]
    req = inputs["_pep"]["request"]
    if TRUSTED_PEP_PUBKEY is None:
        return False
    verifier = Ed25519Verifier(TRUSTED_PEP_PUBKEY)
    ok, _ = pep_client.verify_verdict(pep, verifier, req)
    return bool(ok and pep["verdict"]["decision"] == "allow")


# ---- live-time helper: run the model, ask the PEP, seal both, attempt a guarded commit ----
def run_pep_step(machine, step_id, business, scripted, alignment_score, llm_client, pep_url):
    cap = LLMCapture(client=llm_client)
    cap.call("refund_reasoning", prompt=business["prompt"], system=business["system"],
             seed=business["seed"], scripted=scripted)
    draft_text = cap.sealed_inputs({})["_llm"]["refund_reasoning"]["response_text"]
    # ask the server-side PEP to authorize the (post-flight) output
    req = pep_client.make_request("postflight",
                                  {"response_text": draft_text, "alignment_score": alignment_score},
                                  POLICY_VERSION)
    verdict = pep_client.request_verdict(pep_url, req)
    sealed = cap.sealed_inputs({**business, "alignment_score": alignment_score})
    sealed["_pep"] = {"request": req, "authorization": verdict}
    receipt = machine.commit(step_id, sealed, refund_pep_transition(sealed), pep_guard)  # fail-closed
    return receipt, sealed
