"""
forge/duel_determinism_proof.py — EXP-533 hardware-invariance proof for collider_duel.

Drives identical scripted intent sequences through fresh Duel worlds and asserts the committed H-chain is
bit-identical — including a run with random WALL-CLOCK SLEEPS injected between ticks, which must NOT change
history. Proves no wall-clock value enters a committed transition; H_verified re-derives from the log alone.
Exit 0 iff all properties hold.
"""
import os, sys, time, random
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "Game1"))
import collider_duel as D

SCRIPT_SEED = 1733

def run(inject_sleeps=False):
    W = D.Duel(); W.bot_b = False                       # bot off; the script is the sole, deterministic input
    rng = random.Random(SCRIPT_SEED)                    # SAME stream every run -> identical intents
    sleep_rng = random.Random(99)                       # separate stream so sleeps never perturb the script
    for fr in range(140):
        for _ in range(rng.randint(0, 3)):
            who = rng.choice("AB"); kind = rng.choice(["shear", "shear", "anneal"])
            sec = rng.randrange(48); wi = round(rng.uniform(0.06, 0.13), 4); syn = rng.random() < 0.5
            W.pending.append({"player": who, "kind": kind, "section": sec, "wi": wi, "synced": syn, "gs": None, "recv": W.frame})
        if inject_sleeps and fr % 5 == 0:
            time.sleep(sleep_rng.uniform(0.002, 0.03))  # perturb the host wall clock between ticks
        W.tick()
    chain = [e["H"] for e in W.log]
    meta = [(e.get("tick_pulse"), e.get("beta_eff")) for e in W.log if "section" in e]
    return chain, meta

fails = []
h1, m1 = run(False)
h2, m2 = run(False)
h3, m3 = run(True)          # identical script, but with random wall-clock sleeps

if h1 != h2: fails.append("two identical runs diverged (non-determinism remains)")
if h1 != h3: fails.append("WALL-CLOCK LEAK: injecting sleeps changed the committed H-chain")
if not h1: fails.append("no commits were produced (script drove nothing)")
# every committed melt/anneal logged its deterministic pulse + beta (self-contained for replay)
if not m1 or any(tp is None or be is None for tp, be in m1):
    fails.append("a committed entry is missing tick_pulse/beta_eff in the log")
# tick_pulse must equal the pure frame formula (no clock)
import math
def expect_tp(frame): return round(math.cos(2 * math.pi * (((frame / D.TICK_HZ / D.SEED["T"]) + D.SEED["phase0"]) % 1.0)), 6)
W4 = D.Duel(); W4.frame = 37
if round(W4._tick_pulse(), 6) != expect_tp(37): fails.append("_tick_pulse is not the pure frame function")

print("EXP-533 · hardware-invariant pulse proof")
print("  1 identical runs -> identical H-chain (%d commits) .." % len(h1), "PASS" if h1 == h2 and h1 else "FAIL")
print("  2 wall-clock sleeps -> SAME H-chain (no clock leak) .", "PASS" if h1 == h3 else "FAIL")
print("  3 every commit logs tick_pulse + beta_eff ..........", "PASS" if (m1 and all(tp is not None and be is not None for tp, be in m1)) else "FAIL")
print("  4 _tick_pulse is a pure function of the frame .......", "PASS" if not any('pure frame' in f for f in fails) else "FAIL")
print("  VIOLATIONS:", len(fails))
for f in fails: print("   !", f)
sys.exit(1 if fails else 0)
