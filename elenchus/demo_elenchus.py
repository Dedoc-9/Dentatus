"""
elenchus/demo_elenchus.py — put a claimed derivation on the stand; the math names the exact lie or gap.

  A. VALID TRACE     — premises + steps citing pinned rules replay cleanly; the conclusion is derived.
  B. FABRICATED      — a step asserts an output the rule does not produce; the exact step is named.
  C. SKIPPED STEP    — a transitivity that cites an unestablished relation is caught as a GAP.
  D. UNKNOWN RULE    — a step invoking a rule outside the pinned set is rejected.
  E. PROOF           — the verdict is itself a tessera shard a stranger replays; tampering is caught.

Run:  PYTHONHASHSEED=0 python3 demo_elenchus.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chronicle"))
import interrogate as E
from signing import Ed25519Signer, ed25519_available

PREM = [{"var": "a", "val": 27}]
VALID = [
    {"rule": "collatz", "args": {"src": "a", "dst": "b"}, "claim": {"kind": "val", "var": "b", "val": 41}},
    {"rule": "collatz", "args": {"src": "b", "dst": "c"}, "claim": {"kind": "val", "var": "c", "val": 62}},
    {"rule": "compare", "args": {"lhs": "a", "rhs": "b", "op": "<"}, "claim": {"kind": "rel", "lhs": "a", "op": "<", "rhs": "b"}},
    {"rule": "compare", "args": {"lhs": "b", "rhs": "c", "op": "<"}, "claim": {"kind": "rel", "lhs": "b", "op": "<", "rhs": "c"}},
    {"rule": "transitivity", "args": {"a": "a", "b": "b", "c": "c", "op": "<"}, "claim": {"kind": "rel", "lhs": "a", "op": "<", "rhs": "c"}},
]
CONCLUSION = {"kind": "rel", "lhs": "a", "op": "<", "rhs": "c"}


def main():
    print("A) VALID TRACE (from a=27: two collatz steps, two comparisons, one transitivity):")
    print("   verdict:", E.verify_trace(PREM, VALID, conclusion=CONCLUSION), "\n")

    print("B) FABRICATED (step 1 claims a collatz output the rule does not produce):")
    bad = list(VALID)
    bad[1] = {"rule": "collatz", "args": {"src": "b", "dst": "c"}, "claim": {"kind": "val", "var": "c", "val": 999}}
    print("   verdict:", E.verify_trace(PREM, bad), "\n")

    print("C) SKIPPED STEP (transitivity without establishing b<c first):")
    gap = [VALID[0], VALID[1], VALID[2], VALID[4]]
    print("   verdict:", E.verify_trace(PREM, gap), "\n")

    print("D) UNKNOWN RULE (a step invokes a rule outside the pinned set):")
    unk = [{"rule": "telepathy", "args": {}, "claim": {"kind": "val", "var": "z", "val": 1}}]
    print("   verdict:", E.verify_trace(PREM, unk), "\n")

    print("E) PROOF — the verdict is a tessera shard; a stranger replays the interrogation:")
    signer = Ed25519Signer() if ed25519_available() else None
    shard = E.prove_trace(PREM, VALID, signer=signer)
    print("   shard: %d steps  signed=%s -> verify=%s" % (shard["steps"], shard["signature"] is not None, E.verify_proof(shard)))
    print("   tampered (steps -1):", E.verify_proof(dict(shard, steps=shard["steps"] - 1))[1])
    print("\n   It proves the steps follow the declared rules and replay — never that the conclusion is TRUE.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[elenchus] set PYTHONHASHSEED=0 (the interrogation proof must match across machines).\n\n")
        raise SystemExit(2)
    main()
