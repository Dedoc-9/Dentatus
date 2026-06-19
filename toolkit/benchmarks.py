"""
toolkit.benchmarks — honest scenarios. Each can FAIL the toolkit; that is the point.

Core three (signal quality):
  informative  : signals are noisy views of truth        -> future_surface WINS
  drift        : signals are pure noise                   -> future_surface LOSES to the floor
  adversarial  : signals are confidently MISLEADING       -> future_surface LOSES to the floor

Hardening five (the doors that keep this from becoming an "AI finds importance" claim):
  unknown_unknown : finds a low-consequence/high-M item ONLY if uncertainty/possibility encode it
                    -> attention != discovery
  calibration     : which aggregation (product vs min_gate) wins depends on how M composes
                    -> the aggregation assumption is load-bearing, not universal
  budget_curve    : sweep scarcity instead of trusting one budget
                    -> "better under CONSTRAINED resources", made precise
  coherence       : a stale allocation loses to a fresh floor past a horizon
                    -> attention requires coherence time
  fairness        : a top-score but ineligible item gets ZERO budget
                    -> importance != eligibility

Deterministic: integer math, ties by id, stdlib only.   Run:  PYTHONHASHSEED=0 python3 -m toolkit
"""
from __future__ import annotations
import random

from .attention import attention
from . import policies


# -- worlds ----------------------------------------------------------------------------------------

def make_world(n=60, seed=1):
    """Informative, product-structured. M = hidden t_cons*t_unc; observed signals are noisy views;
    magnitude is raw size (the butterfly: the biggest region is the most inert)."""
    rng = random.Random(seed)
    world = []
    for i in range(n):
        t_cons = rng.randint(1, 1000)
        t_unc = rng.randint(1, 1000)
        M = max(1, (t_cons * t_unc) // 1000)
        size = max(1, 1000 - t_cons + rng.randint(-40, 40))
        world.append({
            "id": "region_%02d" % i, "cost": rng.randint(20, 100),
            "consequence": max(1, t_cons + rng.randint(-80, 80)),
            "uncertainty": max(1, t_unc + rng.randint(-80, 80)),
            "possibility": rng.randint(300, 1000),
            "magnitude": size, "M": M,
        })
    return world


def make_drift_world(n=60, seed=1):
    """Estimate decoupled from truth: observed signals are pure noise. future_surface must lose."""
    rng = random.Random(seed)
    world = []
    for i in range(n):
        t_cons = rng.randint(1, 1000); t_unc = rng.randint(1, 1000)
        M = max(1, (t_cons * t_unc) // 1000)
        world.append({
            "id": "region_%02d" % i, "cost": rng.randint(20, 100),
            "consequence": rng.randint(1, 1000), "uncertainty": rng.randint(1, 1000),
            "possibility": rng.randint(1, 1000), "magnitude": max(1, 1000 - t_cons), "M": M,
        })
    return world


def make_adversarial_world(n=60, seed=1):
    """Confidently MISLEADING signals: high signal anti-correlates with true M (a loud fake_crisis,
    a silent quiet_cascade). future_surface must lose to the floor."""
    rng = random.Random(seed)
    world = [
        {"id": "fake_crisis", "cost": 50, "consequence": 1000, "uncertainty": 1000, "possibility": 1000,
         "magnitude": rng.randint(1, 1000), "M": 1},
        {"id": "quiet_cascade", "cost": 50, "consequence": 300, "uncertainty": 300, "possibility": 300,
         "magnitude": rng.randint(1, 1000), "M": 900},
    ]
    for i in range(n - 2):
        s = rng.randint(1, 1000)
        world.append({
            "id": "region_%02d" % i, "cost": rng.randint(20, 100),
            "consequence": s, "uncertainty": s, "possibility": s,
            "magnitude": rng.randint(1, 1000), "M": max(1, 1000 - s + rng.randint(-50, 50)),
        })
    return world


def make_unknown_world(n=60, seed=1, encoded=True):
    """A category the consequence channel cannot see: every item has LOW consequence, and true M is
    driven by a hidden variable. If uncertainty/possibility ENCODE that variable the field finds it;
    if they are noise the field CANNOT discover it. (attention != discovery)"""
    rng = random.Random(seed)
    world = []
    for i in range(n):
        hidden = rng.randint(1, 1000)
        if encoded:
            unc = max(1, hidden + rng.randint(-80, 80))
            pos = max(1, hidden + rng.randint(-80, 80))
        else:
            unc = rng.randint(1, 1000)
            pos = rng.randint(1, 1000)
        world.append({
            "id": "region_%02d" % i, "cost": rng.randint(20, 100),
            "consequence": rng.randint(1, 200), "uncertainty": unc, "possibility": pos,
            "magnitude": rng.randint(1, 1000), "M": hidden,
        })
    return world


def make_min_world(n=60, seed=1):
    """Min-structured importance: realized M is the WEAKEST true dimension, so min_gate should beat
    the product -- the aggregation choice is load-bearing."""
    rng = random.Random(seed)
    world = []
    for i in range(n):
        a, b, c = (rng.randint(1, 1000) for _ in range(3))
        M = min(a, b, c)
        world.append({
            "id": "region_%02d" % i, "cost": rng.randint(20, 100),
            "consequence": max(1, a + rng.randint(-60, 60)),
            "uncertainty": max(1, b + rng.randint(-60, 60)),
            "possibility": max(1, c + rng.randint(-60, 60)),
            "magnitude": rng.randint(1, 1000), "M": M,
        })
    return world


def make_drifting_world(n=60, seed=1, t=0):
    """Importance rotates among regions over time. A region active now is inert later; signals reflect
    the CURRENT tick. rng draw-count is independent of t, so ids/costs are stable across ticks."""
    rng = random.Random(seed)
    spec = [(rng.randint(0, 9), rng.randint(1, 1000), rng.randint(20, 100), rng.randint(1, 1000))
            for _ in range(n)]
    world = []
    for i, (phase, amp, cost, mag) in enumerate(spec):
        active = ((phase + t) % 10) < 3            # rotation period 10; test staleness < period
        M = amp if active else max(1, amp // 20)
        sig = 1000 if active else 100
        world.append({
            "id": "region_%02d" % i, "cost": cost,
            "consequence": sig, "uncertainty": sig, "possibility": sig,
            "magnitude": mag, "M": M,
        })
    return world


def make_fairness_world(n=20, seed=1):
    """A top-score item that is not eligible (e.g. not visible). It must receive zero budget."""
    rng = random.Random(seed)
    world = [{"id": "hidden_jackpot", "cost": 20, "consequence": 1000, "uncertainty": 1000,
              "possibility": 1000, "magnitude": 1000, "M": 1000, "eligible": False}]
    for i in range(n):
        world.append({
            "id": "region_%02d" % i, "cost": rng.randint(20, 100),
            "consequence": rng.randint(1, 1000), "uncertainty": rng.randint(1, 1000),
            "possibility": rng.randint(1, 1000), "magnitude": rng.randint(1, 1000),
            "M": rng.randint(1, 1000),
        })
    return world


def make_stale_world(n=60, seed=1, lag=5):
    """A single static world that encodes signal staleness: the observed signals are what a fresh field
    saw at t=0, but the objective M is the world as it has since drifted to t=lag. A policy that trusts
    the (now stale) signal is graded against a world that moved. (compare/robustness 'stale' regime)"""
    fresh = {o["id"]: o for o in make_drifting_world(n=n, seed=seed, t=0)}
    later = {o["id"]: o for o in make_drifting_world(n=n, seed=seed, t=lag)}
    world = []
    for k in fresh:
        o = dict(fresh[k])
        o["M"] = later[k]["M"]
        world.append(o)
    return world


def make_shifted_world(n=60, seed=1, shift=0):
    """Input distribution shift: the consequence/uncertainty signal MEANS move by ~shift. This is an
    observable change of input domain -- a runtime monitor can detect it from signal statistics alone,
    with no truth oracle. (monitor 'drift' stream)"""
    rng = random.Random(seed)
    world = []
    for i in range(n):
        c = min(1000, rng.randint(1, 1000) + shift)
        u = min(1000, rng.randint(1, 1000) + shift)
        world.append({
            "id": "region_%02d" % i, "cost": rng.randint(20, 100),
            "consequence": c, "uncertainty": u, "possibility": rng.randint(300, 1000),
            "magnitude": rng.randint(1, 1000), "M": max(1, (c * u) // 1000),
        })
    return world


# -- graders ---------------------------------------------------------------------------------------

def grade(world, budget=1000):
    """Standard policies (default future_surface field carries magnitude/uniform/M columns)."""
    field = attention.observe(world)
    return {p: field.allocate(budget, policy=p).captured("M")
            for p in ("future_surface", "magnitude", "uniform", "M")}


def grade_by(world, budget, scorers):
    """Grade by arbitrary scorers (observe once per scorer so each named column exists). +oracle/floor."""
    out = {}
    for fn in scorers:
        out[fn.__name__] = attention.observe(world, scorer=fn).allocate(budget).captured("M")
    base = attention.observe(world)
    out["uniform"] = base.allocate(budget, policy="uniform").captured("M")
    out["M"] = base.allocate(budget, policy="M").captured("M")
    return out


def _pct(x, whole):
    return (100 * x) // max(1, whole)


# -- the proof -------------------------------------------------------------------------------------

def run(budget=1000):
    inf = grade(make_world(), budget)
    dft = grade(make_drift_world(), budget)
    adv = grade(make_adversarial_world(), budget)

    print("=" * 78)
    print("toolkit -- deciding where limited resources go when you cannot attend to everything")
    print("=" * 78)
    print("\n[1] signal quality -- graded on a hidden, independent objective M (% of oracle):\n")
    print("  %-12s  %14s  %10s  %7s" % ("scenario", "future_surface", "magnitude", "floor"))
    for name, r in (("informative", inf), ("drift", dft), ("adversarial", adv)):
        o = r["M"]
        print("  %-12s  %13d%%  %9d%%  %6d%%"
              % (name, _pct(r["future_surface"], o), _pct(r["magnitude"], o), _pct(r["uniform"], o)))
    ratio = (100 * inf["future_surface"]) // max(1, inf["magnitude"])
    print("\n  measurable improvement (informative): %.2fx the consequence of size-based allocation"
          % (ratio / 100))
    print("  at identical budget; drift & adversarial both LOSE to the floor.")

    enc = grade(make_unknown_world(encoded=True), budget)
    nen = grade(make_unknown_world(encoded=False), budget)
    print("\n[2] attention != discovery -- a low-consequence/high-M category is found ONLY if encoded:")
    print("      encoded signal     : future_surface %d%% vs floor %d%%  -> found"
          % (_pct(enc["future_surface"], enc["M"]), _pct(enc["uniform"], enc["M"])))
    print("      uninformative signal: future_surface %d%% vs floor %d%%  -> NOT discovered"
          % (_pct(nen["future_surface"], nen["M"]), _pct(nen["uniform"], nen["M"])))

    prod = grade_by(make_world(), budget, (policies.future_surface, policies.min_gate, policies.weighted_product))
    mn = grade_by(make_min_world(), budget, (policies.future_surface, policies.min_gate, policies.weighted_product))
    print("\n[3] calibration -- the right aggregation depends on how M composes:")
    print("      product-structured M : product %d%%  >=  min_gate %d%%"
          % (_pct(prod["future_surface"], prod["M"]), _pct(prod["min_gate"], prod["M"])))
    print("      min-structured M     : min_gate %d%%  >=  product %d%%"
          % (_pct(mn["min_gate"], mn["M"]), _pct(mn["future_surface"], mn["M"])))

    bcurve = [(b, grade(make_world(), b)) for b in (100, 250, 500, 1000, 2000, 3000)]
    print("\n[4] budget curve -- future_surface vs magnitude vs floor (% oracle); advantage shrinks to abundance:")
    for b, r in bcurve:
        o = r["M"]
        print("      budget %5d: fs %3d%%   mag %3d%%   floor %3d%%"
              % (b, _pct(r["future_surface"], o), _pct(r["magnitude"], o), _pct(r["uniform"], o)))

    stale_chosen = attention.observe(make_drifting_world(t=0)).allocate(budget).chosen
    print("\n[5] coherence time -- an allocation decided at t=0, graded as the world drifts:")
    coh = {}
    for s in (0, 1, 3, 5):
        ws = {o["id"]: o for o in make_drifting_world(t=s)}
        stale = sum(ws[i]["M"] for i in stale_chosen)
        items = list(ws.values())
        floor = attention.observe(items).allocate(budget, policy="uniform").captured("M")
        oracle = attention.observe(items).allocate(budget, policy="M").captured("M")
        coh[s] = (stale, floor, oracle)
        print("      stale %2d ticks: stale-alloc %3d%%   fresh floor %3d%%"
              % (s, _pct(stale, oracle), _pct(floor, oracle)))

    fair = attention.observe(make_fairness_world()).allocate(budget)
    print("\n[6] importance != eligibility -- a top-score but ineligible item gets zero budget:")
    print("      hidden_jackpot funded: %s  (future_surface is top; eligible=False)"
          % ("hidden_jackpot" in fair.chosen))

    from .tournament import compare, robustness
    from .certify import certify, diff_certificates
    from .monitor import Monitor
    comp = compare([policies.future_surface, policies.weighted_product, policies.min_gate,
                    policies.magnitude, policies.random_priority], worlds=200)
    print("\n[7] policy competition -- avg captured M across 200 worlds (% of oracle):")
    print("\n".join("      " + ln for ln in comp.table().splitlines()))

    assert inf["future_surface"] > inf["magnitude"] and inf["future_surface"] > inf["uniform"], "informative must win"
    assert dft["future_surface"] <= dft["uniform"], "drift must lose to floor"
    assert adv["future_surface"] <= adv["uniform"], "adversarial must lose to floor"
    assert enc["future_surface"] > enc["uniform"], "encoded: must find the hidden-category item"
    assert nen["future_surface"] <= nen["uniform"], "uninformative: must NOT discover (attention != discovery)"
    assert prod["future_surface"] >= prod["min_gate"], "product world: product should win"
    assert mn["min_gate"] >= mn["future_surface"], "min world: min_gate should win (aggregation is load-bearing)"
    assert all(r["future_surface"] >= r["magnitude"] for _, r in bcurve), "future_surface must dominate magnitude across budgets"
    assert coh[0][0] > coh[0][1], "fresh allocation beats floor"
    assert coh[5][0] <= coh[5][1], "stale allocation loses to floor (finite coherence horizon)"
    assert "hidden_jackpot" not in fair.chosen, "ineligible item must get zero budget"
    assert comp.pct("future_surface") >= max(comp.pct(n) for n in ("min_gate", "magnitude", "random_priority")), \
        "future_surface should lead the non-oracle field"
    assert comp.pct("magnitude") < comp.pct("random_priority"), \
        "butterfly world: size is anti-informative -> magnitude loses even to random"
    rob = robustness([policies.future_surface, policies.magnitude, policies.random_priority], worlds=150)
    print("\n[8] policy robustness -- avg captured M (% oracle); a policy survives only where its")
    print("    assumptions hold (oracle=100% everywhere by definition):")
    print("\n".join("      " + ln for ln in rob.table().splitlines()))
    others = [r for r in rob.regime_names if r != "clean"]
    assert rob.pct("future_surface", "clean") >= max(rob.pct("magnitude", "clean"), rob.pct("random_priority", "clean")), \
        "future_surface should win the clean regime"
    assert any(rob.pct("future_surface", r) < max(rob.pct("magnitude", r), rob.pct("random_priority", r)) for r in others), \
        "future_surface must LOSE in at least one non-clean regime (wins when assumptions hold, not always)"

    cert = certify(policies.future_surface, worlds=120)
    def _oracle(item):              # a policy that reads the answer key -> must FAIL the no-hidden check
        return item["M"]
    cheat = certify(_oracle, worlds=40)
    print("\n[9] allocator certification -- a policy must declare assumptions + failure envelope:")
    print("\n".join("      " + ln for ln in cert.report().splitlines()))
    print("      -- the certifier catches a cheater: an M-reading policy fails 'no hidden objective' ->",
          "no_hidden =", cheat.no_hidden)

    assert cert.deterministic and cert.no_hidden and cert.eligibility, "future_surface must pass the honesty checks"
    assert any(r == "clean" for r, _, _ in cert.envelope), "future_surface must be certified in the clean regime"
    assert any(r == "adversarial" for r, _, _ in cert.failures), "future_surface must declare adversarial as a failure"
    assert cheat.no_hidden is False, "the certifier must catch a policy that reads the hidden objective M"

    base_cert = certify(policies.future_surface, worlds=80)
    legit_cert = certify(policies.weighted_product, worlds=80)
    def _oracle2(item):
        return item["M"]
    cheat_cert = certify(_oracle2, worlds=40)
    d_legit = diff_certificates(base_cert, legit_cert)
    d_cheat = diff_certificates(base_cert, cheat_cert)
    print("\n[10] certificate regression -- a change is judged by envelope + integrity, not by score:")
    print("\n".join("      " + ln for ln in d_cheat.report().splitlines()))
    print("      (the cheater scores higher in every regime, yet is REJECTED: integrity regressed.)")

    cd = base_cert.to_dict()
    assert "never a claim of correctness" in cd["scope"], "the certificate must never claim correctness"
    assert cd["claims"]["uses_hidden_objective"] is False, "future_surface must not use the hidden objective"
    assert d_cheat.integrity_regressed() is True and d_cheat.acceptable() is False, \
        "regression gate must REJECT a higher-scoring policy that cheats (reads M)"
    assert d_legit.acceptable() is True, "a legitimate policy change must not trip the integrity gate"

    m_clean = Monitor()
    for s in range(20, 30):
        m_clean.observe(make_world(seed=s))
    m_shift = Monitor()
    for sh in (0, 150, 300, 500, 700):
        m_shift.observe(make_shifted_world(seed=1, shift=sh))
    m_adv = Monitor()
    for s in range(1, 11):
        m_adv.observe(make_adversarial_world(seed=s))
    print("\n[11] runtime drift monitor -- a certificate must keep being earned after deployment:")
    print("      clean input stream      -> %s" % m_clean.report())
    print("      shifting input domain   -> %s" % m_shift.report())
    print("      adversarial stream      -> %s  (BLIND SPOT: signals look normal)" % m_adv.report())
    print("      => observable drift != semantic drift: the monitor catches a new input domain, but a")
    print("         confidently-misleading world is invisible to a marginal-distribution monitor.")

    assert m_clean.status == Monitor.CERTIFIED, "clean stream must stay certified"
    assert m_shift.status == Monitor.QUARANTINED, "a strong input-domain shift must quarantine the policy"
    assert m_adv.status == Monitor.CERTIFIED, "the monitor is BLIND to adversarial inversion (declared limitation)"

    print("\n[OK] all twenty-five properties hold. The toolkit allocates by supplied signal; it does not")
    print("     discover importance, and it loses whenever signal, freshness, or eligibility fails.")


if __name__ == "__main__":
    run()
