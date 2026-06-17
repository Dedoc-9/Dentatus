# EXP-512 — Strain → Bethe Coupling (Fork ε)

**Protocol** `exp512-v1` · **Declaration hash** `dd86223ac4b68ff8d1cfcc208ae807edd9999ede8eea23755bbbe50d03292a37`
**Scope** `engine/validity.py` — ADDITIVE `bethe_citadel_strain_512` + `is_bethe_strain_512` only.
`state.py` / `operators.py` / `confluence.py` FROZEN. Orchestration in
`game/observability/multivelocity.py` (`citadel_strain_coupling`).

---

## A1 — Statement

Boundary shear strain (EXP-511) is a **deformation-energy drain** on the EXP-509 excitation
reservoir. A world that shears past a critical strain `ε_ref` overheats (`ΔS_cit < 0`) and is
rejected by the Citadel: mechanical instability is converted into an informational breach.

    frac    = min( (strain / ε_ref)² , 1 )          # elastic-energy fraction (quadratic, Hooke ½kx²)
    E*_eff  = β_Z · (1 − frac)                       # deformation energy sequestered from level density
    H_in    = 2√(a · E*_eff) / ln2,   a = a₀·d_stalk (FIXED),   H_out = log₂(N_f + N_γ)
    ΔS_cit  = H_in − H_out ,   admit ⇔ ΔS_cit ≥ 0

`strain = 0 ⇒ frac = 0 ⇒ E*_eff = β_Z ⇒` identical to `bethe_citadel_509` (exact recovery, Fork A [2]).

## A2 — Why this form (the design decision, recorded)

The coupling could have entered three ways; the choice is load-bearing.

| Channel | Form | Verdict |
|---|---|---|
| **Scale `a` by strain** (option b — "structural fatigue") | `a → a·g(strain)` | **REJECTED.** `a` is the fixed substrate schema mass (EXP-509). Making it state-dependent re-entangles the constant the engine deliberately froze — the EXP-509 double-count trap — and dissolves the friction. Strain is energetic, not structural; it must not touch `a`. |
| **Additive heat on `E*`** (option a, naive) | `E* → E* + κ·strain` | **WRONG SIGN.** Raising `E*` raises `H_in` → *easier* admission. The physics is the opposite: deformation removes energy from the level density. |
| **Deformation-energy drain on `E*`** (Fork ε, chosen) | `E*_eff = β_Z·(1−(strain/ε_ref)²)` | **CHOSEN.** Subtractive, quadratic (elastic), dimensionless single-knob, `a` and `N` keep their pure meanings, recovers EXP-509 at strain 0. |

**Three reasons the chosen form is principled, not arbitrary:**
1. **Elastic energy is quadratic.** Stored deformation energy is `U = ½ C ε²` (Hooke). A linear term
   would be ad hoc; the square is the physics. `E_strain_frac == (strain/ε_ref)²` is asserted (Fork A [5]).
2. **Gravitational backreaction.** Strain is a stress-energy contribution; minding backreaction, that
   energy must back-react on the *available* excitation — it is drawn down from the reservoir, not
   added. This is why the term is subtractive on `E*` rather than additive.
3. **Reservoir, not substrate.** Excitation `E* = β_Z` is the dynamical temperature; `a` is the fixed
   substrate. A dynamical quantity (strain) couples to the dynamical reservoir (`E*`), never to the
   constant (`a`). This keeps the EXP-509 invariant `a = a₀·d_stalk` intact (Fork A [4]).

## A3 — Operator placement & backreaction firewall

`bethe_citadel_strain_512` is a **pure** engine function (numbers in, numbers out). The game layer
measures the boundary strain and hands it in (`citadel_strain_coupling`):

    step (510) → SMOOTH/STRAIN (511) → reduce(max section strain) → bethe_citadel_strain_512 → verdict

Strain feeds the **verdict** (a read), never the forward state: it does not move leaves, alter the
coarse eigenvector, or change the forward `E*`. Like EXP-509's `bethe_gate`, the coupling is **opt-in**
(a separate function), so the EXP-509 default path is byte-unchanged (Fork A [8]) and the 30 prior
forks are untouched. This is the same A6 orthogonality as EXP-510/511 — strain is write-only w.r.t.
control.

## A4 — Verified friction

Fixed world (`E*=10`, `N=544`), rising strain (`ε_ref=0.5`):

    strain  0.00   0.10   0.20   0.30   0.40   0.50
    E*_eff 10.00   9.60   8.40   6.40   3.60   0.00
    ΔS_cit +5.91  +5.60  +4.65  +2.91  −0.09  −9.09
    admit    ✓      ✓      ✓      ✓      ✗      ✗

Crosses zero at strain ≈ 0.40; at `ε_ref` the reservoir is fully sequestered (`E*_eff=0`,
guaranteed reject). End-to-end (Fork A [7]): a shearing scene (strain 0.0092) is rejected, a rigid
scene (strain 0.0) admitted, with `ε_ref` calibrated between them.

## A5 — P_yz invariance

`strain` (Frobenius norm) and `β_Z` (norm-derived) are P_yz-invariant scalars, so `E*_eff`, `ΔS_cit`
and the verdict are reflection-invariant (Fork B, all 5).

---

## DEV NOTE — Ghost #46: ε_ref is scale-relative (strain is not yet dimensionless)

`strain = ‖Sym(L)‖_F` carries units of velocity-gradient (per-frame inverse length). Its magnitude
therefore depends on the world's characteristic shear *rate* and on `dt` — the synthetic lattice here
produces strains ~10⁻² while a galactic-scale fast-shear could produce very different numbers. As a
result **`ε_ref` is not a universal constant**; it must be calibrated to the engine's characteristic
strain (Fork A [7] calibrates it to the scene, the honest move). This is the analogue of the EXP-509
`a₀` calibration, but per-world rather than per-engine.

The residual ("ghost") is the missing **non-dimensionalisation** of strain. It is not yet an entity —
it surfaces only as the fact that the same `ε_ref` means different things in different worlds.

Mitigation path (Fork η below) is to normalise strain to a dimensionless shear number before the
coupling, e.g. `strain* = strain · dt` (strain-per-step) or `strain* = strain / ⟨ω⟩` (strain over a
characteristic vorticity/rotation rate), so that `ε_ref` becomes a true engine constant. Until then,
`ε_ref` is exposed as the per-world knob and `citadel_strain_coupling(..., eps_ref=...)` is explicit.

## Suggested improvements / forks

- **Fork η (dimensionless strain).** Normalise `strain* = strain·dt` (or `/⟨ω⟩`) so `ε_ref` is a
  universal engine constant; removes Ghost #46. Recommended next.
- **Fork θ (directional / anisotropic drain).** Drain only the excitation aligned with the principal
  strain axis (tensor `E*` rather than scalar), so a world can shear in a benign direction without
  paying the full thermodynamic penalty. Pairs with EXP-511 Fork δ (anisotropic halo).
- **Fork ι (per-section local Citadel).** Apply the drain per section (local `E*_s`, local `ΔS_cit,s`)
  rather than to one global max, so a single violent seam is rejected without condemning the whole
  manifold — a localized firewall. Ties to the EXP-506/507 sectioned architecture.

## Foreign-language note (rhetoric → code)

The chosen coupling is a *Verformungsenergie* (deformation-energy) drain: the *Verzerrung* (strain)
sequesters energy as *Spannungsenergie* (stress/strain energy, quadratic) out of the *Anregung*
(excitation `E*`), leaving the *Niveaudichteparameter* `a` untouched. The rejected option (b) confuses
*Ermüdung* (fatigue, a change to the substrate `a`) with *Anregungsverlust* (loss of excitation) — the
former mutates a constant, the latter draws down a reservoir. Only *Anregungsverlust* is admissible
here.
