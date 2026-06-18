"""
stasis/demo_stasis.py — the boundary layer: Iron Canon, Divergence Ledger, Lazy Lattice.

  A. IRON CANON       — order-independent canonical bytes; ambiguous/non-integer types are rejected.
  B. DIVERGENCE LEDGER— a benign observable drift WARNs; a changed gate FAILs (the exact field is named).
  C. LAZY LATTICE     — many shard hashes fold into one Merkle root; a leaf is proven on demand; tamper fails.

Run:  PYTHONHASHSEED=0 python3 demo_stasis.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import canon as C
import drift as D
import batch as B


def main():
    print("A) IRON CANON (strict boundary into the order zone):")
    print("   {a,b} == {b,a}:", C.canon_hash({"a": 1, "b": 2}) == C.canon_hash({"b": 2, "a": 1}))
    for bad in ({"s": {1, 2}}, {"raw": b"x"}, {"price": 1.5}):
        print("   reject %-14s -> %s" % (str(bad)[:14], C.is_canonical(bad)[1].split(":", 1)[1].strip()[:46]))
    print("   float ok only when explicitly an observable:", C.is_canonical({"logprob": -0.12}, allow_float=True)[0], "\n")

    print("B) DIVERGENCE LEDGER (gate vs observable — lie vs noise):")
    gate = ["decision", "amount_cents"]
    exp = {"decision": "approve", "amount_cents": 4500, "logprob": -0.12, "latency_ms": 40}
    benign = {"decision": "approve", "amount_cents": 4500, "logprob": -0.13, "latency_ms": 55}
    lie = {"decision": "deny", "amount_cents": 4500, "logprob": -0.12, "latency_ms": 40}
    vb, vl = D.classify(exp, benign, gate), D.classify(exp, lie, gate)
    print("   observable drift -> %s (%s on %s)  -> feed to assay as %s"
          % (vb["verdict"], vb["event"]["type"], vb["event"]["field"], D.feed_assay(vb)["signal"]))
    print("   gate changed     -> %s (%s on %s: %s != %s)  -> belongs in front of elenchus\n"
          % (vl["verdict"], vl["event"]["type"], vl["event"]["field"], vl["event"]["expected"], vl["event"]["actual"]))

    print("C) LAZY LATTICE (batch many shards; verify a leaf on demand):")
    leaves = [C.canon_hash({"shard": i}) for i in range(8)]
    shard = B.batch_shard(leaves)
    print("   %d shards -> one root %s" % (shard["count"], shard["root"][:16]))
    proof = B.inclusion_proof(leaves, 5)
    print("   leaf 5 inclusion proof length=%d (O(log M)); verifies: %s" % (len(proof), B.verify_inclusion(leaves[5], proof, shard["root"])))
    print("   a tampered leaf fails its proof:", not B.verify_inclusion(C.canon_hash({"shard": 999}), proof, shard["root"]))
    print("\n   stasis admits reality at the boundary so the order zone (fuel/tessera/quorum) stays exact.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[stasis] set PYTHONHASHSEED=0 (canonical hashes must match across machines).\n\n")
        raise SystemExit(2)
    main()
