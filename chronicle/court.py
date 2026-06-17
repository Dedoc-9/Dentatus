"""
chronicle/court.py — the replay court. Verifies a recorded ledger end-to-end on a SEPARATE machine.

For each decision it proves five things, and names the exact failure point if any breaks:
  1. CHAIN     — prev-hash links and seq are contiguous (no insertion / deletion / reorder of past decisions)
  2. RULE-BOUND— the logic the auditor runs hashes to the recorded ruleset_hash (the rules did not change)
  3. REPLAY    — re-running the logic on the recorded inputs reproduces the recorded outputs bit-for-bit
  4. INVARIANT — the replayed decision still satisfies the precommitted invariant
  5. ATTEST    — the re-derived content hash + HMAC match the receipt (record / key were not altered)
"""
import sys, json, hmac
import core


class Verdict:
    def __init__(self): self.ok = True; self.reason = None; self.at = None
    def fail(self, reason, at): self.ok = False; self.reason = reason; self.at = at; return self


def verify_chain(ledger, secret, logic_fn, invariant_fn):
    v = Verdict()
    secret_b = secret if isinstance(secret, bytes) else secret.encode()
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
        rr = core.Recorder(secret_b, running_ruleset, prev_hash=prev, seq=seq).record(
            f["decision_id"], f["inputs"], actual, invariant_fn)
        if rr["committed_hash"] != r["committed_hash"]:
            return v.fail("TAMPER (content hash mismatch)", f["seq"])
        if not hmac.compare_digest(rr["signature"], r["signature"]):
            return v.fail("TAMPER (signature mismatch / wrong key)", f["seq"])
        prev = r["committed_hash"]; seq += 1
    return v


def print_verdict(v, n):
    if v.ok:
        print("  ✅ VERIFIED — %d decisions reproduced bit-for-bit, chain intact, rules unchanged, untampered." % n)
    else:
        print("  ❌ %s  (at decision seq %s)" % (v.reason, v.at))
    return 0 if v.ok else 1


if __name__ == "__main__":
    # CLI: python court.py <ledger.json>  — loads the demo policy as the logic under audit
    import demo_policy as P
    ledger = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "ledger.json"))
    v = verify_chain(ledger, P.SECRET, P.underwriting_logic, P.fair_lending_invariant)
    sys.exit(print_verdict(v, len(ledger)))
