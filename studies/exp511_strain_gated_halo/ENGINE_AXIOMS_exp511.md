# EXP-511 — Strain-Gated Halo + Boundary Velocity Smoothing

**Protocol** `exp511-v1` · **Declaration hash** `943feae7c1f52a4e99564a692f7e01197f1168cde87e2ad752ae060bfa301268`
**Scope** GAME LAYER ONLY — `game/observability/multivelocity.py` (append) + `sectioned_fiedler.py`
(additive halo params). No `engine/*.py` edits.

---

## A1 — Why (the seam-tear under shear)

EXP-510 gives each section its own velocity `v_s`. When neighbouring sections shear, the EXP-506
stitched Fiedler — computed on instantaneous geometry — is still C⁰ *within* a frame, but the
per-section strain that we would use to widen the halo is computed from raw EMA velocities and
therefore **shimmers** frame-to-frame. EXP-511 smooths `v_s` across boundaries first, then gates the
halo width by the resulting strain, so the blend widens only where the world is actually deforming.

## A2 — Operator order (extends EXP-510; dual → dual)

    step (EXP-510) → SMOOTH(mass-momentum v̄) → STRAIN(Cauchy ‖Sym‖) → HALO(σ gate)

Every added stage is dual→dual. The gate modulates an **interpolation width** (an observability
parameter), never leaf geometry nor the coarse eigenvector `c`. Fork A [10] asserts the `step()`
forward trajectory is identical with or without the smoothing/halo path — the A6 backreaction
firewall holds.

## A3 — Mass-momentum smoothing (dual math ↔ code)

Mass is the section's **integrated volume** `m_s = Σ_{leaf∈s} vol(leaf)` — NOT leaf-count. Every
contributor (including self) enters as momentum `p = m·v`; neighbours carry a Gaussian distance
weight:

    w_d(s,s') = exp(−‖c_s − c_s'‖² / (2σ²))
    v̄_s = ( m_s·v_s + Σ_{s'∈N(s)} m_s'·w_d(s,s')·v_s' ) / ( m_s + Σ_{s'∈N(s)} m_s'·w_d(s,s') )

```python
wsum = float(tk["mass"]) if mode == "mass" else 1.0     # self enters as p = m*v
acc  = vk * wsum
for k2 in neighbours(k):
    w = exp(-d2/(2*sig*sig))
    if mode == "mass": w *= float(t2["mass"])           # volumetric mass (momentum weighting)
    acc += w * v2; wsum += w
v_bar = acc / wsum
```

Verified (Fork A [3]): a light sliver (mass 0.025) bordering a heavy bulk (mass 0.125, 5×) drifting
oppositely — raw `v_x=−0.00375` → mass-smoothed `−0.00025` (bulk momentum dominates) vs
distance-smoothed `−0.00263` (sliver counted as an equal). Momentum is conserved; the sliver cannot
shear-drag the bulk.

## A4 — Strain gate (dual math ↔ code)

    L_s = Σ_{s'∈N(s)} (1/|N|) (v̄_s' − v̄_s) ⊗ (c_s' − c_s) / ‖c_s' − c_s‖²
    strain_s = ‖½(L_s + L_sᵀ)‖_F
    σ_s ← σ_s^(506) · (1 + γ · strain_s)        # γ=0 ⇒ EXP-506 byte-identical

```python
base = clip(kappa*ell[s]*sext[s], leaf, max(sext[s],leaf))         # EXP-506 spectral-diameter halo
gain = 1.0 + (gamma_strain*float(strain[s]) if (strain is not None and gamma_strain) else 0.0)
sigma[s] = base * gain                                             # widen only at deforming seams
```

Verified: shear → mean σ `0.300 → 0.301…` (widened, Fork A [5]); rigid translation → `Δσ = 0`
(unchanged, [6]); `γ=0` → field+σ array-equal to EXP-506 ([2]).

## A5 — Backreaction firewall

`v̄` and `strain` are write-only w.r.t. control. The halo gain scales the partition-of-unity kernel,
so the fault zero-set (topology) is invariant — only its stitched smoothness changes. No operator
branches on `strain` to move leaves or alter `c`. This keeps EXP-511 inside the same orthogonality
discipline as EXP-510 A6.

## A6 — P_yz invariance

Under x→−x: velocity x-components flip, but `strain` (Frobenius norm), smoothed speeds, section mass
(volume), and the gated `σ_s` are invariant. Fork B verifies all four.

---

## DEV NOTE — Ghost #45: mass-churn & the count/volume confusion

Two failure modes that mass-weighting could have introduced, and how they are closed:

1. **Leaf-count is not mass.** The seductive error (and the literal wording of the original design
   question) is to weight by *leaf-count*. Count is a discretization artifact of the octree: subdivide
   a region and its count rises while the region is unchanged. Fork A [4] makes this concrete —
   subdividing the heavy section into 8× leaves of the same total volume leaves the smoothing
   **identical**. Had we weighted by count, the subdivided section would have read 8× the momentum and
   dragged the seam differently. Mass ≡ integrated **volume** (coarsening-invariant). This is the same
   discipline as EXP-509 (`a = a₀·d_stalk`, schema mass not leaf-count): never let a discretization
   count masquerade as a physical quantity.

2. **Mass shimmer under octant churn.** A leaf crossing a section boundary changes that section's raw
   volume discontinuously. If the smoothing weight tracked raw volume, the weight itself would
   shimmer — re-introducing the instability EXP-511 exists to remove. Fix: `m_s` is **EMA-stabilised**
   (`α=0.5`), so a sudden volume change moves the weight only halfway (Fork A [8]: a raw doubling
   `0.125→0.25` damps to `0.1875`). `m_s` is a dual, reported-only scalar; it never controls geometry.

Net effect (Fork A [7]): under alternating boundary jitter, mass-smoothed strain peak-to-peak is
`0.0096` vs raw `0.0223` — a 2.3× reduction in halo shimmer, the "kinematic healing" analogue of the
EXP-506/507 spectral healing.

## Suggested improvements / forks

- **Fork δ (anisotropic halo).** Gate not by `‖Sym‖_F` alone but by the principal strain *direction*:
  widen the halo only along the shear axis (elliptical Gaussian), keeping it tight across the
  fault-normal — sharper fault, smoother seam.
- **Fork ε (strain → Bethe coupling, EXP-509 bridge).** Treat `strain_s` as a local excitation term:
  a violently deforming region raises its `E* = β_Z` requirement, so high-shear seams must carry more
  budget or overheat. Unifies the kinematic and thermodynamic firewalls.
- **Fork ζ (predictive halo).** Gate by `strain_s + dt·∂ₜstrain_s` so the halo widens *before* the
  seam tears, using the velocity field's own time-derivative (still dual-only).

## Foreign-language note (rhetoric → code)

The mass-weighted boundary blend is an *Impulserhaltung* (momentum-conservation) operation: the
conserved quantity is *Impuls* `p = m·v`, not bare velocity, which is why self and neighbours enter
weighted by *Masse* (here the *Volumenmaß*, the volume measure — not *Anzahl*, the count). Naming the
weight *Masse-als-Volumen* rather than *Masse-als-Anzahl* is the whole correctness argument in one
word: only the measure is physical; the count is a *Diskretisierungsartefakt*.
