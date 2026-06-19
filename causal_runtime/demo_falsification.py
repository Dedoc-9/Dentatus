"""
causal_runtime/demo_falsification.py — the system as a FALSIFIABLE STRUCTURE-MAINTENANCE engine, not a causal
discoverer. Ties together the held-out gate, the Self-Confirmation Benchmark, and the two-tier split.

The invariant that survived every experiment: the ghost is a self-skepticism engine. A proposed edge is not
believed because it recurred; it is corroborated only by surviving attempts to falsify it on held-out data, and
its standing can DECAY. Run under PYTHONHASHSEED=0.
"""
import falsification as F
import self_confirmation as SC
import tiers as T


def run():
    rows = SC.run()
    props = []
    for n in SC.WORLDS:
        tr, ho = SC.WORLDS[n]()
        th, tm, _ = F.test_edge("A", "C", tr)
        p = F.make_proposal(n, "C", train_hits=th, train_misses=tm)
        hh, hm, _ = F.test_edge("A", "C", ho)
        props.append(F.apply_heldout(p, hh, hm, epoch=1))
    return rows, T.classify(props), props


if __name__ == "__main__":
    rows, rep, props = run()
    print("== Self-Confirmation Benchmark (naive promotes all; the gate does not) ==")
    for n in ("true", "confounder", "regime"):
        r = rows[n]
        print("  %-11s naive=promote -> falsified=%-12s score=%d" % (n, r["status"], r["score"]))
    print("\n== Two tiers (allocation needs only prediction; structure must be earned) ==")
    print("  predictive (allocation)      :", rep["predictive"])
    print("  corroborated (may claim)     :", rep["may_claim_structure"])
    print("  vocabulary, per edge:")
    for p in props:
        print("    %-12s -> %s" % ((p.source, p.target), T.vocabulary_for(p)))
    print("\nLAW: correlation->allocation ALLOWED ; prediction->truth FORBIDDEN ;")
    print("     falsification->proposal status ALLOWED ; falsification->committed reality FORBIDDEN")
