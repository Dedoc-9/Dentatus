"""
polity/demo_polity.py — deterministic governance: ratify a ruleset change without breaking custody.

  A. GENESIS        — the founding ruleset (version 0), ratified by fiat.
  B. RATIFY         — governors vote on an amendment; a k-quorum mints the next constitution version.
  C. REJECT         — a proposal short of quorum is refused fail-closed; the active ruleset is unchanged.
  D. LINEAGE        — the constitution chain replays; a broken/tampered link is located to the exact version.

Run:  PYTHONHASHSEED=0 python3 demo_polity.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "quorum"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chronicle"))
import constitution as P
import tally as Q
import core

GOVS = ["g1", "g2", "g3", "g4"]


def rh(rules):
    return core.state_hash({"ruleset": "elenchus", "rules": rules})


def main():
    signers = {g: Q.make_witness(g) for g in GOVS}
    reg = P.governor_registry(signers)

    print("A) GENESIS — founding ruleset (version 0):")
    v1_rules = ["premise", "collatz", "add", "compare", "transitivity"]
    c0 = P.genesis_constitution(rh(v1_rules), meta={"name": "founding rules"})
    print("   v%d  ruleset=%s  (%d rules)\n" % (c0["version"], c0["ruleset_hash"][:12], len(v1_rules)))

    print("B) RATIFY — amend the ruleset to add a 'mul' rule (k=3 of 4 governors):")
    v2_rules = v1_rules[:3] + ["mul"] + v1_rules[3:]
    prop = P.propose(c0, rh(v2_rules), proposer_id="g1", meta={"change": "add mul rule"})
    ballots = [P.cast("g1", signers["g1"], prop, "yea"), P.cast("g2", signers["g2"], prop, "yea"),
               P.cast("g3", signers["g3"], prop, "yea"), P.cast("g4", signers["g4"], prop, "nay")]
    res = P.ratify(c0, prop, ballots, k=3, registry=reg)
    c1 = res["constitution"]
    print("   ratified=%s  -> constitution v%d  ruleset=%s  (agreed %d/%d)\n"
          % (res["ratified"], c1["version"], c1["ruleset_hash"][:12], c1["vote"]["agreed"], c1["vote"]["n"]))

    print("C) REJECT — a proposal with only 2 of 4 governors is refused fail-closed:")
    prop2 = P.propose(c1, rh(["premise"]), proposer_id="g2", meta={"change": "gut the ruleset"})
    b2 = [P.cast("g1", signers["g1"], prop2, "yea"), P.cast("g2", signers["g2"], prop2, "yea"),
          P.cast("g3", signers["g3"], prop2, "nay"), P.cast("g4", signers["g4"], prop2, "nay")]
    rej = P.ratify(c1, prop2, b2, k=3, registry=reg)
    print("   ratified=%s  (%s)" % (rej["ratified"], rej["reason"]))
    print("   active ruleset stays v2:", P.active_ruleset([c0, c1]) == c1["ruleset_hash"], "\n")

    print("D) LINEAGE — replay the constitution chain; locate a broken link:")
    print("   [v0, v1] verify:", P.verify_lineage([c0, c1]))
    forged = dict(c1, prev="0" * 64)
    forged["constitution_hash"] = core.state_hash({k: forged[k] for k in forged if k != "constitution_hash"})
    print("   forged prev     :", P.verify_lineage([c0, forged]))
    print("\n   It proves the vote happened and the tally is exact — never that the new rule is wise.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[polity] set PYTHONHASHSEED=0 (constitution + ballot hashes must match across machines).\n\n")
        raise SystemExit(2)
    main()
