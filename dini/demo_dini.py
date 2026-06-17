"""
dini/demo_dini.py — the hyperbolic novelty compass as a live agent SENSOR.

Run:  PYTHONHASHSEED=0 python3 demo_dini.py

An agent navigates a small codebase tree. `dini/` reads the hyperbolic distance of each state it reaches.
Three agent uses, then a chronicle-sealed loop proving the reading is a *captured observable* (recorded +
replayable), never a gate.

  A. NOVELTY COMPASS     — flat distance => stuck on the happy path; growth => diving into new branches.
  B. DRIFT / ANOMALY     — a deep aberrant nested loop spikes distance past a PINNED threshold; the agent
                           treats it as a topological anomaly and chooses to roll back to the last stable hash.
  C. NAVIGATION          — compact [x,y] coordinates encode the hierarchy without dumping raw maps.
  D. SEALED AGENT LOOP    — each step is recorded with `dini_distance` captured; the Replay Court reproduces
                           the loop bit-for-bit. The sensor never gates a commit.

Honest scope: a sensor, not a safety mechanism. An anomaly flag CORRELATES with drift; it does not prove
hallucination. dini_distance is a captured float, never in the commit hash. Integrity != truth.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compass as D
import core
from court import verify_chain, print_verdict
from signing import HmacSigner

THRESHOLD = 6.0   # operator-PINNED anomaly threshold (a heuristic, not a guarantee)


def descend(state, child):
    """Pure transition: move the agent one directory deeper."""
    return {"path": list(state["path"]) + [child]}


def agent_logic(inputs):
    """Records the step; reads the captured dini observable (never recomputed on replay)."""
    return {"path": inputs["path"], "dini_distance": inputs["_cap"]["dini_distance"],
            "depth": inputs["_cap"]["depth"]}


def no_gate(inputs, outputs):
    return True   # the compass is a SENSOR; it does not gate commits


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("[dini] run with PYTHONHASHSEED=0\n"); raise SystemExit(2)

    m = D.HyperbolicMap(edge_length=1.0)
    root = {"path": ["repo"]}
    m.set_root(root)

    print("A) NOVELTY COMPASS:")
    eng = descend(root, "engine")
    o1 = m.observe(root, eng)                                  # first visit: novel
    o2 = m.observe(root, eng)                                  # REVISIT same state: flat, not novel
    print("   first visit  repo/engine        depth=%d dini=%.3f novelty=%s" % (o1["depth"], o1["dini_distance"], o1["novelty"]))
    print("   revisit      repo/engine        depth=%d dini=%.3f novelty=%s  <- flat: agent is on the happy path"
          % (o2["depth"], o2["dini_distance"], o2["novelty"]))
    print("   now dive into NEW branches -> distance grows (agent is exploring):")
    s = eng
    for child in ["kernel", "scheduler"]:
        nxt = descend(s, child); o = m.observe(s, nxt)
        print("     -> %-26s depth=%d dini=%.3f novelty=%s" % ("/".join(nxt["path"]), o["depth"], o["dini_distance"], o["novelty"]))
        s = nxt

    print("\nB) DRIFT / ANOMALY (pinned threshold = %.1f):" % THRESHOLD)
    s = root; stable_hash = core.state_hash(root); stable_path = list(root["path"])
    for child in ["a", "b", "c", "d", "e", "f", "g"]:     # an aberrant deep nested loop
        nxt = descend(s, child); o = m.observe(s, nxt)
        flagged = D.anomaly(o, THRESHOLD)
        print("     depth=%d dini=%.3f %s" % (o["depth"], o["dini_distance"], "<-- ANOMALY" if flagged else ""))
        if flagged:
            print("     agent decision: topologically anomalous; ROLLING BACK to last stable hash %s (/%s)"
                  % (stable_hash[:10], "/".join(stable_path)))
            break
        s = nxt; stable_hash = core.state_hash(s); stable_path = list(s["path"])

    print("\nC) NAVIGATION (compact coordinates instead of raw maps):")
    for label, st in [("repo", root), ("repo/engine", descend(root, "engine")),
                      ("repo/engine/kernel", descend(descend(root, "engine"), "kernel"))]:
        h = core.state_hash(st)
        if h in m.coord:
            z = m.coord[h]; print("     %-22s -> (%.3f, %.3f)  depth=%d" % (label, z.real, z.imag, m.depth[h]))

    print("\nD) SEALED AGENT LOOP (dini captured into the ledger; replays bit-for-bit):")
    rec = core.Recorder(HmacSigner(b"agent"), core.ruleset_hash(agent_logic, no_gate))
    ledger = []; s = root; m2 = D.HyperbolicMap(edge_length=1.0); m2.set_root(root)
    for i, child in enumerate(["engine", "kernel", "scheduler"]):
        nxt = descend(s, child); obs = m2.observe(s, nxt)
        sealed = {"path": nxt["path"], "_cap": {"dini_distance": obs["dini_distance"], "depth": obs["depth"]}}
        ledger.append(rec.record("NAV-%d" % i, sealed, agent_logic(sealed), no_gate)); s = nxt
    print_verdict(verify_chain(ledger, b"agent", agent_logic, no_gate), len(ledger))

    print("\n   NOTE: a SENSOR, not a gate. Anomaly != hallucination; dini is a captured float, never hashed.")
    print("   Integrity != truth — a novelty compass points, it does not guarantee.")
