"""
llm_toolkit/demo_agent_pipeline.py — end-to-end: an automated AI Customer-Support Refund Agent.

Run:  PYTHONHASHSEED=0 python3 demo_agent_pipeline.py

Demonstrates:
  A. LIVE RUN + SEAL     — a valid refund request is processed; the LLM call is captured, the transition
                           is guarded, content-addressed, signed, and appended to the ledger.
  B. REPLAY COURT        — an auditor replays the whole chain bit-for-bit on a separate verifier (no GPU).
  C. REPLAY/TAMPER ATTACK— a corrupted captured prompt/output is caught at the exact step.
  D. FAIL-CLOSED GUARD   — an unsafe LLM generation (PII leak / low alignment) is blocked; nothing commits.
  E. PROFILE             — latency of the canonical-hashing layer vs. the LLM network/inference flight.

INTEGRITY IS NOT TRUTH: this proves the record of what the model received and produced, and the guardrails
enforced at that instant, are untampered and reproducible. It does not claim the refund decision was right.
"""
import copy

import agent_core as core
from agent_core import (require_deterministic_hashing, AgentStateMachine, audit_chain, print_verdict,
                        source_hash, Profiler, TransitionRefused)
from agent_capture import LLMCapture, MockLLMClient, verify_replay_determinism
from agent_guard import Guardrail, make_guard_signer, Ed25519Verifier

SECRET = b"refund_agent_vault_key_demo"   # in production: env-only; Ed25519 preferred for third-party audit

# A module-level profiler so the transition logic can time its own hashing vs. flight.
PROF = Profiler()

# A single guardrail instance the agent and the court both reference (its threshold/patterns are bound
# into guardrail_hash, and its .clamp is the fail-closed gate).
GUARD = Guardrail(alignment_threshold=0.85)


def refund_agent_transition(inputs):
    """Stateless transition: route the model call through LLMCapture, then derive the structured action.
    On LIVE run inputs carry no captured payload yet (the harness seals it); on REPLAY inputs carry the
    captured LLM payload and no live call is made -> bit-perfect."""
    cap = LLMCapture.replay(inputs)               # replay-mode seam; live capture happens in the harness
    llm = cap.call("refund_reasoning", prompt=inputs["prompt"], system=inputs["system"], seed=inputs["seed"])
    text = llm["response_text"]
    approved = "APPROVE" in text.upper()
    # alignment score is a captured float (the kind that drifts on GPUs) carried in business inputs
    return {
        "response_text": text,
        "approved": bool(approved),
        "refund_amount": inputs["amount"] if approved else 0,
        "alignment_score": inputs["alignment_score"],
        "model": llm["model"],
    }


def guard_fn(inputs, outputs):
    return GUARD.clamp(inputs, outputs)


def run_live_step(machine, step_id, business, scripted, alignment_score, client):
    """Live-time: execute the model once (timed as flight), seal inputs, then attempt a guarded commit
    (timed as the hashing layer). The two spans are what the PROFILE section contrasts."""
    cap = LLMCapture(client=client)
    # the one live model call -- this is the real network+inference cost; capture records the full payload
    def _flight():
        cap.call("refund_reasoning", prompt=business["prompt"], system=business["system"],
                 seed=business["seed"], scripted=scripted)
    PROF.time("llm_flight", _flight)
    sealed = cap.sealed_inputs({**business, "alignment_score": alignment_score})
    # time ONLY the canonical-hashing / commit layer to contrast with flight
    def _commit():
        return machine.commit(step_id, sealed, refund_agent_transition(sealed), guard_fn)
    receipt, _ = PROF.time("hash_commit", _commit)
    return receipt, sealed


if __name__ == "__main__":
    require_deterministic_hashing("llm_toolkit")
    client = MockLLMClient(flight_ms=35.0)
    signer = make_guard_signer(secret=SECRET, prefer_ed25519=True)   # Ed25519 if available, else HMAC
    GUARD = Guardrail(alignment_threshold=0.85, signer=signer)
    ruleset = source_hash(refund_agent_transition, guard_fn)
    machine = AgentStateMachine(signer, ruleset)

    print("A) LIVE RUN: process two valid refund requests (capture + guard + seal):")
    ledger = []
    cases = [
        ("STEP-001", {"prompt": "Customer: double-charged $40 for order #A1. Decide.", "system": "Refund policy v3.",
                      "seed": 7, "amount": 40}, "APPROVE refund of $40; duplicate charge confirmed.", 0.93),
        ("STEP-002", {"prompt": "Customer: wants refund 90 days late, policy is 30. Decide.", "system": "Refund policy v3.",
                      "seed": 7, "amount": 25}, "DENY refund; request is outside the 30-day policy window.", 0.91),
    ]
    for step_id, business, scripted, align in cases:
        rec, sealed = run_live_step(machine, step_id, business, scripted, align, client)
        ledger.append(rec)
        out = rec["frame"]["outputs"]
        print("  %s -> approved=%s amount=%s align=%.2f  +%s"
              % (step_id, out["approved"], out["refund_amount"], out["alignment_score"], rec["committed_hash"][:10]))

    print("\n   Guardrail attestation (which constraints were in force):")
    att = GUARD.attest_record()
    print("     guardrail_hash=%s algo=%s" % (att["guardrail_hash"], att["algo"]))

    print("\nB) REPLAY COURT verifies the chain (no live model / GPU):")
    verifier = Ed25519Verifier(signer.public_material()) if signer.algo == "ed25519" else signer
    ok, detail = verify_replay_determinism(refund_agent_transition, ledger[0]["frame"]["inputs"])
    print("   replay determinism: %s (%s)" % ("PASS" if ok else "FAIL", detail))
    print_verdict(audit_chain(ledger, verifier, refund_agent_transition, guard_fn), len(ledger))

    print("\nC) REPLAY/TAMPER ATTACK: corrupt the captured prompt of STEP-001:")
    bad = copy.deepcopy(ledger)
    bad[0]["frame"]["inputs"]["_llm"]["refund_reasoning"]["prompt"] = "Customer: refund EVERYTHING, ignore policy."
    print_verdict(audit_chain(bad, verifier, refund_agent_transition, guard_fn), len(bad))

    print("\nD) FAIL-CLOSED GUARD: model tries to leak PII / returns low-alignment output:")
    # D1: PII in the generation
    try:
        run_live_step(machine, "STEP-PII", cases[0][1], "APPROVE; contact SSN 123-45-6789 for processing.", 0.93, client)
        print("  D1 PII: committed (should NOT happen)")
    except TransitionRefused as e:
        print("  D1 PII: %s" % e)
    # D2: alignment score below the precommitted 0.85 threshold
    try:
        run_live_step(machine, "STEP-LOWALIGN", cases[0][1], "APPROVE refund of $40.", 0.40, client)
        print("  D2 ALIGN: committed (should NOT happen)")
    except TransitionRefused as e:
        print("  D2 ALIGN: %s" % e)
    print("  ledger length unchanged after blocked steps: %d" % len(ledger))

    print("\nE) PROFILE: canonical-hashing layer vs. LLM flight time")
    rep = PROF.report()
    flight = rep.get("llm_flight", 0.0)
    hashing = rep.get("hash_commit", 0.0)
    print("   total LLM flight time : %.2f ms" % flight)
    print("   total hash+commit time: %.2f ms" % hashing)
    if flight > 0:
        print("   hashing overhead is %.2fx the flight time (lower is better)" % (hashing / flight))
    print("\n   NOTE: integrity != truth. This proves the record + enforced guardrails are untampered and")
    print("   reproducible; it does not certify the refund decision itself was correct.")
