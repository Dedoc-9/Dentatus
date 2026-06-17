# EXP-522 — Oriented Nucleation (Fork ψ)

**Protocol** `exp522-v1` · **Declaration hash** `851a4f654a262c2ac4e5ad73c9d67558337315b6714cb399963a67e5c601d3b8`
**Scope** NO engine edits. `game/agency/nucleation.py` uses `dentatus.core` (χ, bethe, cholesky) +
`dentatus.semantic`. Engine FROZEN. **Closes Ghost #54.**

---

## A1 — The missing nucleus

EXP-521 re-crystallisation *amplifies residual order* (`g > 1` widens an existing spread). A fully
isotropic state (`Σ ∝ I`, `χ = 1`, reached by a *total* melt) has no residual axis to amplify — the
geodesic rescale is the identity, so it is amorphous-locked. Oriented nucleation supplies the missing
orienting field from the current **strain tensor**: the manifold re-crystallises along the principal
axis of `Sym(L)`. The world decides its new crystal structure from the forces acting on it — dendrites
aligning to the flow.

## A2 — Nucleation geometry (dual math ↔ code)

```
Sym(L) = V_s · diag(s) · V_sᵀ                 (strain tensor; s eigenvalues, V_s principal axes)
d  = s − mean(s)                               (centred ⇒ Σdᵢ = 0 ⇒ det preserved)
Σ' = V_s · diag( c · exp(β · d/‖d‖) ) · V_sᵀ,  c = geomean(eig Σ)   (isotropic scale retained)
β  : bisection so χ(Σ') = χ_target             (the EXP-521 hysteresis target)
```

```python
sv, sV = eigh(sym_L); d = sv - sv.mean(); dn = d/norm(d)
Sigma_b = (sV * (c * exp(beta*dn))) @ sV.T              # eigenbasis = strain axes; det = c^3 preserved
beta = bisect(b in [0, BETA_MAX] : chi(Sigma_b) <= chi_target)
```

Because the new covariance shares the strain eigenbasis and its largest variance sits on the largest
strain eigenvalue, the **covariance major axis coincides with the strain major axis** — verified
`alignment_cos = 1.0` (Fork A [3]), `χ: 1.0 → 0.751`, det preserved (Fork A [6]).

## A3 — Dispatch & guards (the freeze leg is now total)

| Material state | Operator | Behaviour |
|---|---|---|
| residual order (`spread ≥ ε`) | EXP-521 re-crystallisation | amplify existing order |
| amorphous (`spread < ε`) + anisotropic stress | **EXP-522 oriented nucleation** | nucleate along strain axis |
| amorphous + isotropic stress (`‖d‖ < ε`) | — | `no_orienting_field` (no preferred axis → stays amorphous) |

The hysteresis gate (EXP-521 Schmitt logic) still applies: nucleation fires only with headroom
`χ_cur − χ_required ≥ hysteresis` (Fork A [7]) and stops a margin above the melt boundary (Fork A [8]).
Together, EXP-521 + EXP-522 make the freeze leg **total** — every fluid state, residual or fully
amorphous, can re-order (Fork A [9]: `diamond → total-melt χ=1 → nucleate χ=0.751`).

## A4 — P_yz & determinism

Under joint reflection of the material (Sector D) and the strain tensor `Sym(L)`, the covariance
eigenvalues and the strain/covariance axis alignment are preserved, so `χ_after`, `β`, `alignment_cos`
and `det` are P_yz-invariant (Fork B). Bit-stable (Fork A [10]).

---

## DEV NOTE — Ghost #54 closed; the residual is now physical, not a lock

Ghost #54 (the amorphous lock) is resolved: an amorphous state re-crystallises given a strain field.
The only remaining "hold" case — `no_orienting_field` — is now **physically correct rather than a
limitation**: a perfectly isotropic material under perfectly isotropic stress has, by symmetry, *no*
preferred direction to crystallise along, so it must stay amorphous. That is the right answer, not a
gap. (A hydrostatic-only world cannot spontaneously break its own rotational symmetry.)

A subtle modelling choice worth recording: nucleation aligns the covariance's *largest* variance with
the *largest* strain eigenvalue (extension axis). This is the "grow along the tension" convention;
a compression-led material would use `−d`. The sign is a declared convention, not a hidden degree of
freedom — flip it and the crystal aligns to the compression axis instead. (Cross-reference EXP-511
Fork δ / EXP-513 Fork κ if a future anisotropic-χ tensor needs the full orientation, not just the axis.)

## Suggested improvements / forks

- **Fork Ϡ (nucleation rate / undercooling).** Make `β` (order regained) depend on how far below the
  melt point the stress sits (deeper undercooling → faster, finer nucleation), reproducing the
  classical nucleation-rate curve.
- **Fork Ϣ (poly-crystalline domains).** For a sectioned multi-leaf world, nucleate each section along
  its *local* strain axis → grain boundaries where neighbouring crystal orientations disagree
  (ties to the EXP-506 stitched fault).

## Foreign-language note (rhetoric → code)

Oriented nucleation is *gerichtete Keimbildung*: an *amorph* (amorphous) state forms a *Keim* (nucleus)
along the *Hauptachse* (principal axis) of the *Verzerrungstensor* (strain tensor), the *Erstarrung*
(solidification) following the *Fluss* (flow). With no *Vorzugsrichtung* (preferred direction) — isotropic
stress — there is *kein Richtungsfeld* (no orienting field) and the state *bleibt amorph* (stays
amorphous), which is *symmetriebedingt korrekt* (correct by symmetry), not a *Sperre* (lock).
