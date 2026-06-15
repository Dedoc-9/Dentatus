# ENGINE_AXIOMS_exp604 — MCL Observability Dashboard (content-addressed telemetry)

**Protocol:** exp604-v1 · **Series:** 600 · **Inherits:** exp603-v1
**Primary architect:** Daniel J. Dillberg — bigdilly95@gmail.com
**Declaration hash:** `f1f9c1a4438c3c23aa6cfa6850837615a9c1de9958780098ca6f53aef934e707`
**Status:** open · **Gate source:** EXP-603 agency loop stable → real-time observable telemetry
**Location:** `game/observability/` (decoupled) + `game/observability/mcl_dashboard.html`

---

## Axiom 1 — The data-stream architecture (the pioneering choice)

Polling re-runs the engine every tick and the O(N³) Fiedler eigendecomposition dominates; a raw
socket push is better but still recomputes per frame. EXP-604 exploits the bit-perfect determinism
(EXP-601/602): **telemetry is keyed by `H_state` and cached** — the Fiedler decomposition is
computed once per *unique* reality and never again.

```
producer:  api.observe(telemetry=True) -> frame keyed by H_state
transport: replay bundle (deterministic, offline)  |  SSE push (live)
SSE rule:  first occurrence of an H_state carries full telemetry; repeats carry a reference -> client cache hit
equilibrium: lc-transitions are rare at EMA equilibrium (EXP-409) -> a live stream cycles a handful
             of addresses -> near-zero recompute and bandwidth
```

Measured: a 6-probe agency search produced 5 unique states + 1 content-address cache hit.

## Axiom 2 — L1 telemetry block

`api.observe(telemetry=True)` adds per-leaf `{center, size, fiedler (v₂ eigenvector), g_ent}` plus
`fiedler_lambda`, content-addressed by `H_state`. The **Fiedler vector sign bisects the manifold**
(73 positive / 73 negative at the 148-leaf docking bay) — the basin boundary *is* the fault line.

## Axiom 3 — Panels (observable, not interpreted)

The dashboard renders observables only: Fiedler fault (3D WebGL / 2D fault map), Manifold Firewall
gauge (`B_ent` vs ε=0.8), the tectonic-stress agency-descent curve, selected-realization stats, and
the content-address cache transport. Admissibility is the numeric bound `worst_ratio ≤ ε` — no
boolean verdict appears in telemetry (witness purity, verified Fork A [7][8]).

## Axiom 4 — Results

```
docking-bay reality search rendered: stress 0.170 -> 0.057, firewall ADMITTED (B_ent << eps)
telemetry: 148-leaf fault, 73/73 Fiedler bisection, lambda_2 = 0.240
bundle: deterministic, 6 frames / 5 unique states / 1 cache-hit; dashboard self-contained (cdnjs only)
```

Fork A 10/10, Fork B 5/5 (telemetry observables P_yz-invariant: λ₂, |fiedler| multiset, n_leaves, H_state).

## Ghost Notes

**Ghost #36 — Fiedler sign ambiguity:** the eigenvector sign is arbitrary, so the fault's two
basins may swap colors run-to-run on different platforms. The fault *structure* (the |v₂| multiset
and the bisection) is invariant; the dashboard colors by sign for legibility, not as a claim about
which basin is "which". Fork B asserts the |fiedler| multiset, not signed per-leaf values.

## Scope

`dentatus/api.py` telemetry block (L1, not engine) + `game/observability/` + dashboard + Fork A/B.
No engine change. Requires `PYTHONHASHSEED=0` for bit-stable telemetry/addresses.
