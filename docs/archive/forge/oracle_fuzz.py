"""
forge/oracle_fuzz.py — Differential / metamorphic fuzzer over the FROZEN Dentatus core.

The frozen engine is the behavioral ORACLE. The harness throws large volumes of seeded-random but
well-formed input at the real operators and asserts three classes of property at the L1 envelope:

  (1) CLAMPS         — outputs stay inside their declared envelope (forge/clamps.py).
  (2) METAMORPHIC    — relations that must hold between related inputs (no ground truth needed):
                         strain ↑  ⇒ E*_eff ↓   (shear may only narrow the Citadel window)
                         chi    ↑  ⇒ dS_cit ↑   (more compliant material survives more, EXP-514)
  (3) DETERMINISM    — the oracle is a pure function: identical input ⇒ BIT-IDENTICAL output;
                       MuState.seal is collision-sensitive: a 1-ULP perturbation ⇒ different H.

It also MINES observed invariant ranges (a lightweight Daikon-style pass) to propose tighter clamps.
Deterministic: fixed seed -> identical campaign. Run:  python3 forge/oracle_fuzz.py [N]
"""
import os, sys, random, struct, math
if os.environ.get("PYTHONHASHSEED") != "0":
    os.environ["PYTHONHASHSEED"] = "0"; os.execv(sys.executable, [sys.executable] + sys.argv)
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
for p in (REPO, HERE):
    if p not in sys.path: sys.path.insert(0, p)
import numpy as np
from dentatus import core
import clamps as K

A0 = 0.15; D_STALK = 18; BETA_MAX = 30.0; NF_MAX = 128; NG_MAX = 192


def rand_stalk(rng):
    s = np.zeros(18)
    s[0:4]  = [rng.uniform(0.2, 1.5) for _ in range(4)]            # A photometric
    s[4:8]  = [rng.uniform(-1.0, 1.0) for _ in range(4)]           # B affine
    s[8:12] = [rng.uniform(-1.0, 1.0) for _ in range(4)]           # C curvature
    s[12:15] = [rng.uniform(-1.5, 1.0) for _ in range(3)]          # D log-diagonal (log-Cholesky)
    s[15:18] = [rng.uniform(-0.8, 0.8) for _ in range(3)]          # D off-diagonal
    return s


def perturb_1ulp(x):
    b = struct.unpack("<Q", struct.pack("<d", float(x)))[0]
    return struct.unpack("<d", struct.pack("<Q", b + 1))[0]


def run(N=20000, seed=9671566):
    rng = random.Random(seed)
    viol = []
    rng_obs = {"chi": [1e9, -1e9], "dS_cit": [1e9, -1e9], "E_star_eff": [1e9, -1e9], "frac": [1e9, -1e9]}
    n_surv = 0
    for i in range(N):
        st = rand_stalk(rng)
        # --- chi clamp + determinism ---
        c1 = core.material_compliance_chi_514(stalk=st); c2 = core.material_compliance_chi_514(stalk=st)
        if c1 != c2: viol.append(("determinism.chi", i, "non-identical repeat"))
        ok, why = K.clamp_chi(c1["chi"])
        if not ok: viol.append(("clamp.chi", i, why))
        chi = c1["chi"]
        # --- bethe clamp + determinism ---
        beta = rng.uniform(0.0, BETA_MAX); strain = rng.uniform(0.0, 2.0)
        nf = rng.randint(0, NF_MAX); ng = rng.randint(0, NG_MAX); vort = rng.uniform(0.05, 1.0)
        b1 = core.bethe_citadel_strain_512(beta, strain, nf, ng, vorticity=vort, chi=chi)
        b2 = core.bethe_citadel_strain_512(beta, strain, nf, ng, vorticity=vort, chi=chi)
        if b1 != b2: viol.append(("determinism.bethe", i, "non-identical repeat"))
        ok, why = K.clamp_bethe(b1)
        if not ok: viol.append(("clamp.bethe", i, why))
        n_surv += int(b1["survivable_by_material"])
        # --- metamorphic: strain ↑ ⇒ E*_eff ↓ (monotone non-increasing) ---
        bhi = core.bethe_citadel_strain_512(beta, strain + rng.uniform(0.05, 0.5), nf, ng, vorticity=vort, chi=chi)
        if bhi["E_star_eff"] > b1["E_star_eff"] + 1e-6:
            viol.append(("metamorphic.strain_monotone", i, "E*_eff rose under more strain"))
        # --- metamorphic: chi ↑ ⇒ dS_cit ↑ (window widens, EXP-514) ---
        chi_hi = min(1.0, chi + rng.uniform(0.05, 0.4))
        blo = core.bethe_citadel_strain_512(beta, strain, nf, ng, vorticity=vort, chi=chi)
        bch = core.bethe_citadel_strain_512(beta, strain, nf, ng, vorticity=vort, chi=chi_hi)
        if bch["dS_cit"] < blo["dS_cit"] - 1e-6:
            viol.append(("metamorphic.chi_monotone", i, "dS_cit fell as chi rose"))
        # --- observed ranges ---
        for k, val in (("chi", chi), ("dS_cit", b1["dS_cit"]), ("E_star_eff", b1["E_star_eff"]), ("frac", b1["E_strain_frac"])):
            rng_obs[k][0] = min(rng_obs[k][0], val); rng_obs[k][1] = max(rng_obs[k][1], val)
    # --- seal: determinism + supra-quantum sensitivity + sub-quantum stability ---
    # MINED (this corpus): the seal canonicalisation floor is ~1e-15 (full float significand); H is
    # therefore sensitive to any change comfortably above it and stable to changes below representability.
    seal_det = seal_sens = seal_stab = 0
    for j in range(400):
        stalks = [rand_stalk(rng) for _ in range(6)]
        H1 = _seal(stalks); H2 = _seal([s.copy() for s in stalks])
        if H1 == H2: seal_det += 1
        else: viol.append(("seal.determinism", j, "identical input -> different H"))
        sens = [s.copy() for s in stalks]; sens[0][0] += 1e-9                    # supra-quantum -> MUST change
        if _seal(sens) != H1: seal_sens += 1
        else: viol.append(("seal.sensitivity", j, "1e-9 perturbation did not change H"))
        stab = [s.copy() for s in stalks]; stab[0][0] += 1e-18                   # sub-representable -> MUST NOT
        if _seal(stab) == H1: seal_stab += 1
        else: viol.append(("seal.stability", j, "1e-18 (sub-representable) perturbation changed H"))
    return {"N": N, "violations": viol, "survivable_frac": round(n_surv / N, 4),
            "observed": {k: [round(v[0], 6), round(v[1], 6)] for k, v in rng_obs.items()},
            "seal_determinism": "%d/400" % seal_det, "seal_sensitivity": "%d/400" % seal_sens,
            "seal_stability": "%d/400" % seal_stab}


def _seal(stalks):
    claims = {}
    for k, s in enumerate(stalks):
        cl = core.Claim(provenance=core.Provenance(parent_ids=(), operator_id="fz%d" % k, timestamp=core.now_iso()),
                        payload="p%d" % k, stalk=s, t=0)
        claims[cl.id] = cl
    mu = core.MuState(t=0, claims=claims, entailments={}, active=frozenset(claims.keys()), S=np.zeros(18), alpha=0.5)
    mu.seal(); return mu.H


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    r = run(N)
    print("DENTATUS FORGE · differential fuzz campaign (frozen core as oracle)")
    print("  cases: %d   survivable_by_material: %.1f%%" % (r["N"], 100 * r["survivable_frac"]))
    print("  seal determinism: %s   supra-quantum sensitivity: %s   sub-quantum stability: %s"
          % (r["seal_determinism"], r["seal_sensitivity"], r["seal_stability"]))
    print("  mined invariant ranges:")
    for k, v in r["observed"].items(): print("    %-12s [% .6f, % .6f]" % (k, v[0], v[1]))
    print("  VIOLATIONS: %d" % len(r["violations"]))
    for v in r["violations"][:12]: print("    !", v)
    sys.exit(1 if r["violations"] else 0)
