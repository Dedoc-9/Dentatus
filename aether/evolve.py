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
