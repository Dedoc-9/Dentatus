# EXP-513 — Dimensionless Strain (Fork η)

**Protocol** `exp513-v1` · **Declaration hash** `e283bd260e380617500f9e6a7412633dc422c42ebd71086c460718771417f447`
**Scope** `engine/validity.py` — `bethe_citadel_strain_512` extended ADDITIVELY (`dt`, `vorticity`
params; `STRAIN_STAR_REF_512`, `_VORT_EPS_513` constants). `state.py`/`operators.py`/`confluence.py`
FROZEN. Closes Ghost #46.

---

## A1 — The problem (Ghost #46) and the fix

EXP-512's `strain = ‖Sym(L)‖_F` is a *rate* (units 1/time), so its magnitude is world- and
sampling-relative and `ε_ref` had to be calibrated per world. Fork η non-dimensionalises strain so
`ε_ref` becomes a single universal constant `STRAIN_STAR_REF`, locking the mechanical firewall into
the constitution beside `B_ent ≤ ε` and `ΔS_cit ≥ 0`.

Two non-dimensionalisations, selected by inputs (dimensional path unchanged when neither is given):

| Mode | Input | `strain*` | Property |
|---|---|---|---|
| **Shear-Courant** | `dt` | `strain · dt` | dimensionless **per-step** (CFL number). Unit-universal; scales with `dt`. |
| **Weissenberg** | `vorticity` | `strain / max(‖Ω‖, ε)` | dimensionless **and framerate-independent** (rate/rate). Consolidates EXP-510 vorticity. |

```python
if vorticity is not None:
    s_star = s / max(abs(vorticity), _VORT_EPS_513)   # Weissenberg: exact strain/|vort| above floor
    er = STRAIN_STAR_REF_512 if eps_ref is None else eps_ref
elif dt is not None:
    s_star = s * dt                                   # shear-Courant: per-step CFL number
    er = STRAIN_STAR_REF_512 if eps_ref is None else eps_ref
else:
    s_star = s                                        # dimensional (EXP-512 original)
    er = STRAIN_EPS_REF_512 if eps_ref is None else eps_ref
frac = min((s_star/er)**2, 1.0); E_eff = E*(1-frac)   # EXP-512 drain, now on the dimensionless strain*
```

## A2 — Precise invariance claims (be exact, not hand-wavy)

- **Shear-Courant** `strain·dt` is *dimensionless* and *unit-universal*, but it is a **per-step**
  quantity: the same physical shear sampled at finer `dt` yields a smaller `strain*` and is correctly
  *more permissive per step* (Fork A [3]). This is the right semantics for a per-step firewall and is
  the literal `strain·dt` requested — but it is **not** framerate-absolute.
- **Weissenberg** `strain/‖Ω‖` is *both* dimensionless *and* framerate-**absolute**: strain and
  vorticity are both intrinsic rates, so their ratio is invariant under any common sampling-rate
  scaling (Fork A [6]: `Wi=1.5` identical under ×{2, 0.5, 10}). This is the quantity that makes the
  "Truth of the engine" independent of framerate, and it is the genuine consolidation of EXP-510
  (vorticity) with EXP-512 (strain).

Physical reading: `Wi` is the **shear-to-spin ratio** — how much a region *deforms* versus merely
*rotates*. `Wi ≪ 1` rotation-dominated (rigid-ish, admit); `Wi ≈ 1` simple shear; `Wi ≫ 1`
shear-dominated (tearing, reject). It is the rheologists' Weissenberg number; here it gates existence.

## A3 — ε_ref governance (answering the design question)

**`STRAIN_STAR_REF` is a PROTECTED constitutional constant, NOT a free L1 tunable.** Two reasons:

1. **Firewall integrity.** A per-call `ε_ref` at the L1 API would let any caller set it arbitrarily
   high and *disable the mechanical firewall* — the same reason `FIREWALL_EPSILON`, the Citadel floor,
   and `a₀` are protected engine constants, not request parameters.
2. **Content-addressing.** `H_verified` is a hash over the firewall-gated state. If `ε_ref` were a free
   input, the same world would verify to different addresses under different knobs, fragmenting the
   DAG. A constitutional constant keeps one world → one address.

**Material variation is still possible — but as declared state, not a knob.** Different materials
(brittle crystal vs fluid nebula) legitimately have different critical strains. The correct channel is
a **bounded stiffness modulus** `χ ∈ (0, 1]` *derived from the stalk material sector* (Sector A, already
in the d=18 schema), scaling `ε_ref_eff = STRAIN_STAR_REF · χ`. Because `χ` is (a) bounded so it can
never disable the firewall and (b) a function of *declared state* rather than a free request field, it
respects the backreaction discipline: the law is fixed; the material *response* is a bounded function
of the world's own declaration. (Implementation deferred to a future fork; the governance is fixed
here.)

## A4 — Backreaction firewall & engine freeze

`strain*` feeds the **verdict** only — never leaf geometry, the eigenvector, or the forward `E*`. The
dimensional path is byte-unchanged, so EXP-512 and all prior forks stay green (Fork A [2], [8]). The
edit is additive params + two constants in `validity.py`; `state`/`operators`/`confluence` frozen.

## A5 — P_yz invariance

`strain` and `vorticity` are Frobenius-norm scalars (P_yz-invariant); `β_Z` is norm-derived. Hence
both `strain*` modes and the coupled `dS_cit` are reflection-invariant (Fork B, all 5).

---

## DEV NOTE — Ghost #47: the vorticity singularity (regularised by a floor, not an additive ε)

The Weissenberg ratio `strain/‖Ω‖` is singular where vorticity vanishes (pure shear, pure expansion,
or a momentarily irrotational seam). The naive guard `strain/(‖Ω‖ + ε)` is **wrong**: the additive ε
contaminates the ratio differently at different rate scales, so `Wi` is no longer *exactly*
scale-invariant — the framerate-independence (A2) breaks at the ε-th digit. This was caught by Fork A
[6] before it could enter the constitution.

The correct regulariser is a **floor**: `strain / max(‖Ω‖, ε)`. Above the floor it is *exactly*
`strain/‖Ω‖`, so the ratio is exactly scale-invariant; only at `‖Ω‖ < ε` (genuinely irrotational) does
the floor engage, sending `Wi → strain/ε` (large → reject), which is the physically correct verdict:
a deforming seam with *no* rotation to organise it is maximally non-rigid. The residual ("ghost") is
that `ε` sets the boundary between "irrotational" and "rotating" — an arbitrary model construct, not a
physical edge; pushing `ε → 0` is admissible and only sharpens that boundary.

## Suggested improvements / forks

- **Fork θ (bounded material stiffness χ).** Implement `ε_ref_eff = STRAIN_STAR_REF · χ(stalk_A)` with
  `χ ∈ (0,1]` derived from the photometric/material sector — per-material firewalls without exposing
  the constant. Directly realises A3.
- **Fork ι (per-section local Citadel).** Apply the drain per section (local `E*_s`, `Wi_s`) so a
  single violent seam is rejected without condemning the whole manifold (ties to EXP-506/507).
- **Fork κ (tensor Weissenberg).** Replace the scalar `Wi` with the eigenvalues of `Sym(L)·Ω⁻¹` so the
  firewall can distinguish shear *direction* relative to spin axis (pairs with EXP-511 Fork δ).

## Foreign-language note (rhetoric → code)

The framerate-absolute number is the *Weissenberg-Zahl* (`Wi = Scherrate / Drehrate`), the ratio of
*Scherung* (shear, the symmetric `Sym(L)`) to *Wirbelstärke* (vorticity, the antisymmetric `Ω`). The
per-step number is the *Courant-Zahl* (CFL). Naming them apart is the whole A2 distinction: the
*Courant-Zahl* is `dimensionslos` but `bildratenrelativ` (framerate-relative); only the
*Weissenberg-Zahl* is `bildratenunabhängig` (framerate-independent). The engine's constitutional
"Truth" should rest on the *Weissenberg-Zahl*.
