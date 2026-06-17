"""
tessera/demo_tessera.py — forge a shard, hand it to a stranger, let the math check the process history.

  A. MINT + OFFLINE REPLAY  — a producer mints a tessera over a syracuse orbit; a verifier with ONLY the
                              same pinned rule re-runs it and confirms the exact path. No trust required.
  B. TAMPER                 — a forged step count / terminus / wrong rule is named precisely.
  C. FORENSIC DIVERGENCE    — given a producer's full claimed scroll, the exact lying step index is found.
  D. IMMUTABLE LINEAGE      — shards chain (prev binds to the prior path_hash); a broken link is located.

Run:  PYTHONHASHSEED=0 python3 demo_tessera.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_WB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_WB, "syracuse"))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
import shard as T
import orbit as SY
from signing import Ed25519Signer, ed25519_available


# the declared deterministic computation (module-level so its source binds into ruleset_hash)
def rule(state):
    return {"n": SY.step(state["n"])}


def done(state):
    return state["n"] == 1


def rule_uncompressed(state):
    return {"n": SY.step(state["n"], compressed=False)}


def main():
    signer = Ed25519Signer() if ed25519_available() else None
    print("A) MINT + OFFLINE REPLAY (producer signs; verifier trusts no producer, only the rule):")
    tess = T.mint(rule, done, {"n": 27}, signer=signer)
    print("   shard: seed=27  steps=%d  terminus=%s  path_hash=%s  signed=%s"
          % (tess["steps"], tess["terminus"], tess["path_hash"][:16], tess["signature"] is not None))
    ok, detail = T.verify(tess, rule, done)
    print("   stranger replays on their own machine -> %s (%s)\n" % (ok, detail))

    print("B) TAMPER — the math names the exact lie:")
    print("   claim fewer steps :", T.verify(dict(tess, steps=40), rule, done)[1])
    print("   forge terminus    :", T.verify(dict(tess, terminus={"n": 99}), rule, done)[1])
    print("   wrong rule        :", T.verify(tess, rule_uncompressed, done)[1])
    print()

    print("C) FORENSIC DIVERGENCE — given a full claimed scroll, locate the lying step:")
    honest = [{"n": x} for x in SY.orbit(27)]
    print("   honest scroll       -> divergence index:", T.locate_divergence(tess, rule, honest))
    tampered = list(honest); tampered[10] = {"n": 123456}
    print("   one step altered    -> divergence index:", T.locate_divergence(tess, rule, tampered))
    print()

    print("D) IMMUTABLE LINEAGE (shards chain; prev binds to the prior path_hash):")
    t2 = T.link(tess, rule, done, signer=signer, seed_from=lambda term: {"n": 97})
    chain = [tess, t2]
    print("   two-shard lineage   -> verify:", T.verify_lineage(chain, rule, done))
    # unsigned chain to surface the LINEAGE fault itself (a signed prev would trip the signature first)
    u1 = T.mint(rule, done, {"n": 27})
    u2 = T.link(u1, rule, done, seed_from=lambda term: {"n": 97})
    broken = [u1, dict(u2, prev="deadbeef" + "0" * 56)]
    print("   broken link         -> verify:", T.verify_lineage(broken, rule, done))
    print("\n   integrity != truth: the shard proves the steps were taken, never that the result means anything.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[tessera] set PYTHONHASHSEED=0 (the path-hash must match across machines).\n\n")
        raise SystemExit(2)
    main()
