# EXP-514 — Epistemic Materialism (Fork θ)

**Protocol** `exp514-v1` · **Declaration hash** `99eda360b4e85bd8bf8ff7da6815e5c2bf15b77f7eced542d45303f0bce7398a`
**Scope** `engine/validity.py` — ADDITIVE `material_compliance_chi_514` + `chi` param on
`bethe_citadel_strain_512` (+ `CHI_MIN_514`, `CHI_ENTROPY_W_514`). `state`/`operators`/`confluence`
FROZEN. Realises the governance fixed in EXP-513 A3.

---

## A1 — Thesis (a material is a filter for truth)

In a traditional engine a material is a shader or a physical constant. Here it is a **boundary
condition for the world's own existence**: the compliance `χ` derived from the stalk's Sector D
covariance spectrum sets how much shear the manifold can *logically survive* before the Citadel
overheats. The constitution (`STRAIN_STAR_REF`) is universal; `χ` is the world's declared mechanical
response within it.

## A2 — Continuous map (NOT a lookup table)

Sector D `= stalk[12:18]` (log-Cholesky) reconstructs `Σ = L Lᵀ` (3×3 SPD, `cholesky_from_stalk_401`).
`χ` is a smooth function of its eigenvalues `λ₁ ≥ λ₂ ≥ λ₃ > 0`:

    p_i = λ_i / Σλ                                  # normalised spectrum
    η   = −Σ p_i ln p_i / ln n        ∈ [0,1]       # spectral entropy   (disorder)
    gap = 1 − λ₂/λ₁                   ∈ [0,1)       # spectral gap       (ordering)
    χ   = clip( w·η + (1−w)·(1−gap), χ_min, 1 )     # compliance

```python
ev  = sorted(|eigvals(Σ)|, desc); p = ev/ev.sum()
eta = -(p*log(p)).sum()/log(n);  gap = 1 - ev[1]/ev[0]
chi = clip(w*eta + (1-w)*(1-gap), chi_min, 1.0)
```

Continuity verified (Fork A [4]): a `1e-3` Sector-D perturbation moves `χ` by `5e-4` — no discrete
jumps. Materials live on a **continuum of stability envelopes**, not a palette of labels.

| Material | Σ spectrum | η | gap | χ | behaviour |
|---|---|---|---|---|---|
| **water** | isotropic `[1,1,1]` | 1.0 | 0.0 | **1.0** | survives high Wi |
| **granite** | mild anisotropy | 0.76 | 0.65 | 0.56 | intermediate |
| **diamond** | ordered `[54.6, .14, .14]` | 0.03 | 0.998 | **0.05** (floor) | shatters at tiny shear |

## A3 — The pioneering inversion: stiff = fragile

`ε_ref_eff = STRAIN_STAR_REF · χ`. Because `χ ≤ 1`, a material can only **narrow** the constitutional
window, never widen it. The consequence is the design's most counter-intuitive (and correct) feature:
a **stiff material is more fragile**. Diamond (ordered, low `χ`) has a *narrow admissibility window* —
the slightest shear pushes `ε_ref_eff → 0.025`, `frac → 1`, `E*_eff → 0`, reject. Water (`χ = 1`) sits
at the constitutional ceiling and survives. Fork A [6]: at the same `Wi = 0.30`, water admits
(`ΔS = +14.9`), diamond shatters (`ΔS = −9.09`). The material *is* the truth filter.

## A4 — Phase change of reality (reported, not enacted)

The firewall reports the **phase-change target** — the minimum compliance to survive the present
shear:

    frac_max     = 1 − (H_out·ln2/2)² / (a·E)            # admissible deformation fraction at this E*,N
    χ_required   = strain* / (STRAIN_STAR_REF · √frac_max)
    admit ⇔ χ_world ≥ χ_required

Fork A [7]: `χ_required = 0.630`; `diamond 0.05 < 0.630 ≤ water 1.0`. A diamond sheared past its limit
must **re-compile to a material with χ ≥ 0.630** (solid → fluid) to continue existing. The engine
*reports* the target but never auto-mutates the world's Sector D (A6) — enacting the transition is a
game-layer decision, keeping the firewall a pure read.

## A5 — Dimensional governance (you cannot cheat physics)

`STRAIN_STAR_REF` is a protected constant; `χ` is a function of *declared state* (the Sector D bits of
`H_state`), bounded in `[χ_min, 1]`. You cannot make stone behave like water via an API knob — there
is no knob. To gain water's mechanical freedom you must **change the bits of the world's definition**
to a manifold whose covariance spectrum *is* disordered, and pay the entropic cost in every other
sector that depends on Sector D. The constitutional statement: *you cannot have the structural
benefits of Stone with the mechanical freedom of Water without paying the Entropic Tax.* Fork A [8]:
passing `χ = 5.0` is clipped to `1.0` — no bypass.

## A6 — Backreaction firewall & P_yz

`χ` feeds the **verdict** (a read of declared state); it never mutates geometry, the eigenvector, the
forward `E*`, or the world's stalk. `χ = None` ⇒ byte-identical to EXP-513 (Fork A [9]). Under x→−x,
`Σ → PΣPᵀ` is a similarity transform, so its eigenvalues — and hence `χ`, `χ_required`, the verdict —
are P_yz-invariant (Fork B, all 5).

---

## DEV NOTE — Ghost #48: the compliance/stiffness inversion & the floor

1. **Sign inversion (the trap).** Intuition says "stiffer ⇒ higher number." Here the bounded quantity
   that multiplies `ε_ref` must be a **compliance** (`χ ≤ 1`, so it can only narrow, never bypass), so
   **stiff ⇒ low χ**. A future contributor who wires `χ` as "stiffness" (high = stiff) will invert the
   firewall — diamonds would become indestructible and the bound `ε_ref_eff ≤ ε_ref` would break,
   admitting an API bypass. The compliance convention is load-bearing, not cosmetic. Stiffness, if
   ever reported for UX, is a *derived* `1 − χ`, never the multiplier.

2. **The χ_min floor.** The stiffest material keeps a tiny non-zero window (`χ_min = 0.05`) so a
   degenerate spectrum never produces a literally-zero window that would reject even a perfectly rigid
   world. (At `strain* = 0`, `frac = 0` regardless of `χ`, so rigid worlds always admit; the floor
   only bounds the *shear* tolerance.) The floor's exact value is a model construct, not a physical
   edge — pushing `χ_min → 0` only sharpens the most-fragile limit.

3. **Reported ≠ enacted.** `χ_required` is a target, not an action. The engine deliberately does not
   enact the solid→fluid re-compile (that would be the dual channel mutating declared state — a
   backreaction violation). The residual is the gap between the reported target and a game-layer
   transition policy; closing it is Fork λ.

## Suggested improvements / forks

- **Fork λ (enacted phase change).** A game-layer policy that, on `χ_world < χ_required`, re-declares
  Sector D toward an isotropic spectrum (solid→fluid) and re-hashes `H_state` — an explicit, witnessed
  state transition, never an automatic engine mutation.
- **Fork μ (anisotropic χ tensor).** Replace scalar `χ` with a compliance *tensor* from Σ's
  eigenvectors, so a material can be stiff along one axis and compliant along another — directional
  fragility, pairing with EXP-511 Fork δ / EXP-513 Fork κ.
- **Fork ν (cross-sector tax).** Couple `χ` to Sector A/C so that lowering compliance (stiffening)
  raises photometric/curvature cost — making the "Entropic Tax" of A5 an explicit, measured price.

## Foreign-language note (rhetoric → code)

`χ` is *Nachgiebigkeit* (compliance), not *Steifigkeit* (stiffness): the bounded multiplier must be
the *Nachgiebigkeit* so it can only *verengen* (narrow) the window. The map reads the covariance's
*Eigenwertspektrum* — its *Unordnung* (disorder, `η`) and *Ordnungslücke* (ordering gap) — to set how
much *Verzerrung* the *Materie* can survive. The thesis is *erkenntnistheoretischer Materialismus*
(epistemic materialism): *Materie ist ein Wahrheitsfilter* — matter is a filter for truth.
