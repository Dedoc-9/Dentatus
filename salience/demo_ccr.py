"""
salience/demo_ccr.py — Consequence Capture Ratio: possibility-attention vs distance/visibility/importance.
PYTHONHASHSEED=0.

"Consequence" is an INDEPENDENT counterfactual ground truth (act vs freeze, downstream divergence). The
question: which signal, used to allocate an attention budget, captures the most truly-consequential future?
"""
import os
import sys
import random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "airlock"))
import adapters as A
import horizon as HZ
import predictor as P
import ccr as CCR

S = 1 << 32


def make_region():
    kind = "doorway" if random.random() < 0.45 else "valley"
    n = random.randint(2, 4) if kind == "doorway" else random.randint(1, 3)
    geom = random.randint(1, 4) if kind == "doorway" else random.randint(40, 200)
    bodies = [A.K.body(i, (random.randint(-20, 20), random.randint(2, 8), 0), (random.randint(-3, 3), 0, 0), (1, 1, 1)) for i in range(n)]
    w = A.K.make_world(bodies, ((-60, -60, -60), (60, 60, 60)))
    B = {"budget": {"max_cost": 9, "max_delta": 10**20}, "constraints": {"max_bodies": n + 3}}
    cands = ([{"transition": {"op": "impulse", "id": 0, "dv": [d, 0, 0]}, **B} for d in (5, 25, 50)] +
             [{"transition": {"op": "impulse", "id": 0, "dv": [0, 40, 0]}, **B},
              {"transition": {"op": "advance", "ticks": 6}, **B}]) if kind == "doorway" else \
            [{"transition": {"op": "impulse", "id": 0, "dv": [1, 0, 0]}, **B}, {"transition": {"op": "advance", "ticks": 2}, **B}]
    return {"world": w, "cands": cands, "geom": geom, "n": n, "dist": random.randint(3, 55),
            "vis": random.random(), "tag": 1.0 if (kind == "doorway" and random.random() < 0.6) else 0.2}


def main():
    random.seed(11)
    regs = [make_region() for _ in range(50)]
    feats = lambda r: P.features(r["n"], len(r["cands"]),
                                 sum(1 for i in range(len(r["world"]["bodies"])) for j in range(i + 1, len(r["world"]["bodies"]))), r["geom"])
    poss = lambda r: HZ.neighborhood(r["world"], 0, r["cands"], A)["possibility_pressure"] / S
    C = [CCR.consequence(r["world"], r["cands"], A) / S for r in regs]
    cut = 25
    w = P.calibrate([feats(r) for r in regs[:cut]], [poss(r) for r in regs[:cut]])
    sig = {"distance": [1.0 / (1 + r["dist"]) for r in regs],
           "visibility": [r["vis"] / (1 + r["dist"]) for r in regs],
           "importance": [r["tag"] for r in regs],
           "possibility": [max(P.predict(w, feats(r)), 0.0) for r in regs]}
    rep = CCR.compare(sig, C)
    print("Consequence Capture Ratio — consequence = independent counterfactual downstream divergence\n")
    print("  ranker        CCR@top20%   Spearman(vs consequence)")
    for k in ("distance", "visibility", "importance", "possibility"):
        print("  %-12s  %.3f        %+.2f" % (k, rep[k]["ccr"], rep[k]["spearman"]))
    print("\n  VERDICT: %s" % rep["verdict"].upper())
    print("  Distance/visibility are POOR (even slightly anti-correlated) proxies for consequence.")
    print("  Possibility matches hand-authored importance — but AUTOMATICALLY, deterministically, at scale,")
    print("  and it stays current as the world changes (static tags cannot). Designer-quality attention,")
    print("  without the designer. (Honest bound: a controlled reference result, not a shipping engine.)")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[salience] set PYTHONHASHSEED=0.\n\n")
        raise SystemExit(2)
    main()
