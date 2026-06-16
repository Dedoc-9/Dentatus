# DENTATUS CONSTITUTIONAL CHARTER
## The Theory of the Manifold — a Reality Engine, formally specified

**Status:** canonical · **Series:** 500 (Manifold Integration) + 600 (Interface) · **Engine protocol:** `exp505-v1`
**Authority:** this document is the constitution. Where an experiment study (`studies/exp*`) and this
charter disagree on intent, the charter governs the *law*; the study governs the *proof*. The engine
core (`engine/state.py`, `engine/operators.py`, `engine/confluence.py`) is frozen; behaviour is added
only as additive predicates in `engine/validity.py` or in the decoupled game layer.

---

## PREAMBLE — Reality First

A world is not a collection of bits rendered to a screen; it is a **realized state** that must satisfy
a fixed set of physical laws to exist at all. The engine does not simulate a material — it *realizes*
one, admits or rejects it against a firewall, hashes its identity, and records its lineage. Every
observable is a pure number; every transition is content-addressed; every law is invariant under the
engine's symmetry. What follows is that law.

This charter is written in **strict formal-execution style**: the system is specified only in terms of
state variables, operators, and transformations. Explanatory prose is set apart from the normative
articles.

---

## ARTICLE 0 — STATE AND NOTATION

**0.1 Stalk schema.** Each claim carries a feature stalk `F(v) ∈ ℝ^d`, `d = STALK_DIM = 18`, in four
sectors:

| Sector | Slice | Content |
|---|---|---|
| A | `0:4` | photometric (mass, r, g, b) |
| B | `4:8` | affine |
| C | `8:12` | curvature |
| D | `12:18` | Gaussian covariance, log-Cholesky `(log l11, log l22, log l33, l21, l31, l32)` → `Σ = L Lᵀ` |

**0.2 Engine state.** `μ_t = (G_t, F_t)` is a cellular sheaf:
- `claims : V_t` — id → Claim (a node; `id = SHA256(provenance ⊕ payload ⊕ t ⊕ pv)[:16]`)
- `entailments : E_t` — (src,tgt) → restriction map (an edge)
- `active : W_t` — frozenset of leaf claim ids (out-degree 0)
- `S ∈ ℝ^d` — EMA ghost accumulation; `α` — EMA coefficient; `t` — timestep.

**0.3 Primary observables (pure numeric).**
```
Z_t  = Σ_{v∈W_t} F(v)                          (primary sum, ℝ^d)
B(t) = ‖S_t‖ / (‖Z_t‖ + ε)                      (ghost-to-signal)
ESS  = (Σ wᵢ)² / Σ wᵢ²                           (effective sample size, wᵢ = ‖F(vᵢ)‖)
η_CLT = √|W_t| · (μ̂_active − μ_grand)            (CLT fluctuation)
```

---

## ARTICLE I — THE OPERATOR PIPELINE

**I.1** State evolution obeys the fixed, ordered, stateless pipeline:

```
μ → Lτ → Bτ → Rτ → Z → S → W → OBS
```

Each operator is stateless and depends only on its declared inputs and outputs. No hidden coupling or
cross-stage mutation outside the defined mapping is permitted.

**I.2** Operators are lossless by construction where declared: a partition satisfies
`Σ children = parent`, so the projection ghost (Article III) is zero unless a residual is explicitly
introduced.

---

## ARTICLE II — THE HASH INDEX

**II.1 State hash.** Every sealed state binds an immutable structural identifier:

```
H_t = HASH(Z_t ⊕ S_t ⊕ W_t ⊕ t ⊕ protocol_version)
```

Hashes function only as structural indices; they never encode semantic interpretation.

**II.2 Determinism (EXP-601/602).** `Claim.id` excludes the wall-clock timestamp; with
`PYTHONHASHSEED=0` the same seed declaration yields a bit-identical `H_t` across runs and processes.
`H_verified = H_t` iff the state is admissible (Article IV), else `⊥`; it is the permanent address of a
realized reality.

**II.3 Three facets of identity (EXP-517, EXP-523).** Identity has three orthogonal facets:
- **Geometric** — `H_t = HASH(Z⊕S⊕W⊕t)` hashes the raw `Z` vector and is **orientation-bearing** (the
  live geometric identity; *not* P_yz-invariant).
- **Material** — structural/material witnesses (track-DAG hash, material eigenvalue hash, χ) are built
  from **norms / eigenvalues** and *are* P_yz-invariant.
- **Integrity** — the `verified_address` (EXP-523) binds the SPRT validity class
  (`FULL_VALID`/`LOD_RELAXED`/`INVALID`) to `H_t`: a level-of-detail-relaxed state (a predicate bypassed
  at distance) gets a **distinct** address and cannot launder full integrity. `FULL_VALID → H_t`
  (backward compatible). Integrity is resolution-relative; the address now witnesses the resolution.

Invariance holds where identity lives; orientation is carried where geometry lives; the integrity tag is
a geometry-independent label.

---

## ARTICLE III — THE GHOST

**III.1 Definition.** The residual ("ghost") is defined exclusively as

```
G_t = Z_t − Π_{W_t}(Z_t)
```

a numeric residual, never an entity.

**III.2 Accumulation.** It is stored only through EMA accumulation:

```
S_{t+1} = α·S_t + (1 − α)·G_t
```

**III.3 No backreaction.** No operator branches on `G_t`; there is no direct control or interpretation
based solely on the ghost. Forward evolution (`Z` dynamics under `Lτ/Bτ/Rτ`) and dual residual tracking
(`S, G`, CLT fluctuations) are kept orthogonal — **dual arithmetic separation** — with no algebraic
reduction collapsing both into a single representation.

**III.4 Named ghosts.** See `GHOST_REGISTRY.md`. The injection ghost (#51, `ΔZ` of a re-declaration) and
the compaction shadow (#52, retained sufficient statistics) are the dual-space signatures of the kinetic
operators (Article VI).

---

## ARTICLE IV — THE FOUR-FACED FIREWALL  *(the unified admissibility law)*

A realized state is **admissible** iff all active faces hold. Each face is a pure inequality over
observables.

**Face 1 — Geometric continuity (EXP-501/502).**
```
B_ent(μ) ≤ ε_manifold = 0.8
```
The sheaf coboundary entanglement across face-adjacent octree leaves must stay below the manifold
threshold (degree-normalized; Ghost #22).

**Face 2 — Budget conservation / Law of the Citadel (EXP-508).**
```
ΔS_cit^K = log₂(K_budget) − log₂(N_f + N_γ) ≥ 0
```
Realized complexity (fragments + γ-quanta) may not exceed the declared budget.

**Face 3 + Face 4 — Thermodynamic temperature ∧ mechanical stress (EXP-509/512/513).** *(opt-in gate)*
```
ΔS_cit^β = 2·√(a · E*_eff) / ln2  −  log₂(N_f + N_γ)  ≥  0
```
with the **coupling chain** that unifies stress, temperature, and entropy:

```
L            = ∇v  (section velocity gradient; Cauchy split L = Sym ⊕ Ω)         [EXP-510]
Wi           = ‖Sym(L)‖ / max(‖Ω‖, εΩ)        (Weissenberg: shear / spin)        [EXP-513]
χ            = clip( w·η(Σ_D) + (1−w)·(1−gap(Σ_D)), χ_min, 1 )   (compliance)     [EXP-514]
ε_eff        = STRAIN_STAR_REF · χ            (material narrows the window)        [EXP-514]
E*_eff       = β_Z · ( 1 − (Wi / ε_eff)² )    (deformation-energy drain)           [EXP-512]
a            = a₀ · d_stalk = 0.15 · 18 = 2.7  (FIXED substrate; never scales with N or strain) [EXP-509]
ρ(E*)        = exp( 2·√(a · E*) )             (Bethe level density)                [EXP-509]
```

> **The law in one sentence.** Mechanical shear (`Wi`) sequesters energy into deformation, lowering the
> effective excitation `E*_eff` (the Bethe temperature); a lower temperature lowers the level-density
> entropy `H_in = log₂ρ(E*_eff)`; if `H_in` falls below the realized complexity `H_out = log₂(N_f+N_γ)`,
> the Citadel overheats and the state is rejected. The material's compliance `χ` (Article V) sets how
> much shear it may survive. Mechanical instability is thereby converted into an informational breach.

**IV.2 Combined predicate.**
```
admissible(μ) ⟺ (B_ent ≤ ε_manifold) ∧ (ΔS_cit^K ≥ 0) ∧ [bethe_gate ⇒ (ΔS_cit^β ≥ 0)]
H_verified    = H_t if admissible(μ) else ⊥
```
A calibration constant (`a₀`, `STRAIN_STAR_REF`, `ε_ref`) never silently flips a verdict: the
thermodynamic/mechanical face is **opt-in** (`bethe_gate`) so the default firewall is byte-stable across
the calibration history.

---

## ARTICLE V — EPISTEMIC MATERIALISM  *(EXP-514)*

**V.1** A material is a filter for truth, not a shader. Compliance `χ ∈ [χ_min, 1]` is a continuous
function of the Sector D covariance spectrum (NOT a lookup table):

```
η   = −Σ pᵢ ln pᵢ / ln n,   pᵢ = λᵢ/Σλ        (spectral entropy — disorder)
gap = 1 − λ₂/λ₁                                (spectral gap — ordering)
χ   = clip( w·η + (1−w)·(1−gap), χ_min, 1 )
```

**V.2 Stiff = fragile.** Because `ε_eff = STRAIN_STAR_REF · χ` and `χ ≤ 1`, a declared material can only
**narrow** the constitutional window, never widen it. Ordered/anisotropic matter (low η, high gap →
low χ, "diamond") has a *narrow* admissibility window and shatters at small shear; disordered/isotropic
matter (χ→1, "water") survives high `Wi`.

**V.3 No bypass / dimensional governance.** `STRAIN_STAR_REF` is a protected constitutional constant,
not an L1 parameter. `χ` is a function of *declared state* (the Sector D bits of `H_state`), bounded so
it can never disable the firewall. *You cannot have the structural benefits of Stone with the mechanical
freedom of Water without paying the Entropic Tax* — to gain compliance you must change the world's
definition, not call a knob.

---

## ARTICLE VI — THE KINETIC LINEAGE  *(EXP-515 → EXP-518)*

When the firewall reports a *survivable* breach (`χ_world < χ_required ≤ 1`), the world transitions
rather than erroring. The transition is reported by the engine and enacted by the game layer.

**VI.1 χ_required (the phase-change target, EXP-514).**
```
frac_max   = 1 − (H_out · ln2 / 2)² / (a · E*)
χ_required = strain* / (STRAIN_STAR_REF · √frac_max)
```

**VI.2 Enacted phase change (EXP-515).** Sector D is re-declared along the **volume-preserving
anisotropy-melt geodesic**:
```
ℓᵢ(t) = ℓ̄ + (1 − t)(ln λᵢ − ℓ̄)          (det Σ preserved; χ(t) monotone ↑)
minimal mode: t* = min t with χ(t) ≥ χ_required + margin   (least entropy injection)
total   mode: t = 1                       (full isotropic melt)
```
Outcomes are exhaustive: `stable | melted | unsurvivable`.

**VI.2a Re-crystallization (EXP-521).** The reverse leg closes the thermal cycle with a *distinct*
cooling threshold (Schmitt hysteresis): freeze fires only when `χ_cur − χ_required ≥ hysteresis` and
re-orders down to `χ_required + hysteresis` (a margin above the melt boundary ⇒ chatter-free). Geometry
is the reverse geodesic `ℓ_i(g) = ℓ̄ + g(ℓ_i − ℓ̄)`, `g > 1` widening the spectrum (det preserved). The
dead-zone between the melt and freeze boundaries is **material memory** — a `χ`–`Wi` hysteresis loop. A
totally-isotropic state is amorphous-locked (Ghost #54).

**VI.3 Live injection (EXP-517).** The melted claim replaces the breached leaf in `W_t`; the engine
re-seals; `H_t` advances continuously `H_before → H_after` — **the lineage is the state**.
- *Interference* (intent computed against a superseded world) is resolved by **optimistic concurrency**:
  every actor stamps the `H` it read; injection is a compare-and-swap on `H`; an intent whose
  `basis_H ≠ H_t` is rejected (`stale_basis`) and must rebase. No locks; the hash is the truth.

**VI.4 Provenance DAG (EXP-516).** Each transition is a first-class child Claim
(`operator_id = "PhaseChange:<mode>"`, payload = material eigenvalue hash). `ancestry(id)` and
`lineage(id)` give content-addressed time-travel. The DAG grows only on `melted`. Content-addressing by
destination ⇒ convergent melt paths *merge* (confluence).

**VI.5 History compaction (EXP-518).** Inactive claims are evicted from the live working set under two
inertness guarantees:
- **H-inert:** `H_t` reads only active claims ⇒ eviction leaves `H_t` bit-identical.
- **Observationally inert:** the only all-claims observable `η_CLT` is preserved *exactly* via retained
  sufficient statistics `(Σ‖·‖, count)` of evicted claims.

Tiered memory: a bounded **Skeleton Lineage** (last `N` snapshots) gives O(1) undo; the DAG (hashes
only) is unbounded cold history; look-back beyond `N` requires replay. **Bounded memory, unbounded
auditable history.**

---

## ARTICLE VII — INVARIANCES AND VALIDITY CONDITIONS

**VII.1 P_yz symmetry.** All operators commute with the reflection `x → −x` to machine precision
(`δ ≈ 10⁻¹⁴`). Observables and structural witnesses are built from norms / eigenvalues so they are
P_yz-invariant; the live geometric `H_t` is orientation-bearing by design (Article II.3).

**VII.2 The five validity conditions.** A run is valid iff, simultaneously:
1. **Hash continuity** — every state binds `H_t`; transitions advance it without gaps.
2. **Protocol ordering** — the Article I pipeline order is respected; operators are stateless.
3. **Ghost closure** — `G_t = Z_t − Π_W(Z_t)`; accumulation is EMA-only; no ghost-based control.
4. **Dual arithmetic separation** — forward (`Z`) and dual (`S, G`, CLT) spaces stay orthogonal.
5. **Observable purity** — observables are pure numeric/symbolic (`B, ESS, η_CLT, Wi, χ, ΔS_cit`); no
   interpretation, narrative, or causal attribution; verdict booleans never leak as observables
   (Ghost #31).

If any condition fails, execution is invalid and must revert to the last valid hashed state.

---

## ARTICLE VIII — SPECTRAL GEOMETRY  *(EXP-503, 506, 507, 510, 511)*

**VIII.1** The global fault is the Fiedler vector (`λ₂` eigenpair) of the sheaf Laplacian `L_sheaf`;
`λ₂` is the stability metric for global sections.

**VIII.2 Galactic-scale stitch (EXP-506/507).** A Galerkin coarse Fiedler (`L_c = PᵀLP`) carries the
global fault at section resolution; partition-of-unity interpolation with a dynamic spectral-diameter
halo (`σ_s ∝ 1/√λ₂^local`, 1-leaf floor) makes the fault `C⁰`-continuous; the field is streamable under
a bounded resident set, content-addressed per section.

**VIII.3 Multi-velocity (EXP-510/511).** Per-section co-moving frames (EMA `v_s`) hold correspondence
under non-rigid motion; the Cauchy split `L = strain ⊕ vorticity` isolates true non-rigidity; the halo
is strain-gated (`σ_s ·= 1+γ·strain`) with mass-momentum (volume, not count) boundary velocity
smoothing.

---

## ARTICLE IX — THE CLEAN ROOM  *(architecture)*

**IX.1 Three layers.**
- **L0 engine** (`engine/`) — the frozen black-box oracle (AGPL-3.0). `state.py`, `operators.py`,
  `confluence.py` are immutable; `validity.py` accepts only *additive* firewall predicates.
- **L1 `dentatus.api` / `dentatus.core`** — stateless handshake; the firewall is the contract; emits
  `H_verified`.
- **L2 `dentatus.semantic`** — bit-stable intent → stalk compiler.
- **game/** — every game treats the engine as an immutable oracle; reaches the core only via
  `dentatus.*` (never `import engine.*`).

**IX.2 Immutability ledger.** Since EXP-509, all behaviour lives in the game layer or as additive
`validity.py` predicates. Engine def-counts are invariant: `state.py` 34, `operators.py` 81,
`confluence.py` 13.

---

## ARTICLE X — OBSERVABILITY  *(EXP-604, 605, 519)*

Telemetry is content-addressed by `H_state`; the live SSE conduit emits keyframe+delta coarse codecs
(bitrate ∝ rate-of-change). The Unified Kinetic Dashboard (EXP-519) replays bit-perfect captured
telemetry: the shearing seam (Weissenberg heat-map), the Citadel yield (`χ_required` flash, melt pops,
firewall-holds), the growing provenance tree, the advancing `H_t`, and the flat-memory / climbing-history
gauges — one verdict, four faces, provably real.

---

## CLOSING — THE UNIFIED LAW

```
                 stress              temperature            entropy            identity
   Wi = ‖Sym‖/‖Ω‖  ──▶  E*_eff = β_Z(1−(Wi/(ε*·χ))²)  ──▶  ΔS_cit = 2√(aE*_eff)/ln2 − log₂(N)  ──▶  H_verified
        │                         │                              │                                   │
   EXP-510/513              EXP-509/512                     EXP-508/509                          EXP-602
        │                         │                              │                                   │
   χ = f(spec Σ_D) ─────────────┘ (material narrows window)      │                          on breach: melt→inject→
   EXP-514                                                        └── ΔS<0 ⇒ χ_required ⇒ ───▶  compact→DAG (EXP-515/51

---

## ANNEXES

- **Annex I — The Axiomatic Metabolism** (`constitution/ANNEX_I_AXIOMATIC_METABOLISM.md`): canonical philosophical appraisal. What the engine genuinely achieves (detection-completeness + non-repudiable authority; execution fused with audit) and what it does not (it metabolizes signatures, not lies about the world). Non-normative; the code governs.
s bit-perfect, content-addressed, and auditable forever.

*See `GHOST_REGISTRY.md` for the catalogue of residuals and `EXPERIMENT_LEDGER.md` for the proof index.*
