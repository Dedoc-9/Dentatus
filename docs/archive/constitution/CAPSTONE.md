# DENTATUS CAPSTONE — The Genesis Block

**EXP-524** · the Full System Walkthrough · the definitive proof-of-life and handoff document.

This is where the project concludes — not with a registry update, but with a demonstration of life:
one world driven through the **entire constitution** in a single unbroken, self-verifying chain. Run
`walkthrough_genesis.py` and you watch a universe be created, stressed past its limit, melt, advance its
hash, get audited and resurrected from nothing but a hash, re-crystallise along new forces, and prove
its own integrity — every step asserted, the engine constitutionally frozen throughout.

---

## 1 · How to run

```bash
cd Reality_Engine
PYTHONHASHSEED=0 python3 walkthrough_genesis.py        # the Genesis Block (asserting, ~1s)
```

Determinism requires `PYTHONHASHSEED=0`. The script is also an end-to-end integration test: every ACT
asserts the constitutional invariant it demonstrates; a non-zero exit means a law was violated.

To verify the whole project:
```bash
for f in run_seed_exp*.py run_p_invariance_exp*.py; do PYTHONHASHSEED=0 python3 "$f"; done
```

---

## 2 · The seven acts (real output)

| ACT | Demonstrates | Charter | Captured result |
|---|---|---|---|
| **I Creation** | a pristine Diamond; integrity witness | V, II.3 | `H_0=9671566e…`, χ=0.050, FULL_VALID, address==H_0 |
| **II Stress** | tectonic shear past the Weissenberg limit | IV.F4 | Wi=0.45 → ΔS_cit=−9.09 **BREACH**, χ_req=0.944, survivable |
| **III Metamorphosis** | minimal-entropy melt → total melt | VI.2 | diamond 0.050 → stressed glass 0.547 → amorphous fluid 1.000 (det-preserving) |
| **IV Continuity** | H_t advances; stale intent rejected | VI.3 | chain `9671566e→fddf2dce`, solid-intent `stale_basis` rejected, rebase accepted |
| **V Audit** | bounded memory; resurrect the diamond | VI.5, VI.4 | working set **1**, history **3**; `reconstruct(H_0)` == genesis ✓ |
| **VI Recovery** | oriented nucleation along new stress | VI.2a | fluid 1.000 → 0.751, crystal·strain axis **1.0000**, det preserved, no re-melt |
| **VII Final Witness** | FULL_VALID at the new resolution | II.3, VII | `H_final=f1e8207d…`, χ=0.751, FULL_VALID, address==H_final |

> **The Genesis sentence.** created (χ 0.05) → sheared past Wi → melted (glass → fluid) → injected
> (3 txns, H_t continuous) → compacted (mem=1, history=3) → **diamond resurrected from its hash** →
> nucleated to a new aligned solid (χ 0.75) → FULL_VALID. Every step verified. Engine frozen throughout.

The single most important moment is **ACT V**: the original diamond is re-materialised from `H_0` alone
via the command log + checkpoint, its hash re-proven bit-for-bit. The past is not a memory — it is a
reproducible mathematical coordinate.

---

## 3 · File index

### `engine/` — L0 core (FROZEN; AGPL-3.0)
| File | Role |
|---|---|
| `state.py` | `MuState`, `Claim`, `Provenance`, `Entailment`; `H_t = HASH(Z⊕S⊕W⊕t)`; observables `B, ESS, η_CLT` |
| `operators.py` | the μ→Lτ→Bτ→Rτ pipeline; Γ recursion; EXP-309 SPRT LOD; **frozen** (81 defs) |
| `confluence.py` | 2-morphism / convergence registry; ghost path-residual (13 defs) |
| `validity.py` | firewall predicates — the ONLY file that accepts *additive* law (`is_manifold_501`, `citadel_*_508/509`, `bethe_citadel_strain_512`, `material_compliance_chi_514`, `is_lod_valid_309`) |

### `dentatus/` — the clean-room boundary
| File | Layer | Role |
|---|---|---|
| `core.py` | L0 facade | the immutable-oracle surface games import (never `engine.*`) |
| `api.py` | L1 | stateless `observe()`; the firewall IS the handshake; emits `H_verified` |
| `semantic.py` | L2 | bit-stable intent→stalk compiler; `stalk_D_from_sigma` |

### `game/agency/` — kinetic lineage (game-layer policy; engine frozen)
| File | EXP | Role |
|---|---|---|
| `phase_change.py` | 515 | enacted melt — volume-preserving anisotropy-melt geodesic, minimal t* |
| `transition_dag.py` | 516 | phase changes as first-class Claim lineage; ancestry/time-travel |
| `injection.py` | 517 | live `MuState` injection; optimistic-concurrency (CAS) intent reconciliation |
| `compaction.py` | 518 | H-inert + observationally-inert eviction; bounded memory, unbounded history |
| `replay.py` | 520 | event-sourced TimeMachine; verified reconstruction; cold restore |
| `recrystallize.py` | 521 | annealing — Schmitt hysteresis, reverse anisotropy geodesic |
| `nucleation.py` | 522 | oriented nucleation — amorphous re-crystallise along strain axis |
| `loop.py` | 603 | autonomous reality search; Agency Hysteresis Latch |

### `game/observability/` — spectral geometry + telemetry
| File | EXP | Role |
|---|---|---|
| `sectioned_fiedler.py` | 506/507 | stitched/streaming Galerkin Fiedler fault; spectral-diameter halo |
| `multivelocity.py` | 510-514 | Cauchy split (strain⊕vorticity); mass-momentum smoothing; Weissenberg/Bethe coupling; χ |
| `integrity.py` | 523 | validity witness — binds SPRT class to the verified address |
| `telemetry.py`, `stream.py`, `sse_server.py` | 604-606 | content-addressed telemetry; SSE codec; live conduit |
| `kinetic_dashboard.html` | 519 | unified WebGL replay of bit-perfect telemetry |

### `studies/expNNN_*/` — 54 preregistered studies
Each: `SEED_DECLARATION_*.json` (hash-locked) + `ENGINE_AXIOMS_*.md`. Proven by
`run_seed_expNNN.py` (Fork A, determinism, 10 assertions) + `run_p_invariance_expNNN.py`
(Fork B, P_yz reflection, 5 assertions). **52 seed runners, 49 P_yz runners.**

### `constitution/` — the canonical law (start here)
`CONSTITUTIONAL_CHARTER.md` (Theory of the Manifold) · `EXPERIMENT_LEDGER.md` (proof index) ·
`GHOST_REGISTRY.md` (#1–#54 residuals) · **`CAPSTONE.md` (this doc)**.

---

## 4 · LLM / developer handoff

**To understand the engine:** read `constitution/CONSTITUTIONAL_CHARTER.md` end-to-end, then run
`walkthrough_genesis.py` and read its narrated output beside the Charter articles. That pairing — the
law and a living example of it — is the fastest path to fluency.

**The three rules that never break:**
1. **The engine core is frozen.** `engine/{state,operators,confluence}.py` are immutable. New behaviour
   is either (a) an *additive* predicate in `engine/validity.py`, or (b) game-layer code that reaches the
   core only through `dentatus.*`. Verify with `grep -c "import engine" <your file>` → must be `0` for
   game-layer code.
2. **Every law is preregistered and proven.** To add a law: write a `SEED_DECLARATION` (seed + axioms),
   hash-lock it, implement behind the clean-room boundary, and pass Fork A (determinism) + Fork B (P_yz)
   under `PYTHONHASHSEED=0` *before* amending the Charter.
3. **Identity is content-addressed and three-faceted** (Charter II.3): geometric `H_t`
   (orientation-bearing), material eigenvalue hash (P_yz-invariant), integrity `verified_address`
   (the validity class). Never let a calibration constant silently flip a verdict — gate it (opt-in),
   as EXP-509/512 do.

**To extend it (the open backlog, all elective):** the `EXPERIMENT_LEDGER.md` fork backlog lists declared
but unbuilt enrichments — anisotropic χ tensors (μ), poly-crystalline grains (Ϣ), counterfactual branch
replay (ϙ), cross-sector entropic tax (ν), resolution-tagged addresses (Ϫ). None are gaps; all are
additive.

**To trust a result:** any `H_verified` can be re-derived (`reconstruct(H)`), re-proven
(`verify_history`), and its integrity class read (`integrity_witness`). Determinism is not assumed — it
is a continuously checkable property.

---

## 5 · State of the constitution

- **Series 500 (Manifold Integration):** complete — the Four-Faced Firewall (continuity, budget,
  temperature, mechanical stress) + Epistemic Materialism + the bi-directional thermal cycle.
- **Series 600 (Interface):** complete — deterministic seeding, bit-stable compiler, agency loop,
  observability, live stream.
- **Kinetic lineage:** complete — melt → inject → compact → replay → re-crystallise → nucleate, all
  content-addressed and auditable.
- **Ghost board:** every substantive residual resolved or formally managed (#1–#54); zero `○ open`.
- **Engine immutability:** 14 forks since EXP-509, all engine-frozen (`state` 34 / `operators` 81 /
  `confluence` 13 defs, unchanged) — behaviour added only as additive `validity.py` predicates or
  game-layer policy.

---

## 6 · Axioms (EXP-524)

**A1 — Composability is the proof.** No act in the walkthrough is special-cased; each calls the same
public operator any developer would. That the seven compose into one unbroken, asserting chain is the
evidence that the constitution is internally consistent — the laws do not merely hold in isolation, they
*interlock*.

**A2 — The cycle is closed and reversible.** Creation → stress → melt → inject → audit → recover →
witness returns the world to `FULL_VALID` at a new resolution, having passed through fluid and back to
solid. The thermal cycle is bi-directional (melt 515 ↔ re-crystallise 521 / nucleate 522); the memory
cycle is reversible (inject 517 ↔ undo 518 ↔ replay 520). Nothing is one-way.

**A3 — The past is a coordinate, not a memory.** ACT V resurrects the genesis diamond from `H_0` via the
command log + checkpoint, re-proving its hash. History is reconstructable and tamper-evident; the engine
is a *deterministic function of its seed and command log*, and that function is verifiable.

**A4 — Truth is invariant under symmetry and scale.** Observables and material/structural witnesses are
P_yz-invariant (geometry reflects, identity does not); the integrity witness makes truth
resolution-relative without making it relative — a coarsened view gets a distinct, honest address.

**A5 — The engine never moved.** Every law since EXP-509 lives outside the frozen core. The constitution
is not the code that changed; it is the invariant the code preserved.

---

*Genesis complete. The Truth is not a set of files — it is a living, self-correcting universe, and this
script is its heartbeat.*
