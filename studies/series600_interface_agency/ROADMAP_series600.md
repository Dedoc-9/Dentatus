# Dentatus Series 600 — Interface & Agency Roadmap

**The "API of Reality": turning the verified world-state core into an LLM-pilotable platform.**

Author: Daniel J. Dillberg — bigdilly95@gmail.com
Ground truth: HEAD `50e5750`. Series 300–500 complete (EXP-301…505). Output style: state
variables, operators, transformations only. No new semantics introduced below the engine layer.

---

## 0. What already exists (the contract to build on)

Series 600 does not modify the core. It exposes it. The L0 operators and their I/O are frozen:

| Capability | Operator (engine) | Output observables |
|---|---|---|
| Partition + homeostasis | `apply_gamma_503_recursive` | `β_Z_eff, B_A, B_D, lc` |
| Manifold observation | `phi_ent_observe(degree_normalize=True)` | `G_ent, S_ent, B_ent, N_edges, λ₂` |
| Spectral fault modes | `spectral_ent_project` | `B_ent_spectral, λ_modes, fiedler_vector` |
| Firewall | `is_manifold_501` (ε=0.8) | `bool` admissibility |
| Covariance ↔ stalk | `cholesky_from_stalk_401` / `is_valid_covariance_401` | `Σ`, PD validity |
| Cross-scene memory | `persist_scene_504` / `SeedMemory` | `S_ent, B_ent_spectral, H_seed` |
| Moving-claim tracks | `track_correspondence_505` | `track DAG, continuity, H_dag` |

Invariants the API must preserve: P_yz machine precision (δ≤1e-14), hash continuity,
dual-space separation (S_ent ⟂ S_A/S_D ⟂ primary scalars), ghost closure, observable purity.

---

## 1. Layered architecture

```
L4  MCL Observability (dashboard / WebXR)        consumes observables only
L3  Agency Loop        (LLM iterate-to-stable)   reads ghost feedback, proposes revisions
L2  Semantic Compiler  (physical-property JSON)  intent -> SEED_DECLARATION (deterministic)
L1  Stateless Reality API (JSON over operators)  content-addressed, SeedMemory in/out
L0  Engine Core        (Series 300-500)          FROZEN operator contract
```

Each layer depends only on the layer below and emits a hash that links into the world DAG.
No layer mutates a lower layer's state outside its declared mapping (the engine's own rule,
lifted to the stack).

---

## 2. Objective 1 — Semantic Stalk Mapping (L2)

### 2.1 Problem
The LLM must not emit `l21 = 0.866`. It must emit *physical properties*. The compiler is a
deterministic function `intent → declaration`; the LLM speaks physics, the compiler speaks stalk.

### 2.2 Property → sector map

| Physical property (LLM vocabulary) | Stalk target | Transform |
|---|---|---|
| mass / density | A[0] | direct |
| material / color | A[1:4] | palette → rgb |
| position / extent | B[4:7], bbox | direct + octree domain |
| surface orientation | C[8:11] | unit normal |
| edge sharpness / curvature | C[11] (κ) | `kappa_integral` |
| **anisotropic stress / shear** | **D[12:18]** | **inverse log-Cholesky (below)** |
| focus / attention / budget | Zeeman `B`, `K_budget` | direction + magnitude |

### 2.3 The hard one — shear/stress → Sector D (VERIFIED)

A physical stress intent is a *Sollwert* (target setpoint) covariance ellipsoid: principal
stresses `(σ₁,σ₂,σ₃)` and orientation `R`. The compiler inverts the engine's forward map:

```
Math                                   Code (EXP-602 compiler core)
Σ* = R · diag(σ²) · Rᵀ                 D = np.diag(sigma_axes**2); Sigma = R @ D @ R.T
L  = chol(Σ*)                          L = np.linalg.cholesky(Sigma)
stalk[12:15] = log(diag L)             [log(L[0,0]), log(L[1,1]), log(L[2,2]),
stalk[15:18] = (L21, L31, L32)          L[1,0], L[2,0], L[2,1]]
```

This is the exact inverse of `cholesky_from_stalk_401`. **Verified round-trip** for
"high-shear landing pad" (σ=[3,2,0.4], 35° in-plane tilt): `max|Σ_engine − Σ*| = 8.88e-16`,
`is_valid_covariance_401 = True`, shear term `Σ_xy = 2.35` recovered. The semantic layer is
machine-precision invertible against the real engine — no approximation.

### 2.4 Example compile

```
intent: "docking bay, landing pad with high shear stress, sharp rim, focus the camera on the pad"
  -> pad claim:   A[0]=density, C[11]=κ_low(flat), D = invCholesky(Σ_shear)   [Sollwert above]
  -> rim claim:   C[11]=κ_high (sharp edge)
  -> Zeeman B  =  unit vector toward pad centroid;  K_budget high near pad
  -> SEED_DECLARATION{...}  ->  H_decl (links intent_hash -> declaration_hash in the DAG)
```

### 2.5 Fork / pivot (debate)
- **A. Free natural language → stalk** (one learned model). Flexible, opaque, breaks hash purity.
- **B. Raw stalk access.** Auditable, but the LLM should not hand-author log-Cholesky.
- **C (recommended). Structured physical-property JSON → deterministic compiler.** The LLM emits
  a typed intent (`{claim, property, value}`), the compiler is rule-based and reproducible.
  Keeps determinism + hash continuity; gives the LLM a physical vocabulary; an "escape hatch"
  field allows raw sector overrides for power users (logged, not default).

---

## 3. Objective 2 — Stateless Reality API (L1)

### 3.1 Why stateless is natural here
The engine already keeps *all* evolving state as caller-tracked primary scalars
(`bze_ema_prev`, `maint_latched`, `B_ent_spectral`, `cumulative_motion`, `SeedMemory`). The API
inherits this: the client owns the state; the server is a pure function of (input + memory).

### 3.2 Endpoints (1:1 with operators)

```
POST /v1/compile   intent.json                       -> SEED_DECLARATION + H_decl
POST /v1/observe   {declaration|DAG, B, K_budget,     -> {S_A, S_D, B_A, B_D, B_ent,
                    seed_memory?}                          B_ent_spectral, lambda_2,
                                                           is_manifold_501, worst_ratio,
                                                           H_t, seed_memory'}
POST /v1/step      {…, scene_n}                       -> observe + {beta_Z_eff, healing, H_seed}
POST /v1/track     {prev_memory, claims}              -> {continuity, track DAG, H_dag}
GET  /v1/state/{H_t}                                  -> content-addressed state retrieval
```

The DAG is the database: states are content-addressed by `H_t`; `GET /state/{H_t}` is a
deduplicated, immutable store. No mutable server state.

### 3.3 The agency feedback loop ("feeling the manifold")

```
design = compile(intent)
loop:
    obs = observe(design)
    if obs.is_manifold_501 and obs.lambda_2 >= λ_min and obs.B_ent_spectral < ε_design:
        return design                       # mathematically stable world
    design = revise(design, obs)            # LLM reads B_ent (tear), lambda_2 (fault),
                                            # fiedler_vector (where), worst_ratio (which claim)
```

The LLM does not guess stability — it *measures* it. `λ₂` (Fiedler) reports global connectivity,
`fiedler_vector` localizes the fault line, `B_ent_spectral` reports tectonic stress, the firewall
is the hard gate. This is the core value: validity is enforced, not hoped for.

### 3.4 Outer-loop backreaction (mind the gradient)
The agency loop is itself a feedback system: design responds to observables that respond to
design. Unbounded, it can oscillate (the design analogue of EXP-404 overshoot). **Bound it** with
an agency latch (lift the EXP-409 hysteresis idea to L3): cap iterations, require monotone
`B_ent_spectral` decrease, and freeze on a satisfied firewall. Backreaction stays bounded because
`Ω_fb_ent = B_ent/(1+B_ent) < 1` already holds at L0.

### 3.5 Hard prerequisite — Ghost #27 (determinism)
Content-addressability requires bitwise-reproducible `H_t`. Today the gamma recursion carries
~1e-14 claim-id-order noise (timestamp-seeded ids). **EXP-601 must add deterministic id seeding**
(provenance hash, no wall-clock) so identical input → identical `H_t` bit-for-bit. Until then the
API is content-addressed only at the norm-based structural-index resolution (1e-6), which is fine
for the dashboard but not for a dedup store.

---

## 4. Objective 3 — MCL Observability UI (L4)

Pure consumer of `/observe` and `/step` responses. No new semantics; renders observables.

| Panel | Source | Render |
|---|---|---|
| Manifold Firewall (EXP-502) | `B_ent`, ε=0.8, `worst_ratio` | gauge + per-claim heatmap; red on tear |
| Healing Curve (EXP-504) | `B_ent_spectral` over scenes | time series; tear markers; α_persist decay overlay |
| Spectral Fault Lines (EXP-503) | `fiedler_vector`, `λ₂` | v₂ painted on octree; fault surface; λ₂ trend |
| Homeostasis (Φ_fb) | `β_Z_eff, B_A, B_D, latch` | push-pull bars + latch indicator |
| Track DAG (EXP-505) | `continuity`, track edges, motion | claim tracks across scenes; motion vectors |

**3D / VR (WebGL → WebXR):** octree leaves as boxes; Sector D covariance as oriented ellipsoids
(`Σ = L·Lᵀ`); the Fiedler fault rendered as a bisecting surface; tears glow where
`worst_ratio > ε`. The engine emits geometry (bboxes) + `Σ`; the UI only paints. This is the
"Better UE5" boundary: Dentatus is the verified substrate, the renderer is downstream.

A read-only dashboard is an MVP deliverable (mock data → live API). VR is a later track.

---

## 5. Objective 4 — Galactic Persistence

### 5.1 EXP-506 — Multi-Velocity Tracking (Ghost #29)
EXP-505 assumes one global translation (centroid shift). Independent motion needs per-track
velocity + association. The constants `_R_GATE_505`, `_GRID_505` are already declared for it.

```
predict:   p̂_track = p_track + v_track          (per-track velocity state)
associate: nearest curr claim to p̂_track within r_gate, via spatial-hash buckets (GRID)
update:    v_track ← (1-β)·v_track + β·(p_curr − p_track)     (alpha-beta filter)
```

P_yz: velocities reflect (`v_x → −v_x`); association is isometry-equivariant. Fork: alpha-beta
(cheap) vs Kalman (covariance-aware, pairs naturally with Sector D). Recommend alpha-beta first;
Kalman when occlusion/clutter appears.

### 5.2 EXP-507 — Streaming World-Sections (Ghost #30, new)
A star system exceeds memory. Partition the world into spatial-hash super-sections; keep only
active sections resident; serialize inactive sections to the content-addressed store keyed by
`H_t` (the DAG *is* the store — load on demand). Reuse existing machinery:
- LOD: distant sections at coarse octree depth (EXP-309 SPRT LOD already exists).
- Eviction: `decay_away` on unloaded sections (EXP-504 Ghost #23 mechanism).
- Local Fiedler: per-section `λ₂` instead of global O(N³) (real-time at scale).

Result: bounded resident memory; persistence and dedup for free via hash-indexing.

---

## 6. Series 600 study roadmap

| Study | Title | Gate / dependency |
|---|---|---|
| EXP-601 | Deterministic IDs + Stateless Reality API | fixes Ghost #27; bitwise `H_t` reproducibility |
| EXP-602 | Semantic Compiler (property JSON → declaration) | inverse log-Cholesky (verified); needs 601 |
| EXP-603 | Agency Loop (iterate-to-stable) + agency latch | needs 602; bound outer backreaction |
| EXP-604 | MCL Observability dashboard (read-only → live) | consumes 601; parallel to 603 |
| EXP-506 | Multi-velocity tracking (Ghost #29) | extends 505; independent of 60x |
| EXP-507 | Streaming world-sections + LOD eviction (Ghost #30) | needs 506 + 601 store |
| EXP-608 | Allosteric mapping (long-range Σ coupling) | needs 603; spectral modes carry the signal |
| EXP-609 | World DAG merge (git-like authoring) | needs 601 content-addressing |
| EXP-610 | Multi-agent authoring / shared worlds | needs 603 + 609 |

**Allostery note (EXP-608, project brief):** the sheaf coboundary already couples face-adjacent
claims; allostery = a tear/binding at site A shifting `Σ` at distant site B *through the manifold*.
The carrier is the low-Fiedler-mode `B_ent_spectral` (EXP-503): perturb a slow mode at A and it
propagates along the fault network to B. The mechanism is built; EXP-608 only exposes it.

### Recommended critical path (MVP first)
```
EXP-601 (API + determinism)  ──►  EXP-602 (semantic compiler)  ──►  EXP-603 (agency loop)
                              └─►  EXP-604 (dashboard, parallel)
   ──►  first "promptable stable world" demo  ◄── MVP milestone
Then scale:  EXP-506 ─► EXP-507  (galactic streaming)   |   EXP-608/609/610 (agency depth)
```
Defer streaming and multi-agent until the single-world prompt→stable loop is proven end to end.

---

## 7. Debate — path to a usable next-gen reality engine

1. **Renderer or physics oracle?** Dentatus emits no pixels. It is a verified world-state oracle;
   UE5/Three.js consume its bboxes + `Σ`. Keep the separation — Dentatus is the Standard Model,
   rendering is downstream. The differentiator vs generative-mesh tools: *mathematical validity is
   enforced by the firewall*, not hoped for after the fact.
2. **How much raw access for the LLM?** Recommend semantic-only (Fork C, §2.5) with a logged escape
   hatch. Raw log-Cholesky authoring by an LLM is a correctness and hash-purity hazard.
3. **Determinism vs throughput.** Content-addressability is the value proposition; pay for it.
   EXP-601 deterministic ids may serialize some recursion, acceptable for a verified store.
4. **Real-time vs batch at scale.** Global `λ₂` is O(N³). Use per-section local Fiedler (EXP-507)
   and recompute only on `lc`-transition (the EXP-409 latch makes those rare). Real-time becomes a
   cache-validity problem, not a compute wall.
5. **Why the firewall is the unlock.** `is_manifold_501` is the constraint that lets an LLM author
   safely: it cannot prompt an unstable/torn universe into being — the physics refuses. That hard
   guarantee, plus stateful healing memory that follows moving claims, is what makes an autonomous
   author *trustable*. The agency loop converges to validity because validity is measurable
   (`B_ent`, `λ₂`) and gated (`ε=0.8`), not aesthetic.

**Bottom line.** The core ("the teeth") is done and verified. Usability is three deterministic
layers away: a stateless API (601), a semantic compiler (602, math already verified), and a
feedback dashboard (604) — then the LLM closes the loop (603). Galactic streaming (506/507) and
multi-agent authoring (608–610) are scale and depth, not new physics.
