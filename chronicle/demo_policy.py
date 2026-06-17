"""
chronicle/demo_policy.py — end-to-end proof on a rules-based credit-eligibility flow (no ML needed).
Records real decisions, verifies them in the court, then demonstrates that tampering and rule-changes
are caught, and that an invariant-violating decision is refused at record time.
"""
import json, copy
import core
from court import verify_chain, print_verdict

SECRET = b"institution_vault_key_demo"   # in production: env-only, and prefer Ed25519 for third-party audit


def underwriting_logic(inputs):
    """The deterministic decision. Its SOURCE is hashed into every receipt (rule-binding)."""
    dti = round(inputs["monthly_debt"] / inputs["monthly_income"], 4)
    approved = bool(dti < 0.45 and inputs["credit_score"] >= 620)
    return {"approved": approved, "dti": dti}


def fair_lending_invariant(inputs, outputs):
    """Precommitted hard rule: nobody with DTI > 0.50 may be approved."""
    return not (outputs["dti"] > 0.50 and outputs["approved"])


APPLICANTS = [
    ("DEC-001", {"monthly_debt": 1500, "monthly_income": 6000, "credit_score": 710}),  # dti .25 -> approve
    ("DEC-002", {"monthly_debt": 3000, "monthly_income": 5000, "credit_score": 680}),  # dti .60 -> deny
    ("DEC-003", {"monthly_debt": 2000, "monthly_income": 5200, "credit_score": 600}),  # low score -> deny
]


def build_ledger():
    rh = core.ruleset_hash(underwriting_logic, fair_lending_invariant)
    rec = core.Recorder(SECRET, rh)
    ledger = []
    for did, inp in APPLICANTS:
        out = underwriting_logic(inp)
        ledger.append(rec.record(did, inp, out, fair_lending_invariant))
        print("  recorded %s -> approved=%s dti=%.2f  ⊕%s" % (did, out["approved"], out["dti"], ledger[-1]["committed_hash"][:10]))
    return ledger


if __name__ == "__main__":
    print("1) RECORD three live underwriting decisions into the ledger:")
    ledger = build_ledger()
    json.dump(ledger, open("ledger.json", "w"), indent=2)

    print("\n2) REPLAY COURT (auditor, separate machine) verifies the whole chain:")
    print_verdict(verify_chain(ledger, SECRET, underwriting_logic, fair_lending_invariant), len(ledger))

    print("\n3) TAMPER: flip DEC-002 from denied to approved in the stored record:")
    bad = copy.deepcopy(ledger); bad[1]["frame"]["outputs"]["approved"] = True
    print_verdict(verify_chain(bad, SECRET, underwriting_logic, fair_lending_invariant), len(bad))

    print("\n4) RULE-SWAP: an auditor runs a SECRETLY-LOOSENED logic against the honest ledger:")
    def loosened(inputs):
        dti = round(inputs["monthly_debt"] / inputs["monthly_income"], 4)
        return {"approved": bool(dti < 0.70 and inputs["credit_score"] >= 500), "dti": dti}
    print_verdict(verify_chain(ledger, SECRET, loosened, fair_lending_invariant), len(ledger))

    print("\n5) FAIL-CLOSED: try to record a decision that breaches the invariant (DTI 0.60, approved):")
    try:
        core.Recorder(SECRET, "x").record("DEC-BAD", {"monthly_debt": 6, "monthly_income": 10, "credit_score": 800},
                                          {"approved": True, "dti": 0.60}, fair_lending_invariant)
        print("  ❌ recorded an unsafe decision (should not happen)")
    except core.InvariantViolation as e:
        print("  ✅ refused at record time: %s" % e)
