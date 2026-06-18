"""
aether/evolve.py — Lie-bracket evolution wrapped in the Stiefel audit/retraction loop, with the
Stage-B dual ghost channel.

`lie_step` advances a frame W under a skew-symmetric generator A by one forward-Euler tangent step
(W <- W + dt*(A @ W)), which preserves orthogonality in continuous time. In fixed point it accumulates
bounded, deterministic quantization, so `evolve_audited` audits the Stiefel energy and self-retracts when it
exceeds the declared epsilon — logging each recovery.

CANONICAL PIPELINE (Stage B):  μ(A) → Lτ(lie_step) → [Π_W measure → G → S] → Rτ(retraction, on breach)
    Zₜ = lie_step(Wₜ₋₁,A,dt)        the running, off-manifold forward frame   (canonical Z)
    Wₜ = Π_W(Zₜ)                    its on-manifold projection                (canonical W)
    Gₜ = Zₜ − Wₜ                    the ghost residual (instrumented, not destroyed)
The forward Z trajectory and the retraction control are UNCHANGED from Stage A — the ghost measurement
never writes back to Z (Π_W is run for measurement every `measure_every` steps; Rτ is applied only on an
energy breach). So `final_hash` (the legacy W-only identity) stays byte-identical; `structural_hash`
(Hₜ = HASH(μ⊕Z⊕S⊕W⊕protocol_version)) is the new, additive Stage-B identity that includes the ghost.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixedpoint as F
import stiefel as S
import ghost as Gh
import spd as SP


def is_skew_symmetric(M):
    n = len(M)
    viol = [{"i": i, "j": j} for i in range(n) for j in range(n) if M[i][j] != -M[j][i]]
    return (not viol, viol)


def lie_bracket(A, B):
    """[A,B] = A@B - B@A. With symmetric fixed-point truncation, the bracket of two skew matrices is skew."""
    return F.sub(F.matmul(A, B), F.matmul(B, A))


def lie_step(W, A, dt_fp):
    """One tangent step W <- W + dt*(A @ W)."""
    return F.add(W, F.scalar(dt_fp, F.matmul(A, W)))


def evolve_raw(W, A, dt_fp, steps):
    """Evolve with NO audit/retraction -- lets the fixed-point frame drift off the manifold. Used to
    *demonstrate* drift; production evolution uses evolve_audited."""
    for _ in range(steps):
        W = lie_step(W, A, dt_fp)
    return W


def _project(W):
    """Π_W for MEASUREMENT only (no write-back). Returns the projection, or None on rank failure."""
    try:
        return S.gram_schmidt_integer(W)
    except S.StiefelError:
        return None


def evolve_audited(W, A, dt_fp, steps, epsilon=S.STIEFEL_EPSILON_INT, audit_every=1000, signer=None,
                   alpha_fp=Gh.ALPHA_DEFAULT, measure_every=None):
    """Evolve `steps` times. The forward Z path and retraction CONTROL are unchanged; the ghost channel
    is pure instrumentation:

      * every `measure_every` steps (default = audit_every — a DECLARED coarse-graining of the ghost
        stream, not an inherent boundary): measure Gₜ = Zₜ − Π_W(Zₜ), accumulate Sₜ via EMA, and sample
        ‖Gₜ‖ for the η_CLT diagnostic. Measurement is taken on the PRE-retraction frame (= Zₜ).
      * audit CONTROL (unchanged): every `audit_every` steps, if E > epsilon, self-retract and log a shard.

    Returns the Stage-A fields plus the dual channel: S (ghost EMA), B_t, eta_clt, ghost_samples,
    measure_gaps, structural_hash (Hₜ, the new identity), and final_hash (legacy W-only, byte-identical).
    Deterministic. S, B_t, eta_clt are OBSERVABLES — they never gate Z.
    """
    m = audit_every if measure_every is None else measure_every
    cur = W
    last_valid = W
    retractions = []
    max_E = S.frobenius_energy(W)
    Sg = Gh.zeros_like(W)                      # ghost accumulator (dual space), starts at 0
    norm_stream = []                           # ‖Gₜ‖ samples for η_CLT
    measure_gaps = 0                           # rank-failure measurement skips (recorded, never hidden)

    for t in range(1, steps + 1):
        cur = lie_step(cur, A, dt_fp)          # Zₜ — forward, off-manifold (UNCHANGED arithmetic)

        if t % m == 0 or t == steps:           # ---- ghost measurement (pure, pre-retraction) ----
            proj = _project(cur)               # Π_W(Zₜ)
            if proj is None:
                measure_gaps += 1
            else:
                G = Gh.ghost_residual(cur, proj)
                Sg = Gh.ema_matrix(Sg, G, alpha_fp)
                norm_stream.append(Gh.frob_norm(G))

        if t % audit_every == 0 or t == steps:  # ---- audit CONTROL (unchanged) ----
            chk = S.check_orthogonality(cur, epsilon)
            max_E = max(max_E, chk["E"])
            if not chk["ok"]:
                res = S.handle_retraction(cur, epsilon, signer=signer, last_valid=last_valid)
                cur = res["recovered"]
                retractions.append(res["shard"])
            last_valid = cur

    # ---- end-of-run observables + dual identity ----
    B_t = Gh.backreaction(Sg, cur)
    eta = Gh.clt_eta(norm_stream)
    proj_end = _project(cur) or cur
    structural = Gh.structural_hash(A, cur, Sg, proj_end, Gh.PROTOCOL_VERSION)

    return {"W": cur, "retractions": len(retractions), "max_E": max_E, "log": retractions,
            "final_hash": S.state_hash(cur),                 # legacy W-only identity — byte-identical
            "structural_hash": structural,                   # Hₜ = HASH(μ⊕Z⊕S⊕W⊕pv) — Stage-B identity
            "S": Sg, "B_t": B_t, "eta_clt": eta,
            "ghost_samples": len(norm_stream), "measure_gaps": measure_gaps,
            "protocol_version": Gh.PROTOCOL_VERSION}


def evolve_spd_audited(P, D, dt_fp, steps, margin_tol=SP.PD_FLOOR, horizon=64, alpha_fp=Gh.ALPHA_DEFAULT,
                       measure_every=None, uniform_every=None):
    """Stage C — evolve a covariance P on the SPD cone under a symmetric drift generator D
    (P ← symmetrize(P + dt·D)), with an E-DRIVEN ADAPTIVE retraction cadence and a PURE ghost channel.

    CONTROL (E-driven only): each step computes the cheap Gershgorin lower bound on λ_min (the gate
    observable). The expensive Cholesky retraction Π_SPD fires only when that margin has dropped below
    `margin_tol` OR is *predicted* to cross it within `horizon` steps (linear extrapolation of its
    decrease). So projection effort tracks geometric drift instead of firing uniformly. `uniform_every`,
    if given, additionally reports how many retractions a fixed-cadence policy WOULD have done — the
    latency comparison.

    GHOST (observable only): every `measure_every` steps (default = horizon; a declared coarse-graining)
    measure G = Z − Π_SPD(Z), accumulate S via EMA, sample ‖G‖ — these NEVER drive the cadence.

    Returns the final P, adaptive retraction count, the cheap-gate check count, S/B(t)/η_CLT, and the
    structural hash Hₜ = HASH(D ⊕ Z ⊕ S ⊕ W ⊕ aether-spd/1). Deterministic.
    """
    m = horizon if measure_every is None else measure_every
    cur = P
    retractions = 0
    uniform_retractions = 0
    Sg = Gh.zeros_like(P)
    norm_stream = []
    g_prev = SP.gershgorin_margin(cur)
    min_margin = g_prev

    for t in range(1, steps + 1):
        cur = symmetrize_add(cur, D, dt_fp)            # Zₜ — drifted covariance (forward)

        if t % m == 0 or t == steps:                   # ---- ghost measurement (pure, pre-retraction) ----
            proj = SP.project_spd(cur)
            G = Gh.ghost_residual(cur, proj)
            Sg = Gh.ema_matrix(Sg, G, alpha_fp)
            norm_stream.append(Gh.frob_norm(G))

        g = SP.gershgorin_margin(cur)                  # ---- cheap GATE signal (drives cadence) ----
        min_margin = min(min_margin, g)
        rate = g_prev - g                              # per-step decrease (>0 ⇒ heading to boundary)
        predict_breach = rate > 0 and (g - margin_tol) < rate * horizon
        if g < margin_tol or predict_breach:           # ---- adaptive retraction CONTROL ----
            cur = SP.project_spd(cur)
            retractions += 1
            g = SP.gershgorin_margin(cur)
        g_prev = g

        if uniform_every and (t % uniform_every == 0):
            uniform_retractions += 1

    B_t = Gh.backreaction(Sg, cur)
    eta = Gh.clt_eta(norm_stream)
    W_proj = SP.project_spd(cur)
    structural = Gh.structural_hash(D, cur, Sg, W_proj, SP.SPD_PROTOCOL)
    return {"P": cur, "retractions": retractions, "uniform_retractions": uniform_retractions,
            "min_margin": min_margin, "final_hash": SP.state_hash(cur),
            "structural_hash": structural, "S": Sg, "B_t": B_t, "eta_clt": eta,
            "ghost_samples": len(norm_stream), "protocol_version": SP.SPD_PROTOCOL}


def symmetrize_add(P, D, dt_fp):
    """One forward SPD-drift step: P ← symmetrize(P + dt·D). D symmetric ⇒ stays symmetric; the cone
    constraint (positive-definiteness) is what can drift, and the retraction restores it."""
    return SP.symmetrize(F.add(P, F.scalar(dt_fp, D)))
