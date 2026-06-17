"""
chronicle/demo_policy.py — end-to-end proof on a rules-based credit-eligibility flow.

  A. RECORD + REPLAY COURT     — three live decisions, verified bit-for-bit on a separate verifier.
  B. TAMPER + RULE-SWAP        — a flipped denial and a secretly-loosened ruleset are both caught.
  C. FAIL-CLOSED INVARIANT     — an unsafe decision is refused at record time.
  D. ED25519 THIRD-PARTY AUDIT — an auditor with ONLY the public key verifies and cannot forge.
  E. DETERMINISM CAPTURE       — logic that reads a clock + an external bureau still replays exactly.
  F. DURABLE STORE             — the same flow written through an append-only JSONL LedgerStore.
"""
import json, copy
import os, sys


def _require_deterministic_hashing():
    """Fail fast if not launched with PYTHONHASHSEED=0. Bit-identical hashes across processes/machines
    are the whole premise of the replay court; refuse to produce a ledger under a randomized seed so a
    user never trusts a chain they cannot reproduce. See README 'Run it'."""
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write(
            "\n[chronicle] REFUSING TO RUN: PYTHONHASHSEED is not 0.\n"
            "  Deterministic, reproducible hashing is required for the replay court.\n"
            "  Re-run exactly as documented in README.md -> 'Run it':\n\n"
            "      PYTHONHASHSEED=0 python3 demo_policy.py\n\n")
        raise SystemExit(2)


import core
from court import verify_chain, print_verdict
from signing import HmacSigner, Ed25519Signer, Ed25519Verifier, ed25519_available
from capture import Capture, verify_determinism
from store import JsonlStore

SECRET = b"institution_vault_key_demo"   # in production: env-only; prefer Ed25519 for third-party audit


def underwriting_logic(inputs):
    """Pure decision over business inputs. Source is hashed into every receipt (rule-binding)."""
    dti = round(inputs["monthly_debt"] / inputs["monthly_income"], 4)
    approved = bool(dti < 0.45 and inputs["credit_score"] >= 620)
    return {"approved": approved, "dti": dti}


def fair_lending_invariant(inputs, outputs):
    """Precommitted hard rule: nobody with DTI > 0.50 may be approved."""
    return not (outputs["dti"] > 0.50 and outputs["approved"])


APPLICANTS = [
    ("DEC-001", {"monthly_debt": 1500, "monthly_income": 6000, "credit_score": 710}),
    ("DEC-002", {"monthly_debt": 3000, "monthly_income": 5000, "credit_score": 680}),
    ("DEC-003", {"monthly_debt": 2000, "monthly_income": 5200, "credit_score": 600}),
]


def build_ledger(signer):
    rh = core.ruleset_hash(underwriting_logic, fair_lending_invariant)
    rec = core.Recorder(signer, rh)
    ledger = []
    for did, inp in APPLICANTS:
        out = underwriting_logic(inp)
        ledger.append(rec.record(did, inp, out, fair_lending_invariant))
        print("  recorded %s -> approved=%s dti=%.2f  +%s" % (did, out["approved"], out["dti"], ledger[-1]["committed_hash"][:10]))
    return ledger


def underwriting_logic_captured(inputs):
    """Reads two captured values; otherwise identical rules. `inputs` carries the captured reads."""
    cap = Capture.replay(inputs)
    asof = cap.clock("decision_ts", lambda: 0)        # on replay returns the recorded ts; clock untouched
    bureau = cap.external("bureau_score", lambda: 0)  # on replay returns the recorded score; no network
    dti = round(inputs["monthly_debt"] / inputs["monthly_income"], 4)
    approved = bool(dti < 0.45 and bureau >= 620)
    return {"approved": approved, "dti": dti, "asof": asof, "bureau": bureau}


def fair_lending_invariant_captured(inputs, outputs):
    return not (outputs["dti"] > 0.50 and outputs["approved"])


if __name__ == "__main__":
    _require_deterministic_hashing()
    print("A) RECORD three live underwriting decisions (HMAC backend):")
    ledger = build_ledger(HmacSigner(SECRET))
    json.dump(ledger, open("ledger.json", "w"), indent=2)
    print("\n   REPLAY COURT verifies the whole chain:")
    print_verdict(verify_chain(ledger, SECRET, underwriting_logic, fair_lending_invariant), len(ledger))

    print("\nB) TAMPER: flip DEC-002 from denied to approved in the stored record:")
    bad = copy.deepcopy(ledger); bad[1]["frame"]["outputs"]["approved"] = True
    print_verdict(verify_chain(bad, SECRET, underwriting_logic, fair_lending_invariant), len(bad))
    print("   RULE-SWAP: auditor runs a secretly-loosened logic against the honest ledger:")
    def loosened(inputs):
        dti = round(inputs["monthly_debt"] / inputs["monthly_income"], 4)
        return {"approved": bool(dti < 0.70 and inputs["credit_score"] >= 500), "dti": dti}
    print_verdict(verify_chain(ledger, SECRET, loosened, fair_lending_invariant), len(ledger))

    print("\nC) FAIL-CLOSED: try to record a decision that breaches the invariant (DTI 0.60, approved):")
    try:
        core.Recorder(SECRET, "x").record("DEC-BAD", {"monthly_debt": 6, "monthly_income": 10, "credit_score": 800},
                                          {"approved": True, "dti": 0.60}, fair_lending_invariant)
        print("  recorded an unsafe decision (should not happen)")
    except core.InvariantViolation as e:
        print("  refused at record time: %s" % e)

    print("\nD) ED25519 third-party audit (auditor holds ONLY the public key):")
    if ed25519_available():
        signer = Ed25519Signer.generate()
        led = build_ledger(signer)
        auditor = Ed25519Verifier(signer.public_material())       # public key only -- cannot forge
        print("   auditor verdict:")
        print_verdict(verify_chain(led, auditor, underwriting_logic, fair_lending_invariant), len(led))
        wrong = Ed25519Verifier(Ed25519Signer.generate().public_material())  # someone else's key
        print("   wrong public key must fail:")
        print_verdict(verify_chain(led, wrong, underwriting_logic, fair_lending_invariant), len(led))
    else:
        print("  (cryptography not installed -- Ed25519 backend unavailable; HMAC path still works)")

    print("\nE) DETERMINISM CAPTURE: logic reads a clock + external bureau, yet replays bit-for-bit:")
    rh = core.ruleset_hash(underwriting_logic_captured, fair_lending_invariant_captured)
    rec = core.Recorder(SECRET, rh)
    cap = Capture()
    cap.clock("decision_ts", lambda: 1718500000)        # the live clock read
    cap.external("bureau_score", lambda: 690)           # the live bureau call
    sealed = cap.sealed_inputs({"monthly_debt": 1500, "monthly_income": 6000})
    out = underwriting_logic_captured(sealed)
    cap_ledger = [rec.record("DEC-CAP", sealed, out, fair_lending_invariant_captured)]
    ok, detail = verify_determinism(underwriting_logic_captured, sealed)
    print("   determinism leak check: %s (%s)" % ("PASS" if ok else "FAIL", detail))
    print_verdict(verify_chain(cap_ledger, SECRET, underwriting_logic_captured, fair_lending_invariant_captured), 1)

    print("\nF) DURABLE STORE: same flow appended to an append-only JSONL ledger:")
    open("ledger_store.jsonl", "w").close()
    store = JsonlStore("ledger_store.jsonl")
    rec = core.Recorder(SECRET, core.ruleset_hash(underwriting_logic, fair_lending_invariant), store=store)
    for did, inp in APPLICANTS:
        rec.record(did, inp, underwriting_logic(inp), fair_lending_invariant)
    print("   re-open the file and verify what was persisted:")
    print_verdict(verify_chain(list(JsonlStore("ledger_store.jsonl")), SECRET,
                               underwriting_logic, fair_lending_invariant), 3)
