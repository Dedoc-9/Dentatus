"""
intervention/natural_experiment.py — quasi-experimental evidence from the committed history (no shadow, no do()).

The shadow `do()` experiment tests a counterfactual OF THE MODEL. This module uses the one thing the shadow
system lacks: the real kernel's ACTUAL recorded transitions. It mines committed history for moments the world
happened to supply a natural experiment — `source` varied while the named confounders stayed stable — and asks
whether `target` responded. That is instrumental-variable / quasi-experimental logic on real data:

    candidate: A → C
    context  : A varied, confounders {X,...} stable, C response observed
    result   : supports | refutes

No mutation. No alternate world. No fantasy counterfactual — only observation of what the kernel already
committed. It cannot manufacture the variation it needs; when the history never isolates `source`, it reports
NONE (untested), never a false positive. Law: `committed-history mining → evidence` ALLOWED;
`mining → committed reality` FORBIDDEN (pure read). Deterministic. Stdlib only.
"""
from collections import namedtuple

NaturalExperiment = namedtuple(
    "NaturalExperiment", "source target confounders supports refutes opportunities verdict")


def _changed(a, b):
    return a is not None and b is not None and a != b


def _stable(state0, state1, nodes):
    return all(state0.get(n) == state1.get(n) for n in nodes)


def mine(source, target, confounders, history, lag=1):
    """Scan `history` (committed states) for natural experiments isolating `source` from `confounders`, and
    tally whether `target` responded. Returns a NaturalExperiment record."""
    confounders = [c for c in confounders if c not in (source, target)]
    supports = refutes = opps = 0
    for t in range(len(history) - lag):
        s0, s1 = history[t].get(source), history[t + 1].get(source)
        if not _changed(s0, s1):
            continue
        if not _stable(history[t], history[t + 1], confounders):
            continue                                    # confounders moved too -> not a clean isolation
        opps += 1
        if _changed(history[t].get(target), history[t + lag].get(target)):
            supports += 1
        else:
            refutes += 1
    if opps == 0:
        verdict = "NONE"                                # the history never isolated the cause -> untested
    elif refutes == 0:
        verdict = "SUPPORTS"
    elif supports == 0:
        verdict = "REFUTES"
    else:
        verdict = "MIXED"
    return NaturalExperiment(source, target, tuple(sorted(confounders)),
                             supports, refutes, opps, verdict)


if __name__ == "__main__":
    # A real A->C history where A is sometimes isolated from confounder X
    true_hist = [{"A": i, "C": 3 * i, "X": 0} for i in range(8)]            # A isolated, C follows
    conf_hist = [{"A": i, "C": 200, "X": 0} for i in range(8)]             # A isolated, C flat (confounded)
    none_hist = [{"A": 5, "C": i, "X": i} for i in range(8)]              # A never varies -> untested
    for label, h in [("true A->C", true_hist), ("confounded", conf_hist), ("no isolation", none_hist)]:
        r = mine("A", "C", ["X"], h)
        print("%-14s -> %-8s (supports %d, refutes %d, opportunities %d)"
              % (label, r.verdict, r.supports, r.refutes, r.opportunities))
    print("\nLAW: committed-history mining -> evidence ALLOWED ; -> committed reality FORBIDDEN (pure read)")
