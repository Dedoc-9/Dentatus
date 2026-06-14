# Reality Engine — EXP-301 Dentatus

Generative reality engine implementing a cellular sheaf state machine over a claim DAG.
State evolution is governed by a fixed operator pipeline with immutable hash-indexed states,
dual ghost channels, and preregistered validity predicates.

**License**: GNU Affero General Public License v3.0 — see `AGPL-3.0`

---

## Architecture

### State

`engine/state.py` — core state structures.

```
H_t = SHA256(Z_t ⊕ S_t ⊕ W_t ⊕ t ⊕ protocol_version)
G_t = Z_t − Π_{W_t}(Z_t)
S_{t+1} = α·S_t + (1−α)·G_t
```

`MuState` holds the claim DAG (`claims`, `entailments`), active leaf set `W_t`, and EMA ghost `S`.
Every state transition requires `seal()` before the hash `H_t` is accessible.
Dual ghost channels `S_A` (dims 0–7) and `S_C` (dims 8–11) are tracked independently (EXP-306+).

### Operator pipeline

```
μ → Lτ → Bτ → Rτ → Z → S → W → OBS
```

Each operator is stateless and depends only on declared inputs/outputs.
Cross-stage mutation outside the defined mapping is forbidden.

`engine/operators.py` implements:

| Operator | Study | kappa rule |
|----------|-------|------------|
| `apply_gamma_306` / `_recursive` | EXP-306 | additive: `kappa_child = kappa_parent * ω_i` |
| `apply_gamma_307` / `_recursive` | EXP-307 | shape operator trace: `tr(H_bbox) = Σ 2/l_i` |
| `apply_gamma_308` / `_recursive` | EXP-308 | area-weighted integral: `2(ly·lz/lx + lx·lz/ly + lx·ly/lz) / (lx·ly + ly·lz + lx·lz)` |
| `apply_gamma_309` / `_recursive` | EXP-309 | SPRT LOD gating on top of EXP-308; focal point update; ghost quarantine |

### Stalk schema — d=12

```
F(v) ∈ ℝ¹²  =  [Sector A (0-3) | Sector B (4-7) | Sector C (8-11)]

Sector A: [mass, r, g, b]          — photometric
Sector B: [x, y, z, w]             — affine position + weight
Sector C: [nx, ny, nz, kappa]      — centroid-outward unit normal + curvature
```

Restriction map `F` is block-diagonal 12×12; no cross-sector coupling.

### Validity predicates (EXP-308, 6 total)

| Predicate | Description |
|-----------|-------------|
| `is_valid` | `F @ stalk_parent == stalk_child` for all entailments |
| `is_valid_b` | Sector B barycentric weights sum to 1; `w=1` |
| `is_unit_norm` | `‖stalk[8:11]‖ = 1.0` for all d≥11 claims |
| `is_spatially_valid` | bbox containment on SPATIAL edges |
| `is_valid_block_diagonal_306` | no cross-sector coupling in F (d=12) |
| `is_valid_kappa_308` | `stalk[11] == kappa_integral(bbox)` for all claims with bbox |

State is valid only when all 6 predicates pass simultaneously.
On failure, execution reverts to the last valid hashed state.

### Ghost channel

```
G_t = Z_t − Π_{W_t}(Z_t)              residual (0 for lossless operators)
S_{t+1} = α·S_t + (1−α)·G_t           EMA accumulation (α = 0.85)

B(t)   = ‖S‖   / (‖Z‖   + ε)          global ghost ratio
B_A(t) = ‖S_A‖ / (‖Z_A‖ + ε)          sector A+B ghost ratio
B_C(t) = ‖S_C‖ / (‖Z_C‖ + ε)          sector C ghost ratio
η_AC   = |λ_A · λ_C| / (‖λ_A‖·‖λ_C‖ + ε)   sector coupling (EXP-308)
```

`G_t` is a numeric residual only — not an entity, not directly controlled.
Dual arithmetic (forward Z space vs dual S/G space) is never collapsed.

---

## Study series (EXP-301 → EXP-308)

| Study | Description | declaration_hash (first 16) |
|-------|-------------|----------------------------|
| EXP-301 | R⁴ symbolic generative engine | — |
| EXP-302 | R⁶ pos×col; sum conservation | — |
| EXP-303 | R⁹ pos×col×nrm; Gamma; bbox containment | — |
| EXP-304 | R⁸ dual-sector; Sector B barycentric | — |
| EXP-305 | R¹¹ triple-sector; Sector C unit-norm; P_yz; block-diagonal F | — |
| EXP-306 | R¹² curvature engine; centroid-outward normals; kappa additive; dual ghost S_A/S_C | `5a8e1afc590d8ffb` |
| EXP-307 | R¹² shape operator; kappa = tr(H_bbox); auto-payload recursive Gamma | `8e288c601093e1dd` |
| EXP-308 | R¹² integral curvature; kappa = area-weighted mean curvature; η_AC; bbox-hash payload | `ad5215b859de58d5` |

Each study is gate-locked before implementation. `SEED_DECLARATION_*.json` hashes are
immutable structural indices — not semantic labels.

---

## Coordinate conventions

- **Centroid-outward normal**: `n_child = normalize(centroid_child − centroid_parent)` — purely
  geometric, closes E-305-002 (P_yz exact).
- **P_yz mirror**: `x → −x` (polar dim 4), `nx → −nx` (axial dim 8), bbox x-axis reflected.
  kappa_integral is P_yz-invariant: extents `|hi[i]−lo[i]|` are preserved under x-reflection.
- **Bbox hash payload** (EXP-308+): `SHA256(bbox_lo_bytes ‖ bbox_hi_bytes ‖ depth_bytes ‖ index_bytes)[:16]`
  — spatially varying K_bound as geometric signal.

---

## Running the tests

```
# Dependencies
pip install numpy scipy

# Fork A — seed expansion and kappa validation
python run_seed_exp308.py

# Fork B — P_yz invariance
python run_p_invariance_exp308.py
```

All prior study runners (`run_seed_exp30{6,7}.py`, `run_p_invariance_exp30{6,7}.py`) remain
executable as regression checks.

---

## Dev notes

### Ghost non-zero signal

For lossless centroid-outward octree partitions, `G = 0` by construction
(children sum exactly to parent). `S_A` and `S_C` accumulate non-zero residuals only when
the active-leaf W_basis cannot fully reconstruct `Z` via lstsq — e.g., after asymmetric splits
or when kappa_child ≠ kappa_parent in non-additive regimes (EXP-307+).

### Recursive tree asymmetry under P_yz (ghost #1)

`apply_gamma_308_recursive` uses `_cost(mu.S)` at each node to gate budget. Since `S` evolves
differently for forward (nx=+0.6) vs mirror (nx=−0.6) seeds, the recursion trees are
structurally non-isomorphic — leaves occupy different bbox positions. Geometric pair-matching
is therefore inapplicable for recursive P_yz tests. The correct check is sorted kappa
distribution equality + per-predicate validation. Equal leaf counts confirm K-budget depth
profile symmetry.

### EPS_REL relative floor (EXP-308 rev)

`kappa_integral` uses `eps = max(lx, ly, lz) * 1e-9` as the per-axis regularization floor
instead of an absolute `1e-6`. For all normal extents (≥ 1e-3) the two floors are identical.
The relative floor is strictly correct for degenerate extents < 1e-7 where the absolute floor
would over-clamp relative to bbox scale, and is scale-invariant under uniform bbox rescaling.

### η_AC = 1.0 for symmetric partitions

For uniform octree splits, `lstsq(W_A, Z_A)` and `lstsq(W_C, Z_C)` both return equal-weight
coefficient vectors (all children contribute identically). Cosine similarity = 1.0 is the
correct result. The observable becomes informative only for asymmetric splits or deep
non-uniform recursions where Sector A and Sector C stalk geometry decouple.

### NTFS git workaround

`.git/config` may disappear between sessions on NTFS. Fix: run `git init` in the repo root
to reinitialize, then `git push --set-upstream origin main`.

### Forbidden operations

`ghost_direct_control`, `stalk_collapse`, `retroactive_confluence_cert`,
`budget_retroactive_adjustment`, `validity_predicate_shift`, `post_hoc_rewrite_rule_addition`.
Post-execution rule addition is forbidden. All predicates must be declared and locked in
`SEED_DECLARATION_*.json` before any operator is implemented.

---

## EXP-309 dev notes

### Ghost quarantine ghost #2

For lossless centroid-outward operators, G_C = 0 exactly (children sum to parent in Sector C). S_C therefore accumulates zero residual regardless of quarantine case. Quarantine becomes informative only when a non-lossless operator (e.g. asymmetric stalk injection) creates persistent G_C != 0.

### LOD_RELAXED validity_class propagation

validity_class is set on MuState (not on individual Claim objects). The recursive guard checks getattr(mu, "validity_class", "FULL_VALID") on the input state. A LOD_RELAXED input state blocks all further expansion of its active leaves. FULL_VALID states recurse normally.

### Focal point is not hashed

focal_point is a dynamic attribute on MuState, excluded from H_t. It is a mutable observer parameter, not part of the validity state. Changing focal_point between calls produces different LOD values and validity classes without invalidating the hash chain.

## EXP-310 dev notes

### KSG degeneracy guard (ghost #3)

KSG TE is undefined when any marginal has zero variance. Constant c_t (frozen S_C under LOD_RELAXED kappa bypass) triggers this:  returns 0.0 by convention when std(c) < 1e-15. This is the correct information-theoretic result: if S_C is frozen, no information flows from S_A to S_C (T_{A->C} = 0). The degeneracy guard makes the architectural quarantine guarantee machine-checkable.

### TE sign vs magnitude

KSG magnitude is biased ~5-50% depending on N. With the ghost history buffer at W=32, sign(delta_T_AC) is the reliable statistic (correct 100% of trials at W=64). Magnitude becomes reliable at N~2000. The preregistered threshold is: sign(delta_T_AC) is the primary observable; magnitude is logged but not asserted.

## EXP-309 open limits

| limit | description |
|-------|-------------|
| kappa face model | inscribed curvature κ_i = 2/l_i is flat-face; actual curvature of rounded bbox requires Monte Carlo surface sampling |
| η_AC interpretation | measures coefficient alignment, not information flow; EXP-309: directed mutual information I(S_A;S_C) across time |
| bbox-hash K_bound | spatially varying but not yet used to gate partition depth; EXP-309: K_bound(depth) feeds recursive termination directly |
| G_C non-zero signal | persistent G_C requires explicit non-lossless operator; EXP-309: design asymmetric partition |
