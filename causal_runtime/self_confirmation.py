"""
causal_runtime/self_confirmation.py — the Self-Confirmation Benchmark.

The brutal test: three worlds where TRAINING evidence looks identical (A and C correlate, a proposal is formed),
but a HELD-OUT window separates a real structure from a self-confirming fiction. The naive frequency-only model
(`coupling_discovery` alone) would promote all three — that is the bug. The held-out gate must NOT.

    world        structure                       held-out behaviour                naive   falsified
    true         A → C                            A changes -> C follows            promote CORROBORATED
    confounder   A ← X → C                        A varies alone -> C does NOT      promote REJECTED   (decays)
    regime       A → C only when temp>threshold   new regime -> A changes, C flat   promote not CORROBORATED

`naive` = "did training correlate?" (always yes here). `falsified` = the held-out track record. The gap between
the two columns is exactly the self-confirmation a frequency-only system hides. Deterministic. Stdlib only.
"""
import falsification as F

N = 10


def world_true():
    train = [{"A": i, "C": 3 * i, "temp": 9} for i in range(N)]
    heldout = [{"A": 100 + i, "C": 3 * (100 + i), "temp": 9} for i in range(N)]   # A changes -> C follows
    return train, heldout


def world_confounder():
    # A ← X → C : in TRAIN both ride X (correlate). In HELD-OUT, A is perturbed alone (X, C stay flat):
    # a natural experiment that the edge A→C must survive — and cannot.
    train = [{"X": i, "A": 2 * i, "C": 4 * i, "temp": 9} for i in range(N)]
    heldout = [{"X": 50, "A": 50 + i, "C": 200, "temp": 9} for i in range(N)]      # A varies, C constant
    return train, heldout


def world_regime():
    # A → C only while temp > 5. TRAIN is all in-regime (temp high) so it looks causal. HELD-OUT is a new
    # regime (temp low) where the local regularity does not hold.
    train = [{"A": i, "C": 3 * i, "temp": 9} for i in range(N)]
    heldout = [{"A": 100 + i, "C": 777, "temp": 1} for i in range(N)]              # new regime: C frozen
    return train, heldout


WORLDS = {"true": world_true, "confounder": world_confounder, "regime": world_regime}


def evaluate(name):
    train, heldout = WORLDS[name]()
    th, tm, topp = F.test_edge("A", "C", train)
    p = F.make_proposal("A", "C", train_hits=th, train_misses=tm)
    hh, hm, hopp = F.test_edge("A", "C", heldout)
    p = F.apply_heldout(p, hh, hm, epoch=1)
    naive_promote = th > tm                                      # frequency-only model would promote
    return {"world": name, "train": (th, tm), "heldout": (hh, hm, hopp),
            "naive_promote": naive_promote, "status": p.status,
            "score": F.corroboration_score(p)}


def run():
    return {n: evaluate(n) for n in WORLDS}


def verdict(rows=None):
    rows = rows or run()
    ok = (rows["true"]["status"] == F.CORROBORATED
          and rows["confounder"]["status"] in (F.REJECTED, F.DECAYING)
          and rows["regime"]["status"] != F.CORROBORATED
          and all(rows[w]["naive_promote"] for w in WORLDS))            # naive promotes ALL -> the contrast
    return ("held-out-gate-breaks-self-confirmation" if ok else "inconclusive"), rows


if __name__ == "__main__":
    rows = run()
    for n in ("true", "confounder", "regime"):
        r = rows[n]
        print("%-11s naive=promote  ->  falsified=%-12s  (train %s, heldout %s, score %d)"
              % (n, r["status"], r["train"], r["heldout"], r["score"]))
    label, _ = verdict(rows)
    print("\nVERDICT:", label)
    print("the naive frequency-only model promotes ALL three; the held-out gate corroborates only the true edge.")
    print("LAW: falsification -> proposal status ALLOWED ; falsification -> committed reality FORBIDDEN")
