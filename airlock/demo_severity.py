"""
airlock/demo_severity.py — the toggleable severity layer. PYTHONHASHSEED=0.

One engine, two use modes: a fast game tier (cheap inline integrity) and a strict/relativistic tier (heavy
causal checks), with an offline physics court for game-tier commits. Severity gates the validator, never the
kernel.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import membrane as M
import adapters as A

S = 1 << 32


def main():
    W = A.K.make_world([A.K.body(0, (0, 5, 0), (0, 0, 0), (1, 1, 1))], ((-1000, -1000, -1000), (1000, 1000, 1000)))
    cons = {"max_bodies": 4, "c_limit": 5 * S}   # declared light-speed analog: 5 units/tick
    superluminal = {"transition": {"op": "impulse", "id": 0, "dv": [99, 0, 0]},
                    "budget": {"max_cost": 5, "max_delta": 10**22}, "constraints": cons}

    print("Proposal: a 99 units/tick impulse, against a declared c_limit of 5 units/tick.\n")
    rg = M.propose(W, dict(superluminal), A, severity="game")
    print("  game tier   -> %s  (strict deferred: %s) — fast path admits it" % (rg["gate"], rg["telemetry"]["deferred"]))
    rs = M.propose(W, dict(superluminal), A, severity="strict")
    print("  strict tier -> %s  (%s) — causal gate blocks inline" % (rs["gate"], rs.get("reason", "")))
    v = M.audit(W, superluminal["transition"], A, constraints=cons, commit_hash=rg["shard"]["shard_hash"])
    print("  physics court (offline audit of the game commit) -> %s: %s" % (v["verdict"], v["reason"]))

    lawful = {"transition": {"op": "impulse", "id": 0, "dv": [2, 0, 0]},
              "budget": {"max_cost": 5, "max_delta": 10**22}, "constraints": cons}
    pg = M.propose(W, dict(lawful), A, severity="game")["shard"]["post_hash"]
    ps = M.propose(W, dict(lawful), A, severity="strict")["shard"]["post_hash"]
    print("\n  lawful transition: game post_hash == strict post_hash -> %s" % (pg == ps))
    print("  => severity changes ADMISSIBILITY, never the deterministic kernel output. Fidelity is orthogonal.")
    print("\nOne engine: game speed with cheap integrity, OR relativistic severity offline. Severity declared + hashed.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[airlock] set PYTHONHASHSEED=0.\n\n")
        raise SystemExit(2)
    main()
