"""
run_seed_exp310.py -- EXP-310 Causal Ghost seed test (Fork A).

Protocol: exp310-v1
declaration_hash: 767cd60f165a131d8ad738c2256c0654961d31a7e193d4bb1cc0318dcd9b3666

Tests:
  1. KSG ground truth: AR(1) Gaussian N=2000.
       a_t ~ N(0,1) iid; c_t = 0.5*a_{t-1} + N(0,1).
       True T_{a->c} = 0.5*ln(1.25) = 0.111572 nats.
       Verify: estimate within 15% of truth, T_{c->a} < T_{a->c}/2.
  2. Lossless engine degenerate: all ghost_history entries (0,0) -> T~0.
  3. Sign reliability at W=64: 10 independent trials of non-negative causal model
       a_t = chi2(2)/2 (Exp(1) iid); c_t = 0.7*a_{t-1} + Exp(1).
       delta_T_AC sign correct >= 7/10.
  4. dev note: KSG ghost_history stores signed floats for validation;
       production engine stores ||S_A||, ||S_C|| >= 0 via _update_ghost_history.
"""

import sys, json, hashlib, math
import numpy as np
from collections import deque
sys.path.insert(0, ".")

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.validity import kappa_integral

# ---------------------------------------------------------------------------
# Hash verify
# ---------------------------------------------------------------------------
with open("studies/exp310_causal_ghost/SEED_DECLARATION_exp310.json") as f:
    DECL = json.load(f)
stored = DECL["declaration_hash"]
fields = {k:v for k,v in DECL.items() if k not in ("declaration_hash","status")}
canonical = json.dumps(fields, sort_keys=True, separators=(',',':'))
assert hashlib.sha256(canonical.encode()).hexdigest() == stored
print(f"Seed hash verified: {stored[:16]}...")

def make_mu_bare():
    stalk = np.array([1.,1.,1.,1., 0.5,0.5,0.5,1., 0.,0.,1.,
                      kappa_integral((np.zeros(3), np.ones(3)))])
    prov  = Provenance(parent_ids=(), operator_id="EXP310", timestamp=now_iso())
    claim = Claim(provenance=prov, payload="310", stalk=stalk.copy(), t=0,
                  bbox=(np.zeros(3), np.ones(3)))
    mu = MuState(claims={claim.id: claim}, entailments={},
                 active=frozenset([claim.id]),
                 t=0, S=np.zeros(12), alpha=ALPHA, S_A=np.zeros(8), S_C=np.zeros(4))
    mu.seal()
    return mu

# ---------------------------------------------------------------------------
# Test 1 -- KSG ground truth: Gaussian AR(1) N=2000
# Dev note: synthetic test stores signed Gaussian values directly.
# Analytical TE = 0.5*ln(1+gamma^2) valid only for Gaussian inputs.
# Production engine stores non-negative norms; this test validates estimator only.
# ---------------------------------------------------------------------------
print("\n--- Test 1: KSG ground truth (Gaussian AR(1), N=2000) ---")

np.random.seed(42)
N_syn = 2000
a_syn = np.random.randn(N_syn)
c_syn = 0.5 * np.roll(a_syn, 1) + np.random.randn(N_syn)
a_syn = a_syn[2:]; c_syn = c_syn[2:]
true_TE = 0.5 * math.log(1.25)
print(f"  True T_{{a->c}} = 0.5*ln(1.25) = {true_TE:.6f} nats")

mu1 = make_mu_bare()
hist1 = deque(maxlen=2000)
for av, cv in zip(a_syn, c_syn):  # signed -- analytical formula valid
    hist1.append((float(av), float(cv)))
mu1.ghost_history = hist1

T_ac, T_ca, dT, Tn = mu1.te_observables(k=5)
print(f"  T_{{a->c}} = {T_ac:.6f}  err = {abs(T_ac - true_TE)/true_TE*100:.1f}%")
print(f"  T_{{c->a}} = {T_ca:.6f}  (true = 0)")
print(f"  delta_T_AC = {dT:.6f}  T_norm = {Tn:.4f}")
assert T_ac > T_ca, f"Sign wrong: T_ac={T_ac} <= T_ca={T_ca}"
assert abs(T_ac - true_TE) / true_TE < 0.15, f"Magnitude error > 15%: {abs(T_ac-true_TE)/true_TE*100:.1f}%"
assert T_ca < T_ac * 0.3, f"T_ca should be < 30% of T_ac"
print("  Sign correct, magnitude within 15%, T_{c->a} << T_{a->c}: PASS")

# ---------------------------------------------------------------------------
# Test 2 -- Lossless degenerate (all zeros)
# ---------------------------------------------------------------------------
print("\n--- Test 2: Lossless degenerate ghost_history (all zeros) ---")
mu2 = make_mu_bare()
hist2 = deque(maxlen=200)
for _ in range(200):
    hist2.append((0.0, 0.0))
mu2.ghost_history = hist2
T_ac2, T_ca2, dT2, _ = mu2.te_observables(k=5)
print(f"  T_{{a->c}} = {T_ac2:.6f}  T_{{c->a}} = {T_ca2:.6f}")
assert T_ac2 < 0.05 and T_ca2 < 0.05, f"Degenerate T not near zero: {T_ac2}, {T_ca2}"
print("  Degenerate T ~ 0: PASS")

# ---------------------------------------------------------------------------
# Test 3 -- Sign reliability at W=64, non-negative causal model
# Model: a_t = Exp(1) iid; c_t = 0.7*a_{t-1} + Exp(1)  (both non-negative)
# ghost_history stores actual non-negative values (production-realistic).
# No closed-form TE for Exp; rely on directional test only.
# ---------------------------------------------------------------------------
print("\n--- Test 3: Sign reliability (non-negative Exp model, W=64, 10 trials) ---")
correct = 0
for seed in range(10):
    np.random.seed(seed * 31 + 7)
    N_w = 66
    a_w = np.random.exponential(1.0, N_w)
    c_w = 0.7 * np.roll(a_w, 1) + np.random.exponential(1.0, N_w)
    a_w = a_w[2:]; c_w = c_w[2:]  # discard roll artifact
    mu_w = make_mu_bare()
    hist_w = deque(maxlen=N_w)
    for av, cv in zip(a_w, c_w):
        hist_w.append((float(av), float(cv)))
    mu_w.ghost_history = hist_w
    T_ac_w, T_ca_w, dT_w, _ = mu_w.te_observables(k=5)
    ok = T_ac_w > T_ca_w
    correct += int(ok)
    print(f"  trial {seed}: T_{{a->c}}={T_ac_w:.4f}  T_{{c->a}}={T_ca_w:.4f}  {'OK' if ok else 'WRONG'}")
rate = correct / 10
print(f"\n  Correct sign: {correct}/10 = {rate:.0%}")
assert rate >= 0.7, f"Sign reliability < 70%: {rate:.0%}"
print(f"  Sign reliability >= 70%: PASS")

print("""
=== EXP-310 Causal Ghost PASS (Fork A) ===
  declaration_hash: 767cd60f165a131d8ad738c2256c0654961d31a7e193d4bb1cc0318dcd9b3666
  Test 1 KSG ground truth Gaussian AR(1) N=2000:    PASS
  Test 2 Lossless degenerate T~0:                   PASS
  Test 3 Sign reliability non-neg Exp W=64 >=70%:   PASS
""")
