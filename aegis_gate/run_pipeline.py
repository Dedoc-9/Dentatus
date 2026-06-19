# SPDX-License-Identifier: AGPL-3.0-only
"""
aegis_gate/run_pipeline.py — the application harness and loopback hook.

Flow per request:
    NL prompt --agent.parse_request--> INTENT (proposal, untrusted)
              --host fact lookup------> src_verified / dst_restricted / supervisor_authorized (exact gates)
              --policy.decide---------> approved? + accounts_post + world_H
              --chronicle.Recorder----> append SIGNED, hash-chained receipt to ledger.jsonl
                                        (recorder REFUSES to log a decision that breaks aml_invariant)

What is gated (folded into the committed hash): amount_cents, src, dst, src_verified, dst_restricted,
supervisor_authorized, the full pre-state snapshot. What is captured but never gated: the prompt, model
seed, token logprobs, parse confidence (agent observables).

Run:
    PYTHONHASHSEED=0 python3 run_pipeline.py          # build ledger.jsonl + print the run
Determinism is required: bit-identical hashing across processes is the premise of the replay court.
"""
import os, sys, json

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from _workbench import (Recorder, JsonlStore, Capture, ruleset_hash, canonical_bytes,
                        HmacSigner, Ed25519Signer, Ed25519Verifier, ed25519_available, InvariantViolation)
from app import agent as agent
from app import policy as policy
from app import bank_engine as be

LEDGER_PATH = os.path.join(_HERE, "ledger.jsonl")
INSTITUTION_SECRET = b"aegis_institution_demo_key"          # ledger attestation (HMAC; demo). Env-only in prod.
# Pinned supervisor keypair (compliance officer). Fixed hex so the demo is reproducible; in production the
# PRIVATE half lives only with the officer and the host stores ONLY the public half.
SUPERVISOR_SK_HEX = "8223d7b568b0371928bfffb1e1434c839d38308dc83377a7b14cfaae64c05146"  # 32-byte demo key; in prod the private half lives only with the officer


def initial_bank():
    """Mock bank database (integer cents). routing flags drive the restricted-routing AML gate."""
    return {
        "A_US_CHECKING": {"balance_cents": 5_000_000, "verified": True,  "routing": "US100"},
        "U_UNVERIFIED":  {"balance_cents": 5_000_000, "verified": False, "routing": "US101"},
        "B_DE_SUPPLIER": {"balance_cents": 0,         "verified": True,  "routing": "DE777"},
        "C_US_LANDLORD": {"balance_cents": 0,         "verified": True,  "routing": "US200"},
        "D_US_SAVINGS":  {"balance_cents": 0,         "verified": True,  "routing": "US201"},
        "Z_OFFSHORE":    {"balance_cents": 0,         "verified": False, "routing": "RU000"},
    }


# ---------------------------------------------------------- supervisor compliance token (Ed25519)
def _supervisor_signer():
    if ed25519_available():
        return Ed25519Signer(SUPERVISOR_SK_HEX)
    return HmacSigner(b"supervisor_fallback_demo_key")        # symmetric fallback (no third-party non-repudiation)


def _supervisor_verifier(signer):
    if ed25519_available():
        return Ed25519Verifier(signer.public_material())      # host holds ONLY the public half
    return signer                                             # HMAC fallback: same key verifies


def _token_message(src, dst, amount_cents):
    return canonical_bytes({"purpose": "compliance_signoff", "src": src, "dst": dst, "amount_cents": amount_cents})


def mint_supervisor_token(signer, src, dst, amount_cents):
    msg = _token_message(src, dst, amount_cents)
    return {"src": src, "dst": dst, "amount_cents": amount_cents, "sig": signer.sign(msg), "algo": signer.algo}


def verify_supervisor_token(verifier, token, src, dst, amount_cents):
    """Returns the exact-gate bool. A token authorizes ONLY the (src,dst,amount) it was signed for, so it
    cannot be replayed onto a different transfer. Missing/invalid token -> False (fail-closed)."""
    if not token:
        return False
    if (token.get("src"), token.get("dst"), token.get("amount_cents")) != (src, dst, amount_cents):
        return False
    try:
        return bool(verifier.verify(_token_message(src, dst, amount_cents), token["sig"]))
    except Exception:
        return False


# ---------------------------------------------------------- the pipeline
def build_inputs(prompt, account_holder, model_seed, accounts, sup_verifier, supervisor_token=None):
    """Run the volatile agent, look up host-side facts, assemble the exact-gate frame for decide()."""
    cap = Capture()
    intent, cap = agent.parse_request(cap, prompt, account_holder, model_seed)
    dst = intent["dst"]
    # host facts (NOT from the prompt): resolved against the authenticated session + the bank DB
    src_verified = bool(accounts.get(account_holder, {}).get("verified", False))
    dst_known = dst in accounts
    dst_restricted = policy.is_restricted(accounts[dst]["routing"]) if dst_known else True
    supervisor_authorized = verify_supervisor_token(sup_verifier, supervisor_token,
                                                     account_holder, dst, intent["amount_cents"])
    if supervisor_token is not None:
        cap.value("supervisor_token", lambda: {"sig": supervisor_token["sig"], "algo": supervisor_token["algo"]})
    sealed = cap.sealed_inputs({})
    inputs = {
        "amount_cents": intent["amount_cents"], "src": account_holder, "dst": dst,
        "src_verified": src_verified, "dst_restricted": dst_restricted,
        "supervisor_authorized": supervisor_authorized,
        "dst_known": dst_known,
        "accounts_pre": accounts,
        "_captured": sealed["_captured"],
    }
    return inputs


def run(verbose=True):
    open(LEDGER_PATH, "w").close()                            # fresh ledger each run
    store = JsonlStore(LEDGER_PATH)
    rh = ruleset_hash(policy.decide, policy.aml_invariant)
    rec = Recorder(HmacSigner(INSTITUTION_SECRET), rh, store=store)

    sup_signer = _supervisor_signer()
    sup_verifier = _supervisor_verifier(sup_signer)

    accounts = initial_bank()
    summary = []
    for label, prompt, holder, seed in agent.request_book():
        # the legit cross-border (restricted DE777) request arrives WITH a valid supervisor sign-off
        token = None
        if label == "legit_supplier":
            i0 = agent.parse_request(Capture(), prompt, holder, seed)[0]
            token = mint_supervisor_token(sup_signer, holder, i0["dst"], i0["amount_cents"])

        inputs = build_inputs(prompt, holder, seed, accounts, sup_verifier, token)
        if not inputs["dst_known"]:
            # unknown payee: deny without touching the engine; still record the denial honestly
            outputs = {"approved": False, "reasons": ["unknown destination account"],
                       "accounts_post": accounts, "world_H": be.world_hash(accounts)}
        else:
            outputs = policy.decide(inputs)

        try:
            receipt = rec.record(label, inputs, outputs, policy.aml_invariant)
        except InvariantViolation as e:
            # the recorder refused an unsafe write: bank state is NOT adopted (rollback to last hash)
            summary.append((label, "REFUSED-FAILCLOSED", str(e)))
            if verbose:
                print("  [%-18s] REFUSED at record time (fail-closed): %s" % (label, e))
            continue

        if outputs["approved"]:
            accounts = outputs["accounts_post"]              # adopt the new world only on an approved write
        verdict = "APPROVED" if outputs["approved"] else "DENIED"
        summary.append((label, verdict, receipt["committed_hash"][:16]))
        if verbose:
            amt = be.dollars(inputs["amount_cents"])
            why = "" if outputs["approved"] else "  reason: %s" % outputs["reasons"][0]
            print("  [%-18s] %-8s %10s %s->%s  +%s%s" %
                  (label, verdict, amt, inputs["src"], inputs["dst"], receipt["committed_hash"][:12], why))
    return summary, accounts


def demonstrate_failclosed():
    """Show the recorder REFUSING to log an approved-but-breaching decision (a poisoned gate that tries to
    approve an unverified over-ceiling drain). The write is rejected; no ledger entry is produced."""
    rh = ruleset_hash(policy.decide, policy.aml_invariant)
    rec = Recorder(HmacSigner(INSTITUTION_SECRET), rh)
    accounts = initial_bank()
    poisoned_inputs = {"amount_cents": 2_000_000, "src": "U_UNVERIFIED", "dst": "D_US_SAVINGS",
                       "src_verified": False, "dst_restricted": False, "supervisor_authorized": False,
                       "dst_known": True, "accounts_pre": accounts, "_captured": {}}
    forged_post = be.apply_transfer(accounts, "U_UNVERIFIED", "D_US_SAVINGS", 2_000_000)
    poisoned_outputs = {"approved": True, "reasons": [], "accounts_post": forged_post,
                        "world_H": be.world_hash(forged_post)}              # a lie: approved over ceiling
    try:
        rec.record("POISONED", poisoned_inputs, poisoned_outputs, policy.aml_invariant)
        return False, "recorder logged an unsafe decision (should not happen)"
    except InvariantViolation as e:
        return True, str(e)


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[aegis_gate] REFUSING TO RUN: set PYTHONHASHSEED=0 (replay court needs stable hashing).\n"
                         "    PYTHONHASHSEED=0 python3 run_pipeline.py\n\n")
        raise SystemExit(2)
    print("AegisGate pipeline — agent proposes, host gates, chronicle records (ledger.jsonl):\n")
    summary, final_accounts = run()
    print("\nFinal bank state (integer cents):")
    for aid, a in sorted(final_accounts.items()):
        print("  %-14s %12s  verified=%s routing=%s" % (aid, be.dollars(a["balance_cents"]), a["verified"], a["routing"]))
    ok, detail = demonstrate_failclosed()
    print("\nFail-closed recorder check: %s" % ("REFUSED an unsafe write (%s)" % detail if ok else "FAILED — %s" % detail))
    print("\nLedger written to ledger.jsonl — open the dashboard to replay & verify it.")
