# ENGINE_AXIOMS_exp509 — Zeeman/Bethe Citadel (dynamic thermodynamic firewall)

**Protocol:** exp509-v1 · **Series:** 500 · **Inherits:** exp508-v1
**Primary architect:** Daniel J. Dillberg — bigdilly95@gmail.com
**Declaration hash:** `58f3f306a8f48cbe7defa35291a8374a8a94ba7e37d02849c3807fa344c5eea2`
**Status:** open · **Location:** `engine/validity.py` + `dentatus/api.py`

---

## Axiom 1 — From static budget to living ecology

EXP-508 used `E* = K_budget` with a counting level density. EXP-509 makes the Citadel a *reactive
thermodynamic* law: `E*` is the **Zeeman excitation** `β_Z` (the homeostatic field — the manifold's
"temperature"), and the level density is the nuclear **Bethe** form:

```
ρ(E*)         = exp( 2·√(a·E*) )                  Bethe level density
H_in          = log₂ ρ(E*) = 2·√(a·E*) / ln2      available phase space (bits)
H_out         = log₂(N_f + N_γ)                    realized microstates
ΔS_cit_bethe  = H_in − H_out ≥ 0                   thermodynamic Law of the Citadel
```

A world whose realized complexity exceeds the phase space its excitation licenses **overheats** and
is rejected. Verified friction (fixed complexity N=544): `E* = [40,20,10,5,2] → ΔS = [20.9, 12.1,
5.9, 1.5, −2.4]` — crosses zero (overheat) below `E* ≈ 3`. Excitation gates structure.

## Axiom 2 — The level-density parameter `a` (the careful choice)

```
a = a0 · d_stalk        d_stalk = 18 (stalk-schema mass = substrate degrees of freedom)
a0 = 0.15               calibrated so valid realizations pass (margin >= +0.86)
```

`a` is a **substrate property, FIXED per realization** — it scales with the *schema mass* `d=18`,
the engine's intrinsic degrees of freedom per claim (the Dentatus analog of nucleon count). It does
**NOT** scale with leaf-count. Leaf-count is the realized complexity already in `H_out`; coupling
`a` to it double-counts `N` (`H_in ~ √(N·E*)` would outrun `H_out ~ log₂N`) and **dissolves the
excitation friction**. So the obvious "system mass = leaf-count" choice is the wrong one.

## Axiom 3 — Observable + opt-in gate (safety)

`bethe_citadel` is ALWAYS reported by `api.observe` as the temperature observable. It is an
**opt-in gate**: `request["bethe_gate"]=True` makes the firewall triple (manifold AND citadel-508
AND bethe-509). By default `H_verified` is gated only by manifold + static-508, so a calibration
constant never silently flips verification. Verified: valid docking-bay realizations are
Bethe-admissible across the budget ladder; the default `H_verified` is unchanged vs EXP-508.

## Axiom 4 — Results

```
docking bay @ beta_Z=36.9: H_in=28.8, H_out=9.1, dS_cit_bethe=+19.7 -> ADMIT (cool)
overheat @ beta_Z=2:        dS_cit_bethe=-2.4 -> REJECT (too complex for its excitation)
opt-in gate: bethe_gate=True -> triple firewall; valid worlds still verified
```

Fork A 10/10, Fork B 5/5 (`E_star=β_Z` is norm-derived -> P_yz-invariant -> ΔS_cit P_yz-invariant).

## Ghost Notes

**Ghost #43 — Calibration vs autonomy:** `a0` is a fixed engine constant; a fully autonomous
ecology could let `a0` (or `E*`) co-evolve with the homeostatic loop (Φ_fb), making "temperature"
a state variable rather than a parameter. Deferred — keep `a0` fixed for verifiability.

## Scope

`engine/validity.py` (`bethe_citadel_509` + `is_bethe_citadel_509`, additive) + `dentatus/api.py`
(observable + opt-in gate). Operators/state/confluence untouched. `PYTHONHASHSEED=0`.
