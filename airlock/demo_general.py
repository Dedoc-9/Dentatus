"""
airlock/demo_general.py — one membrane, two realities. PYTHONHASHSEED=0.

Physics (AetherPulse bodies) and config/repo state (KV) cross the IDENTICAL `membrane.propose` pipeline.
The airlock is the general reality-transition membrane; the world is just whichever adapter is plugged in.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import membrane as M
import adapters as PHYS
import adapters_kv as KV
import contract
import conformance as CF


def run(label, adapter, world0, seq, budget, constraints):
    print("== %s ==" % label)
    print("   adapter satisfies contract:", contract.validate_adapter(adapter))
    W, L = world0, M.Ledger()
    for txn in seq:
        r = M.propose(W, {"transition": txn, "budget": budget, "constraints": constraints,
                          "provenance": {"who": "proposer"}}, adapter, ledger=L)
        if r["ok"]:
            W = r["world"]
        print("   %-44s -> %s%s" % (str(txn)[:44], r["gate"], "" if r["ok"] else " (rejected)"))
    v = CF.make_vector(label, adapter, world0, [{"transition": t} for t in seq], budget, constraints)
    print("   ledger head: %s  commits=%d rejections=%d  conformance=%s\n"
          % (L.head()[:12], len(L.commits), len(L.rejections), CF.verify_vector(v, adapter)[0]))


def main():
    PW = PHYS.K.make_world([PHYS.K.body(0, (0, 5, 0), (0, 0, 0), (1, 1, 1))], ((-10, -10, -10), (10, 10, 10)))
    run("REALITY A — physics (AetherPulse)", PHYS, PW,
        [{"op": "impulse", "id": 0, "dv": [2, 0, 0]}, {"op": "advance", "ticks": 4},
         {"op": "impulse", "id": 0, "dv": [0.5, 0, 0]}],
        {"max_cost": 10, "max_delta": 10**15}, {"max_bodies": 4})
    run("REALITY B — config / repo state (KV)", KV, KV.empty_world(),
        [{"op": "set", "key": "replicas", "value": 3}, {"op": "bump", "key": "replicas", "by": 2},
         {"op": "freeze", "key": "replicas"}, {"op": "set", "key": "replicas", "value": 9}],
        {"max_cost": 5, "max_delta": 10**9}, {"max_keys": 4})
    print("Same membrane, same two laws (telemetry != control, intent != authority), two realities.")
    print("Different proposers (LLM, agent, human) and different worlds — one transition protocol.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[airlock] set PYTHONHASHSEED=0.\n\n")
        raise SystemExit(2)
    main()
