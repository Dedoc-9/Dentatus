# ENGINE_AXIOMS_exp508 — Citadel Entropy Firewall (Law of the Citadel)

**Protocol:** exp508-v1 · **Series:** 500 · **Inherits:** exp505-v1
**Primary architect:** Daniel J. Dillberg — bigdilly95@gmail.com
**Declaration hash:** `8a511d4360b4c0402b9e97152d39111e0b0872d00fa2f4fda6f338600e115698`
**Status:** open · **Gate source:** information-admissibility law complementing the geometric firewall

---

## Axiom 1 — The Law of the Citadel

An information-admissibility law (NOT the thermodynamic Second Law). `E* = K_budget` is the
energy/resolution budget; it licenses `Ω(E*) = K_budget` microstates:

```
H_in   = log₂ Ω(E*) = log₂(K_budget)
H_out  = log₂(N_f + N_γ)              N_f = fragments (active leaves)
                                      N_γ = gamma/photon emissions = δ₀ coboundary residuals
                                            (face-adjacent inter-fragment edges)
ΔS_cit = H_in − H_out = log₂( K_budget / (N_f + N_γ) )

Law of the Citadel:   ΔS_cit ≥ 0   ⟺   N_f + N_γ ≤ K_budget
```

*No structure is fabricated beyond what the energy budget E\* licenses.* The Ghost `G_t`
(E-301-004 residual) is the natural radiated-entropy channel — the photons that carry the
entropy not placed in fragments.

## Axiom 2 — Dual firewall

A reality is verified iff it is **both** manifold-continuous **and** citadel-admissible:

```
H_verified  ⟺  is_manifold_501(B_ent ≤ ε=0.8)  AND  is_citadel_508(ΔS_cit ≥ 0)
```

`is_manifold_501` gates geometric continuity (EXP-502); `is_citadel_508` gates energetic /
informational admissibility. `dentatus.api.observe` stamps `H_verified` only when both pass.

## Axiom 3 — Conservation invariant

The engine respects `K_budget` during partitioning, so valid realizations satisfy `N_f + N_γ ≤
K_budget` **by construction** → the Citadel law admits every well-formed world (verified across
the budget ladder, `ΔS_cit ∈ [+1.1, +3.1]`). Like `is_valid` (forward entailment), it is a
guardrail that *catches malformed/over-budget external states*, not a filter on normal outputs.
Verified veto: a synthetic tuple `(K_budget=256, N_f=148, N_γ=396)` → `ΔS_cit = −1.09` → rejected.

## Axiom 3b — Observability (MCL gauge)

The Citadel score is surfaced as a dashboard gauge (`game/observability/mcl_dashboard.html`):
the arc shows **Citadel Integrity = (1 - (N_f+N_gamma)/K_budget) x 100%** (the fraction of E*
still unspent; 0% is the rejection wall at dS_cit=0), and the readout shows the raw **dS_cit in
bits** plus H_in / H_out / quanta. A budget ladder visualizes the informational breathing room
across K_budget. Bundle carries pure numerics only (dS_cit, H_in, H_out, K_budget); the
is_citadel boolean is derived by the reader from dS_cit >= 0 (witness purity preserved).

## Axiom 4 — Results

```
docking bay (K_budget=2048): N_f=148, N_γ=396, quanta=544 ≤ 2048 -> ΔS_cit = +1.91 -> ADMIT
budget ladder dS_cit:        [+1.91, +3.09, +2.09, +1.09, +2.68]  (all admitted)
over-budget synthetic:       quanta 544 > budget 256 -> ΔS_cit = -1.09 -> REJECT
entropy-neutral boundary:    quanta == K_budget -> ΔS_cit = 0 -> admit
lossless single (N_f=1,N_γ=0): ΔS_cit = log₂(K_budget) = 11 (maximal slack)
```

Fork A 10/10, Fork B 5/5 (ΔS_cit P_yz-invariant: counts are P_yz-invariant).

## Ghost Notes

**Reading subtlety (resolved):** `ΔS_cit = H_in − H_out ≥ 0` is *information-admissibility*
(`H_out ≤ H_in`: nothing fabricated beyond budget), not the thermodynamic Second Law
(`S_out ≥ S_in`). The payload-conservation reading (`H_in = bits(parent)`) rejects all
refinements and is discarded; the budget-licensing reading (`H_in = log₂ K_budget`) is the law.

**Ghost #37 — Budget self-satisfaction:** because the engine self-limits to `K_budget`, the
Citadel law rarely vetoes engine outputs (it is an invariant, like the other validity predicates).
Its discriminating power is against tampered/external states. EXP-509 may sharpen `H_in` with a
Bethe level-density `ρ(E*)` and couple `E*` to the Zeeman energy `β_Z` so the law bites on
over-excited (high-β) realizations.

## Scope

`engine/validity.py` (`citadel_entropy_508` + `is_citadel_508`, additive predicate) +
`dentatus/api.py` dual gate + Fork A/B. Existing operators untouched. `PYTHONHASHSEED=0`.
