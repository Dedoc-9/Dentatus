"""
forge/chaos_harness.py — EXP-529 Network Chaos-Injection Harness.

Adversarial test of the L1 commit boundary under worst-case mobile transport. A deterministic L1 reducer
(tick-batched NET superposition -> seal H -> EXP-528 nonce) is fed through a seeded chaos transport that
drops, reorders, and delays intents. The harness proves the ONE invariant that matters:

    The committed H_verified timeline is a PURE FUNCTION of the accepted-intent set and the server-assigned
    sequence — independent of arrival order, jitter, or latency. Transport sabotage cannot fork reality.

Why this holds (and is provable, not asserted):
  * WITHIN a tick, resolution is NET superposition (Σ shear − Σ anneal applied once) -> order-independent;
    an `anneal` arriving before the `shear` that "caused" it changes nothing, because the tick commits the
    sum, not a sequence.
  * ACROSS ticks, each intent commits into its SERVER-assigned tick (by seq), never its arrival slot; the
    reducer commits ticks in seq order. Arrival jitter only delays when a tick closes, not its membership.
  * The bounded rebase window W is the hard fence: an intent arriving > W ticks late is REJECTED
    (stale_basis) — deterministically, never spliced into deep history (re-proving is bounded, not free).
    Beyond-window rejection is a feature, not a cold-restore miracle.

Honest scope: this is NOT "zero-latency re-prove the whole timeline." It is bounded-window order-invariance
+ deterministic stale-rejection. That is the real, defensible robustness property.

Deterministic (fixed seed). Run:  python3 forge/chaos_harness.py [N_TICKS]
"""
import os, sys, hashlib, random
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
for p in (REPO, os.path.join(REPO, "game/observability")):
    if p not in sys.path: sys.path.insert(0, p)
import composite_witness as W

CHI0, CHI_MIN, CHI_MAX = 0.25, 0.05, 1.0
ANNEAL_BASE = 0.06
REBASE_WINDOW = 3          # ticks; an intent later than its commit-tick + W is rejected (stale_basis)
N_TILES = 12


# ── canonical intent stream: each intent is (tick, iid, player, kind, tile, wi) ───────────────────────
def make_stream(n_ticks, seed=528529):
    rng = random.Random(seed); intents = []; iid = 0
    for t in range(n_ticks):
        for _ in range(rng.randint(1, 4)):
            player = rng.choice("AB"); kind = rng.choice(["shear", "shear", "anneal"])
            tile = rng.randrange(N_TILES); wi = round(rng.uniform(0.05, 0.14), 4)
            intents.append({"tick": t, "iid": iid, "player": player, "kind": kind, "tile": tile, "wi": wi}); iid += 1
    return intents


# ── deterministic L1 reducer: commit accepted intents tick-by-tick (NET superposition) ────────────────
def reduce_l1(accepted, n_ticks, session="chaos"):
    chi = [CHI0] * N_TILES; H = "%016x" % 0; chain = []; nc = W.NonceChain(session)
    by_tick = {}
    for it in accepted:
        by_tick.setdefault(it["tick"], []).append(it)
    for t in range(n_ticks):
        net = [0.0] * N_TILES
        for it in by_tick.get(t, []):                       # NET superposition: order within tick irrelevant
            net[it["tile"]] += (it["wi"] if it["kind"] == "shear" else -ANNEAL_BASE)
        for k in range(N_TILES):
            if net[k] != 0.0:
                chi[k] = min(CHI_MAX, max(CHI_MIN, chi[k] + net[k]))
        body = "|".join("%.6f" % c for c in chi)
        H = hashlib.sha256(("%s\x1f%s\x1f%d" % (H, body, t)).encode()).hexdigest()[:16]
        seq, nonce = nc.issue(H)
        chain.append((t, H, seq, nonce))
    return chain


# ── chaos transport: drop / reorder / delay, then apply the bounded-rebase accept rule ────────────────
def chaos_transport(intents, mode, seed):
    rng = random.Random(seed)
    p_drop = {"drop": 0.30, "storm": 0.30}.get(mode, 0.0)
    arrivals = []
    for it in intents:
        if rng.random() < p_drop:                           # DROP-CASCADE
            continue
        delay = 0
        if mode in ("jitter", "storm"):
            delay = rng.randint(0, REBASE_WINDOW)            # JITTER: within the rebase window
        if mode in ("latency", "storm") and rng.random() < 0.15:
            delay = REBASE_WINDOW + rng.randint(1, 4)        # LATENCY-SPIKE: blow past the window
        arrivals.append(dict(it, arrival=it["tick"] + delay))
    rng.shuffle(arrivals)                                    # JITTER-REORDER: scramble arrival order
    accepted, stale = [], 0
    for it in arrivals:
        if it["arrival"] <= it["tick"] + REBASE_WINDOW:      # bounded-rebase accept rule (server-assigned tick)
            accepted.append(it)
        else:
            stale += 1                                       # stale_basis -> rejected, never spliced
    return accepted, stale, len(intents) - len(arrivals)     # accepted, stale_rejected, dropped


def run(n_ticks=200):
    intents = make_stream(n_ticks)
    canon = reduce_l1(intents, n_ticks)                      # ground truth: in-order, lossless
    fails = []

    # P1 — ARRIVAL-ORDER INVARIANCE: jitter+reorder within window, NO drops -> bit-identical timeline
    for s in range(40):
        acc, stale, drop = chaos_transport(intents, "jitter", seed=1000 + s)
        if drop or stale:  # jitter mode keeps all within window
            fails.append(("jitter.lossy", s, "unexpected drop/stale in pure-jitter mode"))
        if reduce_l1(acc, n_ticks) != canon:
            fails.append(("order_invariance", s, "jittered/reordered timeline != canonical"))

    # P2 — DETERMINISM: identical seed -> identical committed chain (every mode)
    for mode in ("drop", "latency", "storm"):
        a = reduce_l1(chaos_transport(intents, mode, seed=77)[0], n_ticks)
        b = reduce_l1(chaos_transport(intents, mode, seed=77)[0], n_ticks)
        if a != b:
            fails.append(("determinism", mode, "same-seed chaos diverged"))

    # P3 — BOUNDED-REBASE REJECTION: latency spikes -> deterministic stale count; accepted-subset is the
    #      exact reduction over that subset (no corruption from the rejected late frames)
    acc, stale, drop = chaos_transport(intents, "latency", seed=9)
    sub_canon = reduce_l1(sorted(acc, key=lambda x: (x["tick"], x["iid"])), n_ticks)
    if reduce_l1(acc, n_ticks) != sub_canon:
        fails.append(("rebase.subset", 0, "accepted-subset timeline depends on arrival order"))
    stale2 = chaos_transport(intents, "latency", seed=9)[1]
    if stale != stale2:
        fails.append(("rebase.stale_nondeterministic", 0, "stale count not reproducible"))

    # P4 — DROP RESILIENCE: 30% drop -> deterministic over the survivor set; survivors == canonical-on-survivors
    acc, stale, drop = chaos_transport(intents, "drop", seed=3)
    surv_ids = {it["iid"] for it in acc}
    canon_surv = reduce_l1([it for it in intents if it["iid"] in surv_ids], n_ticks)
    if reduce_l1(acc, n_ticks) != canon_surv:
        fails.append(("drop.order", 0, "survivor timeline depends on arrival order"))

    # P5 — LIVENESS: the worst-case storm never raises / never hangs (bounded work), server thread free
    liveness_ok = True
    try:
        for s in range(60):
            chaos_transport(intents, "storm", seed=5000 + s)
            reduce_l1(chaos_transport(intents, "storm", seed=5000 + s)[0], n_ticks)
    except Exception as e:
        liveness_ok = False; fails.append(("liveness", 0, "storm raised: %r" % e))

    # report stats from one representative storm
    sacc, sstale, sdrop = chaos_transport(intents, "storm", seed=42)
    return {"n_ticks": n_ticks, "n_intents": len(intents), "fails": fails,
            "storm_dropped": sdrop, "storm_stale_rejected": sstale, "storm_accepted": len(sacc),
            "liveness": liveness_ok}


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    r = run(n)
    P = lambda key: "PASS" if not any(key in f[0] for f in r["fails"]) else "FAIL"
    print("EXP-529 · Network Chaos-Injection Harness  (%d ticks, %d intents)" % (r["n_ticks"], r["n_intents"]))
    print("  representative storm: dropped %d · stale-rejected %d · committed %d"
          % (r["storm_dropped"], r["storm_stale_rejected"], r["storm_accepted"]))
    print("  P1 arrival-order invariance (jitter/reorder == canonical) ..", P("order_invariance"))
    print("  P2 chaos determinism (same seed -> same H-chain) ...........", P("determinism"))
    print("  P3 bounded-rebase rejection (stale deterministic, subset OK)", "PASS" if not any('rebase' in f[0] for f in r['fails']) else "FAIL")
    print("  P4 drop-cascade resilience (survivor timeline canonical) ...", P("drop"))
    print("  P5 liveness under storm (no lock / no raise) ...............", "PASS" if r["liveness"] else "FAIL")
    print("  VIOLATIONS:", len(r["fails"]))
    for f in r["fails"][:12]: print("   !", f)
    sys.exit(1 if r["fails"] else 0)
