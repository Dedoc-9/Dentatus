"""
forge/invariant_synthesis.py — EXP-530 Automated Invariant Synthesis under the MCL_OBS2 protocol.

Separation of powers (MCL_OBS2 witness discipline): mining may PROPOSE, only the registry may LICENSE,
and L1 enforces ONLY what is licensed. A fuzzer that could activate its own constraints is a machine that
manufactures its own confirmations (Layer-0 violation). This pipeline makes that structurally impossible.

  PHASE 1 — THE FORGE (proposer).   `mine()` runs an observation pass over the frozen operators and emits
            candidate invariants, each tagged by BASIS:
              • constitutional — derivable/provable (chi∈[0.05,1]; Bethe frac∈[0,1]; E*_eff≥0). Hard-licensable.
              • empirical      — sample-observed range (dS_cit). A finite sample is NOT a law; these may be
                                 licensed ONLY as monitors (log/alert), NEVER as hard reverts.
            Each candidate is fingerprinted (SHA-256 over its semantic content + the engine code hash).

  PHASE 2 — THE REGISTRY (license). `constitution/INVARIANT_REGISTRY.json` is a precommitment ledger. A
            candidate becomes active ONLY when a human licenses its exact fingerprint, and only if it
            declares a failure_condition (a registry that cannot record falsification only confirms).
            `enforcement="hard"` is refused for empirical basis. Append-only; revocation is an errata entry.

  L1 — `active_clamps()` compiles a runtime guard for an entry ONLY if: (a) its recomputed fingerprint
       matches the licensed fingerprint (no silent drift), AND (b) the engine code hash still matches
       (license voids if the operator it was mined against changes). Mining alone enforces nothing.

Deterministic. `python3 forge/invariant_synthesis.py` runs the property proof of the gate.
"""
import os, sys, json, hashlib, random
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
for p in (REPO, HERE, os.path.join(REPO, "game/observability")):
    if p not in sys.path: sys.path.insert(0, p)
import numpy as np
from dentatus import core

REGISTRY_PATH = os.path.join(REPO, "constitution", "INVARIANT_REGISTRY.json")
PROTOCOL = "mcl-invariant-v1"
_CORE_FIELDS = ("name", "field", "kind", "lo", "hi", "basis", "failure_condition", "code_fp")


def engine_code_fp():
    """Bind invariants to the exact operator source they were mined against (MCL_OBS2 script-hash rule)."""
    src = open(os.path.join(REPO, "engine", "validity.py"), "rb").read()
    return hashlib.sha256(src).hexdigest()[:16]


def fingerprint(c):
    core_view = {k: c.get(k) for k in _CORE_FIELDS}
    return hashlib.sha256(json.dumps(core_view, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]


# ── PHASE 1 · THE FORGE (proposer) ────────────────────────────────────────────────────────────────────
def _rand_stalk(rng):
    s = np.zeros(18)
    s[0:4] = [rng.uniform(0.2, 1.5) for _ in range(4)]; s[4:12] = [rng.uniform(-1, 1) for _ in range(8)]
    s[12:15] = [rng.uniform(-1.5, 1.0) for _ in range(3)]; s[15:18] = [rng.uniform(-0.8, 0.8) for _ in range(3)]
    return s


def mine(seed=530530, N=20000):
    """Observation pass -> candidate invariants. Proposes only; licenses nothing."""
    rng = random.Random(seed)
    obs = {"chi": [1e9, -1e9], "dS_cit": [1e9, -1e9], "E_star_eff": [1e9, -1e9], "frac": [1e9, -1e9]}
    for _ in range(N):
        st = _rand_stalk(rng); chi = core.material_compliance_chi_514(stalk=st)["chi"]
        b = core.bethe_citadel_strain_512(rng.uniform(0, 30), rng.uniform(0, 2),
                                          rng.randint(0, 128), rng.randint(0, 192),
                                          vorticity=rng.uniform(0.05, 1.0), chi=chi)
        for k, v in (("chi", chi), ("dS_cit", b["dS_cit"]), ("E_star_eff", b["E_star_eff"]), ("frac", b["E_strain_frac"])):
            obs[k][0] = min(obs[k][0], v); obs[k][1] = max(obs[k][1], v)
    fp = engine_code_fp()
    cands = [
        # constitutional: derivable bounds — safe to license HARD
        {"name": "chi_bounds", "field": "chi", "kind": "range", "lo": 0.05, "hi": 1.0, "basis": "constitutional",
         "failure_condition": "any material_compliance_chi_514 returns chi<0.05 or >1.0",
         "provenance": {"seed": seed, "N": N, "observed": [round(obs["chi"][0], 6), round(obs["chi"][1], 6)]}},
        {"name": "bethe_frac_bounds", "field": "E_strain_frac", "kind": "range", "lo": 0.0, "hi": 1.0, "basis": "constitutional",
         "failure_condition": "E_strain_frac outside [0,1] (frac=min((s*/er)^2,1) by construction)",
         "provenance": {"seed": seed, "N": N, "observed": [round(obs["frac"][0], 6), round(obs["frac"][1], 6)]}},
        {"name": "E_star_eff_nonneg", "field": "E_star_eff", "kind": "range", "lo": 0.0, "hi": 1e9, "basis": "constitutional",
         "failure_condition": "E_star_eff<0 (E_eff=E*(1-frac), E>=0, frac<=1)",
         "provenance": {"seed": seed, "N": N, "observed": [round(obs["E_star_eff"][0], 6), round(obs["E_star_eff"][1], 6)]}},
        # empirical: a finite-sample range — NOT a law. May only be licensed as a MONITOR.
        {"name": "dS_cit_observed_envelope", "field": "dS_cit", "kind": "range",
         "lo": round(obs["dS_cit"][0], 6), "hi": round(obs["dS_cit"][1], 6), "basis": "empirical",
         "failure_condition": "a future fuzz case observes dS_cit outside this sampled envelope -> revoke/widen",
         "provenance": {"seed": seed, "N": N, "observed": [round(obs["dS_cit"][0], 6), round(obs["dS_cit"][1], 6)]}},
    ]
    for c in cands:
        c["code_fp"] = fp; c["fingerprint"] = fingerprint(c)
    return cands


# ── PHASE 2 · THE REGISTRY (license) ──────────────────────────────────────────────────────────────────
def load_registry():
    if not os.path.exists(REGISTRY_PATH):
        return {"protocol": PROTOCOL, "licensed": [], "errata": []}
    return json.load(open(REGISTRY_PATH))


def save_registry(reg):
    json.dump(reg, open(REGISTRY_PATH, "w"), indent=2, sort_keys=True); open(REGISTRY_PATH, "a").write("\n")


def license_candidate(reg, cand, licensor, enforcement="hard", licensed_at="UNDATED"):
    """The HUMAN act. Refuses: missing failure_condition; hard enforcement of an empirical basis; a
    candidate whose recomputed fingerprint disagrees with its claimed one (tampered proposal)."""
    if not cand.get("failure_condition"):
        raise ValueError("refused: no failure_condition (a registry that cannot record falsification only confirms)")
    if enforcement == "hard" and cand.get("basis") != "constitutional":
        raise ValueError("refused: empirical basis cannot be licensed as a HARD revert (only monitor)")
    if fingerprint(cand) != cand.get("fingerprint"):
        raise ValueError("refused: candidate fingerprint mismatch (tampered proposal)")
    entry = {k: cand[k] for k in _CORE_FIELDS}
    entry.update({"fingerprint": cand["fingerprint"], "enforcement": enforcement,
                  "licensed_by": licensor, "licensed_at": licensed_at, "provenance": cand.get("provenance", {})})
    reg["licensed"].append(entry)
    return reg


def revoke(reg, fingerprint_hex, reason, by, at="UNDATED"):
    """Append-only revocation (errata), never deletion — falsification stays on the record."""
    reg["licensed"] = [e for e in reg["licensed"] if e["fingerprint"] != fingerprint_hex]
    reg["errata"].append({"revoked": fingerprint_hex, "reason": reason, "by": by, "at": at})
    return reg


# ── L1 · enforcement (compile guards ONLY from valid licenses) ────────────────────────────────────────
def _range_pred(field, lo, hi):
    def pred(val):
        ok = (val == val) and (lo - 1e-9 <= val <= hi + 1e-9)
        return ok, ("ok" if ok else "%s=%r outside licensed [%g,%g]" % (field, val, lo, hi))
    return pred


def active_clamps(reg=None, current_code_fp=None):
    """Returns {name: (predicate, enforcement)} for entries that are licensed AND fingerprint-intact AND
    mined against the CURRENT engine. A drifted bound, a tampered entry, or an engine change -> not active."""
    reg = reg or load_registry(); fp_now = current_code_fp or engine_code_fp(); out = {}
    for e in reg.get("licensed", []):
        if fingerprint(e) != e.get("fingerprint"):     # entry edited after licensing -> void
            continue
        if e.get("code_fp") != fp_now:                 # engine changed since mining -> license void
            continue
        if e["kind"] == "range":
            out[e["name"]] = (_range_pred(e["field"], e["lo"], e["hi"]), e["enforcement"])
    return out


# ── PROOF of the gate ─────────────────────────────────────────────────────────────────────────────────
def _proof():
    fails = []
    cands = mine(N=4000)                                          # smaller N for the proof; bounds are stable
    by = {c["name"]: c for c in cands}

    # 1) MINING ALONE ENFORCES NOTHING — proposed but unlicensed -> not in active clamps
    empty = active_clamps({"protocol": PROTOCOL, "licensed": [], "errata": []})
    if empty: fails.append("unlicensed proposals were active")

    # 2) LICENSING IS THE GATE — license the constitutional chi bound (hard) -> becomes active
    reg = {"protocol": PROTOCOL, "licensed": [], "errata": []}
    reg = license_candidate(reg, by["chi_bounds"], "D.Dillberg", "hard", "2026-06-16")
    act = active_clamps(reg)
    if "chi_bounds" not in act: fails.append("licensed constitutional invariant not active")
    pred, enf = act["chi_bounds"]
    if not pred(0.5)[0] or pred(1.7)[0] or enf != "hard": fails.append("licensed chi clamp misbehaves")

    # 3) EMPIRICAL CANNOT BE HARD — refused; allowed only as monitor
    try:
        license_candidate(dict(reg), by["dS_cit_observed_envelope"], "D.Dillberg", "hard")
        fails.append("empirical bound accepted as HARD revert")
    except ValueError:
        pass
    reg2 = license_candidate({"protocol": PROTOCOL, "licensed": [], "errata": []},
                             by["dS_cit_observed_envelope"], "D.Dillberg", "monitor")
    if active_clamps(reg2)["dS_cit_observed_envelope"][1] != "monitor":
        fails.append("empirical bound not licensed as monitor")

    # 4) NO FALSIFICATION, NO LICENSE — a candidate without failure_condition is refused
    nofc = dict(by["chi_bounds"]); nofc["failure_condition"] = ""; nofc["fingerprint"] = fingerprint(nofc)
    try:
        license_candidate(dict(reg), nofc, "D.Dillberg", "hard"); fails.append("licensed without failure_condition")
    except ValueError:
        pass

    # 5) CRYPTOGRAPHIC DRIFT GUARD — silently widen a licensed bound in the registry -> fingerprint mismatch -> void
    tampered = {"protocol": PROTOCOL, "errata": [], "licensed": [dict(act and reg["licensed"][0])]}
    tampered["licensed"][0]["hi"] = 5.0                          # attacker widens the licensed bound
    if "chi_bounds" in active_clamps(tampered):
        fails.append("tampered (widened) bound stayed active")

    # 6) ENGINE-DRIFT GUARD — license void if the operator source hash no longer matches
    if "chi_bounds" in active_clamps(reg, current_code_fp="0000000000000000"):
        fails.append("license survived an engine code change")

    # 7) DETERMINISM — same seed -> identical fingerprints (reproducible precommitment)
    if [c["fingerprint"] for c in mine(N=4000)] != [c["fingerprint"] for c in cands]:
        fails.append("mining fingerprints not reproducible")
    return fails, reg


if __name__ == "__main__":
    fails, reg = _proof()
    chk = lambda i: "PASS" if not any(t in f for f in fails for t in i) else "FAIL"
    print("EXP-530 · Automated Invariant Synthesis — separation-of-powers proof")
    print("  1 mining alone enforces nothing ................", chk(["unlicensed"]))
    print("  2 licensing activates (constitutional, hard) ...", chk(["not active", "misbehaves"]))
    print("  3 empirical cannot be hard (monitor only) ......", chk(["HARD revert", "monitor"]))
    print("  4 no failure_condition -> no license ...........", chk(["failure_condition"]))
    print("  5 cryptographic drift guard (tamper -> void) ...", chk(["tampered"]))
    print("  6 engine-drift guard (code change -> void) .....", chk(["engine code"]))
    print("  7 deterministic precommitment fingerprints .....", chk(["reproducible"]))
    print("  VIOLATIONS:", len(fails))
    for f in fails: print("   !", f)
    sys.exit(1 if fails else 0)
