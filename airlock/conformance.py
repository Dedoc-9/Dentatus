"""
airlock/conformance.py — portable conformance vectors for the membrane.

Binds (adapter, world0, [proposals]) to the membrane's deterministic outcome: the per-proposal gate verdicts
and the resulting commit-ledger head (a hash chain over every committed transition). A different
implementation (a native port, another language, a re-host) is membrane-conformant for that vector iff it
reproduces the same gate sequence AND the same ledger head — bit-for-bit. This is what makes the airlock a
PROTOCOL, not a single program.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import membrane as M

SCHEMA = "airlock-conformance/1"


def run_sequence(adapter, world0, proposals, budget=None, constraints=None):
    """Feed a proposal sequence through the membrane, advancing the world on each commit. Returns the
    Ledger and the per-proposal gate verdicts (the deterministic decision trace)."""
    world = world0
    ledger = M.Ledger()
    gates = []
    for p in proposals:
        pp = dict(p)
        pp.setdefault("budget", budget or {})
        if constraints is not None:
            pp.setdefault("constraints", constraints)
        r = M.propose(world, pp, adapter, ledger=ledger)
        gates.append(r["gate"])
        if r["ok"]:
            world = r["world"]
    return world, ledger, gates


def make_vector(name, adapter, world0, proposals, budget=None, constraints=None):
    world, ledger, gates = run_sequence(adapter, world0, proposals, budget, constraints)
    return {"schema": SCHEMA, "name": name, "world0": world0, "proposals": proposals,
            "budget": budget or {}, "constraints": constraints or {},
            "gates": gates, "ledger_head": ledger.head(),
            "final_world_hash": adapter.state_hash(world),
            "n_commits": len(ledger.commits), "n_rejections": len(ledger.rejections)}


def verify_vector(vector, adapter):
    """Replay the vector against `adapter`; return (ok, detail). Conformant iff gates + ledger head + final
    world hash all reproduce."""
    world, ledger, gates = run_sequence(adapter, vector["world0"], vector["proposals"],
                                        vector["budget"], vector["constraints"] or None)
    if gates != vector["gates"]:
        return False, "gate sequence diverged at %d" % next(i for i in range(len(gates)) if i >= len(vector["gates"]) or gates[i] != vector["gates"][i])
    if ledger.head() != vector["ledger_head"]:
        return False, "ledger head mismatch"
    if adapter.state_hash(world) != vector["final_world_hash"]:
        return False, "final world hash mismatch"
    return True, "conformant"
