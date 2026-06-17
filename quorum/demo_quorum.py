"""
quorum/demo_quorum.py — exact integer consensus, and the 2D pact lattice, end to end.

  A. UNANIMOUS         — n witnesses agree; certificate issued; ESS == 1 (one opinion-bloc).
  B. HONEST DISSENT    — one witness forks; k=3 still certifies; the ghost names the dissenter (preserved).
  C. STRICT UNANIMITY  — same votes, k=n; no quorum; the fork set is emitted instead of a verdict.
  D. EQUIVOCATION      — a witness double-signs two states for one round; excluded and named.
  E. INTRUDER          — an unpinned voter is rejected, never counted.
  F. LATTICE           — 3 rounds bound into a pact covenant; then a lateral fault and a temporal fault,
                         each localized to the exact axis.

Run:  PYTHONHASHSEED=0 python3 demo_quorum.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tally as Q
import lattice as L

WS = ["w1", "w2", "w3", "w4"]


def _setup():
    signers = {w: Q.make_witness(w) for w in WS}
    return signers, Q.build_registry(signers)


def votes(signers, rid, states):
    return [Q.witness_vote(w, rid, s, signers[w]) for w, s in states.items()]


def main():
    signers, reg = _setup()
    print("Witness keys: %s (algo=%s)\n" % (", ".join(WS), signers["w1"].algo))

    print("A) UNANIMOUS (k=3): all four sign the same world state")
    c = Q.tally(votes(signers, 0, {w: {"x": 7} for w in WS}), 3, reg, 0)
    o = c["observables"]
    print("   certified=%s  agreed=%d/%d  quorum_hash=%s  A_r=%.2f ESS=%.2f\n"
          % (c["certified"], c["agreed"], c["n"], c["quorum_hash"][:12], o["agreement_ratio"], o["ess_opinions"]))

    print("B) HONEST DISSENT (k=3): w4 reports a different state")
    c = Q.tally(votes(signers, 1, {"w1": {"x": 7}, "w2": {"x": 7}, "w3": {"x": 7}, "w4": {"x": 8}}), 3, reg, 1)
    print("   certified=%s  ghost(dissent)=%s  divergence=%.2f  ESS=%.2f"
          % (c["certified"], list(c["ghost"].keys()), c["observables"]["divergence"], c["observables"]["ess_opinions"]))
    print("   -> the certificate holds; the dissent is recorded, not discarded (it may be the correct one)\n")

    print("C) STRICT UNANIMITY (k=4): same votes, threshold raised")
    c = Q.tally(votes(signers, 1, {"w1": {"x": 7}, "w2": {"x": 7}, "w3": {"x": 7}, "w4": {"x": 8}}), 4, reg, 1)
    print("   certified=%s  quorum_hash=%s  (fork emitted; k is the declared model cut)\n" % (c["certified"], c["quorum_hash"]))

    print("D) EQUIVOCATION (k=3): w2 signs TWO different states for the same round")
    v = votes(signers, 2, {"w1": {"x": 7}, "w3": {"x": 7}, "w4": {"x": 7}})
    v += [Q.witness_vote("w2", 2, {"x": 7}, signers["w2"]), Q.witness_vote("w2", 2, {"x": 9}, signers["w2"])]
    c = Q.tally(v, 3, reg, 2)
    print("   equivocators=%s  excluded from count  certified=%s (counted_n=%d)\n" % (c["equivocators"], c["certified"], c["n"]))

    print("E) INTRUDER (k=3): an unpinned witness submits a vote")
    intruder = Q.make_witness("evil")
    v = votes(signers, 3, {"w1": {"x": 7}, "w2": {"x": 7}, "w3": {"x": 7}})
    v.append(Q.witness_vote("w_evil", 3, {"x": 7}, intruder))
    c = Q.tally(v, 3, reg, 3)
    print("   rejected=%s  certified=%s (intruder never counted)\n" % ([r["witness"] for r in c["rejected"]], c["certified"]))

    print("F) THE 2D LATTICE: quorum (lateral) bound to pact (temporal)")
    notary = Q.make_witness("notary")
    preg = {"notary": Q.verifier_for(notary)}

    def monotonic(prev, new):
        return new["round"] > prev["round"]

    def rnd(rid, states):
        return (rid, votes(signers, rid, states))

    good = [rnd(0, {w: {"acc": 10} for w in WS}), rnd(1, {w: {"acc": 15} for w in WS}), rnd(2, {w: {"acc": 22} for w in WS})]
    res = L.evaluate(good, 3, reg, "notary", notary, preg, monotonic)
    print("   happy:          ok=%s  lattice_hash=%s" % (res["ok"], res["lattice_hash"][:16]))

    badlat = [rnd(0, {w: {"acc": 10} for w in WS}),
              ("1", votes(signers, "1", {"w1": {"acc": 15}, "w2": {"acc": 15}, "w3": {"acc": 16}, "w4": {"acc": 16}}))]
    res = L.evaluate(badlat, 3, reg, "notary", notary, preg, monotonic)
    print("   lateral fault:  ok=%s  axis=%s round=%s ghost=%s" %
          (res["ok"], res["fault"]["axis"], res["fault"]["round"], res["fault"]["ghost"]))

    badtmp = [rnd(2, {w: {"acc": 10} for w in WS}), rnd(1, {w: {"acc": 15} for w in WS})]
    res = L.evaluate(badtmp, 3, reg, "notary", notary, preg, monotonic)
    print("   temporal fault: ok=%s  axis=%s (round index regressed; covenant rule broke)" % (res["ok"], res["fault"]["axis"]))
    print("\n   Two orthogonal residuals — lateral dissent and temporal break — never collapsed into one number.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[quorum] set PYTHONHASHSEED=0 (exact hashing is the premise of integer consensus).\n\n")
        raise SystemExit(2)
    main()
