# SPDX-License-Identifier: AGPL-3.0-only
"""
aegis_gate/app/policy.py — host-side AML/KYC validity predicates as EXACT GATES, plus the
chronicle-bound decision function and its precommitted invariant.

THE EXACT-GATE / OBSERVABLE SPLIT (the load-bearing idea):

  EXACT GATES are integer/boolean/string facts that fully determine approval and are folded into the
  committed hash. They are reproducible bit-for-bit: amount_cents (int), src/dst ids (str), src_verified
  (bool), dst_restricted (bool), supervisor_authorized (bool). decide() reads ONLY these.

  OBSERVABLES are model-dependent or floating values an LLM emits — the natural-language prompt, model
  seed, per-token logprobs, a parse-confidence score. They are CAPTURED into the frame (so tampering
  with them breaks the ledger) but NEVER gate the decision. A float logprob must not decide whether
  money moves; if it did, two replays could diverge and the audit would be a fiction.

So `supervisor_authorized` is a BOOLEAN gate. The cryptographic check that produces it (verifying an
Ed25519 supervisor compliance token against a pinned public key) happens upstream in run_pipeline.py;
its result enters decide() as an exact bool, and the token bytes/signature ride along as observables.
This keeps decide() pure and key-free so the replay court can re-run it anywhere.

Pinned, source-hashed policy: decide + aml_invariant are bound by chronicle.ruleset_hash, so an auditor
re-running the court proves the rules that produced a verdict are exactly the rules on record.
"""
from _workbench import captured_view
from app import bank_engine as be

# ---- pinned thresholds (compliance configuration; in a real deployment these come from signed config) ----
UNVERIFIED_SINGLE_CEILING_CENTS = 1_000_000     # $10,000.00 — an unverified account's single-transfer ceiling
RESTRICTED_ROUTING_FLAGS = ("DE777", "RU000", "KP000")   # mock high-risk routing prefixes needing sign-off


def gate_reasons(intent):
    """Pure exact-gate evaluation. `intent` carries only gate fields (no observables). Returns the list
    of AML/KYC reasons a transfer is BLOCKED; empty list == all gates pass. Deterministic."""
    reasons = []
    amt = intent["amount_cents"]
    if not isinstance(amt, int) or isinstance(amt, bool) or amt <= 0:
        reasons.append("amount is not a positive integer number of cents")
        return reasons                                   # nothing else is meaningful without a valid amount
    if not intent["src_verified"] and amt >= UNVERIFIED_SINGLE_CEILING_CENTS:
        reasons.append("KYC: unverified source over single-transfer ceiling (%d cents)" % UNVERIFIED_SINGLE_CEILING_CENTS)
    if intent["dst_restricted"] and not intent["supervisor_authorized"]:
        reasons.append("AML: restricted routing requires an Ed25519-signed supervisor authorization")
    if amt > intent["src_balance_cents"]:
        reasons.append("insufficient funds for requested amount")
    return reasons


def is_restricted(routing):
    return routing in RESTRICTED_ROUTING_FLAGS


# ============================================================ chronicle-bound decision + invariant
def decide(inputs):
    """PURE decision over an exact-gate frame. Reproduced bit-for-bit by court.verify_chain.

    inputs (all exact gates + a full pre-state snapshot; observables live under inputs['_captured'] and
    are deliberately NOT read here):
        amount_cents, src, dst, src_verified, dst_restricted, supervisor_authorized, accounts_pre
    outputs:
        approved (bool), reasons (list[str]), accounts_post (dict), world_H (str)
    """
    intent = {
        "amount_cents": inputs["amount_cents"],
        "src_verified": inputs["src_verified"],
        "dst_restricted": inputs["dst_restricted"],
        "supervisor_authorized": inputs["supervisor_authorized"],
        "src_balance_cents": inputs["accounts_pre"][inputs["src"]]["balance_cents"],
    }
    reasons = gate_reasons(intent)
    approved = (len(reasons) == 0)
    if approved:
        try:
            accounts_post = be.apply_transfer(inputs["accounts_pre"], inputs["src"], inputs["dst"], inputs["amount_cents"])
        except be.InvariantViolation as e:
            approved = False
            reasons = ["engine refused: %s" % e]
            accounts_post = inputs["accounts_pre"]
    else:
        accounts_post = inputs["accounts_pre"]           # denied -> state unchanged
    return {"approved": approved, "reasons": reasons,
            "accounts_post": accounts_post, "world_H": be.world_hash(accounts_post)}


def aml_invariant(inputs, outputs):
    """Precommitted HARD rule the recorder will not log a breach of (fail-closed). If ANY of these is
    false on an approved transfer, chronicle raises InvariantViolation and the write is rejected:
      (1) conservation: total money is unchanged;
      (2) no negative balance anywhere in the post-state;
      (3) an unverified source over the ceiling is NEVER approved (defends against a buggy/poisoned gate);
      (4) a restricted-routing transfer is NEVER approved without supervisor authorization.
    On a denied transfer the post-state must equal the pre-state (a denial cannot move money)."""
    pre, post = inputs["accounts_pre"], outputs["accounts_post"]
    if not outputs["approved"]:
        return be.world_hash(post) == be.world_hash(pre)
    if be.total_cents(post) != be.total_cents(pre):
        return False
    if any(a["balance_cents"] < 0 for a in post.values()):
        return False
    if not inputs["src_verified"] and inputs["amount_cents"] >= UNVERIFIED_SINGLE_CEILING_CENTS:
        return False
    if inputs["dst_restricted"] and not inputs["supervisor_authorized"]:
        return False
    return True


def observables(inputs):
    """Read-only view of what the volatile agent emitted (prompt/seed/logprobs/confidence). For the
    forensic panel only — never an input to decide()."""
    return captured_view(inputs)
