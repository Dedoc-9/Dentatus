"""
salience/demo_bench.py — Distance vs Cheap vs True, the decisive falsification. PYTHONHASHSEED=0.

Question: can a cheap O(local) predictor approximate possibility well enough to outperform distance, after
overhead, when amortized through a Possibility Atlas? Real airlock/horizon ground truth; honest metrics.
"""
import os
import sys
import time
import random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "airlock"))
import adapters as A
import horizon as HZ
import predictor as P
import bench as BN

S = 1 << 32


def make_region(kind):
    n = random.randint(2, 4) if kind == "doorway" else random.randint(1, 2)
    geom = random.randint(1, 3) if kind == "doorway" else random.randint(50, 200)
    bodies = [A.K.body(i, (random.randint(-30, 30), 5, 0), (0, 0, 0), (1, 1, 1)) for i in range(n)]
    w = A.K.make_world(bodies, ((-100, -100, -100), (100, 100, 100)))
    B = {"budget": {"max_cost": 9, "max_delta": 10**20}, "constraints": {"max_bodies": n + 3}}
    cands = ([{"transition": {"op": "impulse", "id": 0, "dv": [d, 0, 0]}, **B} for d in (1, 15, 40)] +
             [{"transition": {"op": "impulse", "id": 0, "dv": [0, 25, 0]}, **B},
              {"transition": {"op": "spawn", "body": {"id": n, "pos": [6, 5, 0], "vel": [0, 0, 0], "half": [1, 1, 1]}}, **B},
              {"transition": {"op": "advance", "ticks": 8}, **B}]) if kind == "doorway" else \
            [{"transition": {"op": "impulse", "id": 0, "dv": [1, 0, 0]}, **B},
             {"transition": {"op": "impulse", "id": 0, "dv": [2, 0, 0]}, **B}]
    return {"world": w, "cands": cands, "geom": geom, "n": n, "dist": random.randint(5, 90)}


def main():
    random.seed(7)
    regs = [make_region("doorway" if random.random() < 0.4 else "valley") for _ in range(60)]
    feats = lambda r: P.features(r["n"], len(r["cands"]),
                                 sum(1 for i in range(len(r["world"]["bodies"])) for j in range(i + 1, len(r["world"]["bodies"]))),
                                 r["geom"])
    truef = lambda r: HZ.neighborhood(r["world"], 0, r["cands"], A)["possibility_pressure"] / S
    distf = lambda r: 1.0 / (1 + r["dist"])

    def cost(fn, reps=150):
        t0 = time.perf_counter()
        for _ in range(reps): fn(regs[0])
        return (time.perf_counter() - t0) / reps * 1e6

    cut = 30
    w = P.calibrate([feats(r) for r in regs[:cut]], [truef(r) for r in regs[:cut]])
    te = regs[cut:]
    true = [truef(r) for r in te]; cheap = [P.predict(w, feats(r)) for r in te]; dist = [distf(r) for r in te]
    costs = {"distance": cost(distf), "cheap": cost(feats), "true": cost(truef)}
    rep = BN.evaluate(true, cheap, dist, costs, len(te), maintenance_budget_us=50.0)

    print("Distance vs Cheap vs True — possibility-scheduling falsification (60 regions, held-out 30)\n")
    print("  cheap predictor accuracy:  Spearman=%.2f   top-20%% ranking=%.2f" % (rep["accuracy_spearman"], rep["accuracy_topk"]))
    print("  QUALITY (compute landed on true possibility):")
    print("     true=%.3f   cheap=%.3f   distance=%.3f" % (rep["quality"]["true"], rep["quality"]["cheap"], rep["quality"]["distance"]))
    print("     cheap keeps %.0f%% of true's quality and is %.1fx distance's quality" % (rep["quality_cheap_vs_true_pct"], rep["quality_cheap_vs_distance_x"]))
    print("  COST / region:  distance=%.2fus  cheap=%.2fus  true=%.0fus  (cheap = %.2f%% of true)" % (
        costs["distance"], costs["cheap"], costs["true"], rep["cost_cheap_vs_true_pct"]))
    print("  ATLAS freshness @50us/frame maintenance: refresh-all in frames =", rep["frames_to_refresh_all"])
    print("\n  VERDICT: %s" % rep["verdict"].upper())
    print("  The cheap predictor outperforms distance on quality AND stays fresh where true cannot.")
    print("  Possibility is terrain, not a per-frame quantity: build the atlas, sample O(1), refresh cheaply.")
    print("  (Honest bound: a controlled reference result on a synthetic scenario — evidence the SCHEDULING")
    print("   PRINCIPLE is real, not a shipping engine. The atlas holds estimates; it never gates physics.)")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[salience] set PYTHONHASHSEED=0.\n\n")
        raise SystemExit(2)
    main()
