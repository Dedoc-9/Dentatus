"""
chronicle/court.py — the replay court. Verifies a recorded ledger end-to-end on a SEPARATE machine.

For each decision it proves five things, and names the exact failure point if any breaks:
  1. CHAIN     — prev-hash links and seq are contiguous (no insertion / deletion / reorder of past decisions)
  2. RULE-BOUND— the logic the auditor runs hashes to the recorded ruleset_hash (the rules did not change)
  3. REPLAY    — re-running the logic on the recorded inputs reproduces the recorded outputs bit-for-bit
  4. INVARIANT — the replayed decision still satisfies the precommitted invariant
  5. ATTEST    — the re-derived content hash + signature match the receipt (record / key were not altered)

The verifier is pluggable: pass an Ed25519Verifier holding only the PUBLIC key and an auditor can prove
authenticity WITHOUT being able to forge. A bytes/str is accepted as a shorthand HMAC verifier.
"""
import sys, json, hashlib
import core
from signing import HmacVerifier


class Verdict:
    def __init__(self): self.ok = True; self.reason = None; self.at = None
    def fail(self, reason, at): self.ok = False; self.reason = reason; self.at = at; return self


def verify_chain(ledger, verifier, logic_fn, invariant_fn):
    v = Verdict()
    vf = verifier if hasattr(verifier, "verify") else HmacVerifier(verifier)
    running_ruleset = core.ruleset_hash(logic_fn, invariant_fn)
    prev = core.GENESIS; seq = 0
    for r in ledger:
        f = r["frame"]
        if f["prev"] != prev or f["seq"] != seq:
            return v.fail("CHAIN broken (insertion/deletion/reorder)", seq)
        if f["ruleset_hash"] != running_ruleset:
            return v.fail("RULESET changed (logic differs from what was recorded)", f["seq"])
        actual = logic_fn(f["inputs"])
        if core.canonical_bytes(actual) != core.canonical_bytes(f["outputs"]):
            return v.fail("REPLAY drift (recorded outputs not reproducible from inputs)", f["seq"])
        if not invariant_fn(f["inputs"], actual):
            return v.fail("INVARIANT breach on replay", f["seq"])
        # re-derive the content address + chain link directly from the (replayed) frame
        sh = core.state_hash({"seq": f["seq"], "decision_id": f["decision_id"], "inputs": f["inputs"],
                              "outputs": actual, "ruleset_hash": running_ruleset, "prev": prev})
        committed = hashlib.sha256(("%s|%s" % (sh, prev)).encode()).hexdigest()
        if committed != r["committed_hash"]:
            return v.fail("TAMPER (content hash mismatch)", f["seq"])
        if not vf.verify(committed.encode(), r["signature"]):
            return v.fail("TAMPER (signature mismatch / wrong key)", f["seq"])
        prev = r["committed_hash"]; seq += 1
    return v


def print_verdict(v, n):
    if v.ok:
        print("  VERIFIED -- %d decisions reproduced bit-for-bit, chain intact, rules unchanged, untampered." % n)
    else:
        print("  REJECTED: %s  (at decision seq %s)" % (v.reason, v.at))
    return 0 if v.ok else 1


if __name__ == "__main__":
    import demo_policy as P
    ledger = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "ledger.json"))
    v = verify_chain(ledger, P.SECRET, P.underwriting_logic, P.fair_lending_invariant)
    sys.exit(print_verdict(v, len(ledger)))
