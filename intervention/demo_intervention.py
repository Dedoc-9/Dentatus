"""
demo_intervention.py — observation proposes, the airlock authorizes a question, intervention answers it, and
the committed history never moves.

Chain shown end to end:
    coupling candidate (from a persistent ghost)  ->  intervention REQUEST  ->  airlock AUTHORIZE
        ->  shadow do()-experiment  ->  evidence verdict (CONFIRMED / REJECTED / CYCLE)

Then the extended invariant, proven on a real application: running EVERY experiment in the Causal Intervention
Benchmark leaves the committed AetherPulse hash trajectory byte-identical — the experiment subsystem has no path
to committed history. Run under PYTHONHASHSEED=0.
"""
import _wb
import protocol as P
import benchmark as B
from query import query

CD = _wb.coupling_discovery()
K = _wb.aetherpulse_kernel()


def _make_world():
    bodies = [K.body(i, (40 + 4 * i, 70 - 3 * i, 40 + i), (5 - i, i, 2), (4, 4, 4)) for i in range(1, 6)]
    return K.make_world(bodies, ((0, 0, 0), (100, 100, 100)), gravity=10, dt_ms=8)


def run():
    # 1) a coupling candidate (as coupling_discovery would emit) becomes an intervention QUESTION
    reg = CD.CouplingRegistry()
    for f in range(6):
        reg.observe({"A"}, {"C": 100}, {"C": set()}, context="c%d" % f, now=f)
    coupling = reg.proposals(min_frequency=3, min_contexts=2)[0]
    request = P.from_coupling(coupling)
    auth = P.authorize(request)

    # 2) the benchmark answers the question across the three worlds (shadow experiments only)
    bench = {k: r.verdict for k, r in B.run().items()}

    # 3) extended invariant: committed AetherPulse history is untouched by ALL experiments
    before = K.run(_make_world(), 24)[1]
    _ = B.run()                                            # run every shadow experiment again
    for w in B.WORLDS.values():
        init, dyn = w()
        query(P.make("A", "C"), dyn, init)                # more experiments
    after = K.run(_make_world(), 24)[1]

    return {"coupling": (coupling.source, coupling.target),
            "request_hypothesis": request.hypothesis, "authorized": auth.admitted,
            "bench": bench, "committed_history_identical": before == after}


if __name__ == "__main__":
    r = run()
    print("Intervention as a causal query protocol — reality stays put\n")
    print("  coupling candidate (persistent ghost):", r["coupling"])
    print("  intervention request:", r["request_hypothesis"], " authorized:", r["authorized"])
    print("  benchmark verdicts:", r["bench"])
    print("  committed AetherPulse history identical across ALL experiments:", r["committed_history_identical"])
    print("\n  => the model asked questions and gained evidence; the territory (committed hash) never changed.")
    print("     causal_information -> experiment ALLOWED (airlock, shadow-only) ; -> truth FORBIDDEN")
