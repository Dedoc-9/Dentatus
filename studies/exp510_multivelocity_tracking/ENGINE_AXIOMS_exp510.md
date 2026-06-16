# EXP-510 — Multi-Velocity Section Tracking (Ghost #40)

**Protocol** `exp510-v1` · **Declaration hash** `5f83cb5ac6b907e1fc618707b4d500f5e3a0dea44522fa1b70d07e2ecf38e579`
**Scope** GAME LAYER ONLY — `game/observability/multivelocity.py`. No `engine/*.py` edits. Consumes
`sectioned_fiedler` + `dentatus.core`; never imports `engine.*` (Clean Room).

---

## A1 — The failure mode (Ghost #40)

`engine.operators.track_correspondence_505` keys every claim in **one** world frame offset by a
single `cumulative_motion` vector. That presumes the world translates as a rigid body. When sections
move at **different** velocities, one global offset cannot hold every section's keys stable:
matched-track counts collapse and the stitched Fiedler fault tears at the moving seams.

The fix is one velocity per section, each section tracked in its own co-moving frame.

## A2 — State variables (forward ⟂ dual)

Forward (geometry, **observed**, never mutated by the dual channel):

    leaves_t   : list[ {center:(3,), size:(3,)} ]   engine telemetry
    so_t, C_s  : section_of_leaf, section centroid   (assign_sections, observed)
    field_t    : stitched Fiedler per leaf           (sectioned_fiedler)

Dual (kinematics, **residual**, reported, never fed back as control):

    v_s        : per-section velocity      EMA of observed displacement
    Ĉ_s = C_s^prev + v_s·dt                predicted centroid (correspondence only)
    G_s = C_s^match − Ĉ_s                  kinematic ghost (Ghost #44)
    Skin_s     : EMA(G_s)                  observable only

## A3 — Operator order (stateless, declared I/O)

    μ(leaves) → SEC(assign) → PRED(Ĉ) → ASSOC(greedy gate) → VEL(EMA v) → GHOST(G,Skin) → OBS

No stage mutates forward geometry from the dual channel. **SEC runs on observed centers every
frame**, so the Fiedler operator never sees a velocity-displaced world — forward/dual orthogonality
(dual arithmetic separation, A6).

## A4 — Velocity & ghost update (dual math ↔ code)

Math (per matched section *s*, EMA constants α_v, α_g; observed displacement Δ = C_s − C_s^prev):

    v_s   ← α_v · v_s  + (1−α_v) · (Δ / dt)
    Ĉ_s   = C_s^prev + v_s · dt
    G_s   = C_s − Ĉ_s
    Skin_s ← α_g · Skin_s + (1−α_g) · G_s

Code (`multivelocity.step`):

```python
obs_v = tuple(_r((c[d] - t["centroid"][d]) / dt) for d in range(3))     # Δ/dt
v     = tuple(_r(alpha_v*t["v"][d] + (1-alpha_v)*obs_v[d]) for d in range(3))
g     = tuple(_r(c[d] - pred[tid][d]) for d in range(3))                # C - Ĉ  (Ghost #44)
skin  = tuple(_r(alpha_g*t["Skin"][d] + (1-alpha_g)*g[d]) for d in range(3))
```

## A5 — Kinematic decomposition (the pioneering observable)

`rigidity_R = ‖mean v‖ / mean‖v‖` is only a **coherence** measure — it cannot separate uniform
expansion or rotation (still rigid-ish) from true deformation. So we fit a linear velocity field over
the section centroids and split its gradient (Cauchy / Helmholtz):

    v(x) ≈ v₀ + L·(x − x̄),   L = dvᵢ/dxⱼ
    L = Sym + Ω,   Sym = ½(L+Lᵀ) (strain),   Ω = ½(L−Lᵀ) (vorticity)

| Observable | Definition | Reads |
|---|---|---|
| `translation` | ‖v₀‖ | bulk drift (rigid) |
| `vorticity` | ‖Ω‖_F | rotation rate (rigid) |
| `strain` | ‖Sym‖_F | **true non-rigidity** (deformation) |
| `divergence` | tr(L) | expansion/contraction (isotropic) |

Verified modes: rigid translation → `strain=0, vort=0, div=0`; isotropic expansion → `div>0, vort=0`;
simple shear → `strain=vort, div=0` (textbook); rotation → `vort ≫ strain`.

**Mindfulness on coarse-graining.** `L` is a property of the section centroids — a coarse sampling of
the continuum field. Its section boundaries are model constructs, not inherent limits; refine the
grid and `L` converges to the local velocity gradient. `div` is reported separately because a uniform
expansion is non-rigid yet structurally benign (isotropic), unlike anisotropic shear.

## A6 — Backreaction firewall (mind gravitational backreaction)

The hazard: `v_s` → `Ĉ_s` → association → membership → `v_s` is a closed loop; if prediction were
used to **relocate** leaves, the velocity estimate would drive the geometry it is measured from
(runaway backreaction). Firewall: prediction is used **only** for correspondence; section assignment
always uses observed centers. The dual channel (`v`, `G`, `Skin`) is **write-only** w.r.t. control —
no operator branches on `Skin`. Fork A [8] asserts the matched sequence is identical with/without the
Skin path, closing the loop (consistent with the standing rule: no control based solely on Gₜ).

## A7 — P_yz invariance

Under x→−x: `center.x`, `v.x`, `Ĉ.x`, `G.x` flip sign; `‖v‖`, `strain`, `vorticity`, `R`,
match/birth/death counts and the size-multiset are invariant. The structural hash is built **only**
from invariants (sorted speed multiset + scalar observables); signed x-components are excluded —
consistent with `track_dag_hash_505` / Ghost #27. Fork B verifies hash equality under reflection.

---

## DEV NOTE — Ghost #44: kinematic residual & section-assignment churn

Two new residuals appear with multi-velocity tracking:

1. **`G_kin` (the kinematic residual)** — `G_s = C_s^match − Ĉ_s`, the gap between predicted and
   observed section centroid. Under constant velocity it **decays** as the EMA velocity converges
   (verified `G_kin = [0.01, 0.005, 0.0025, …]`, halving per frame at α=0.5). It is *not* an entity;
   it is a number. It is accumulated into `Skin` purely as an observable and **never** read by any
   control branch. Treating `G_kin` as a thing to "correct" would re-open the A6 backreaction loop.

2. **Octant-assignment churn (the boundary artifact)** — leaves crossing a section (octant) boundary
   reassign discontinuously. This is the coarse-graining caveat made operational: the boundary at
   `int(c·grid)` is an arbitrary model construct, not a physical edge. Symptom: a symmetric/degenerate
   seed (e.g. a perfectly symmetric cube, frame 0 of a static world) has a **degenerate Fiedler**
   (tied eigenvalues) whose sign pattern is an arbitrary tie-break — `fault_continuity` reads ~0.5
   across the symmetry-breaking transition off that seed. This is noise from the degeneracy, not a
   fault tear; under sustained differential motion (symmetry already broken) continuity holds ≥0.75.
   Mitigation path (future): track sections as persistent entities by track-membership rather than
   re-deriving octants each frame, so identity survives boundary crossings.

## Suggested improvements / forks

- **Fork α (strain-gated halo).** Feed `strain_s` into the EXP-506 halo width: widen the
  partition-of-unity Gaussian where deformation is high so the stitched fault stays C⁰ across
  shearing seams. (Observable→observable; still no forward backreaction.)
- **Fork β (per-section Bethe coupling, ties to EXP-509).** Treat `strain` as an excitation source:
  high deformation raises the local `E* = β_Z` requirement, so a violently deforming region must
  carry proportionally more budget or it overheats (rejection). Unifies kinematics with the
  thermodynamic firewall.
- **Fork γ (Hungarian association).** Replace greedy gate matching with an optimal assignment
  (Jonker–Volgenant) for dense, fast-moving section fields; keep the deterministic tie-break for
  bit-stability.

## Foreign-language note (rhetoric → code)

The connection that keeps the fault "healed" across moving sections is the differential-geometric
*Zusammenhang* (parallel-transport connection) — here realized as the per-section co-moving frame
that transports each section's keys along its own velocity. The deformation reading is the
*Verzerrungstensor* (strain tensor, `Sym`); rotation is the *Wirbelstärke* (vorticity, `Ω`). Naming
them precisely keeps the implementation honest: only `Verzerrung` (strain) is true non-rigidity;
`Wirbelstärke` and translation are rigid and must not be counted as deformation.
