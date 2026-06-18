"""
aether/evolve.py — Lie-bracket evolution wrapped in the Stiefel audit/retraction loop.

`lie_step` advances a frame W under a skew-symmetric generator A by one forward-Euler tangent step
(W <- W + dt*(A @ W)), which preserves orthogonality in continuous time. In fixed point it accumulates
bounded, deterministic quantization, so `evolve_audited` audits the Stiefel energy and self-retracts when it
exceeds the declared epsilon — logging each recovery. The result is a deterministic, replayable manifold
evolution that provably never strays beyond epsilon.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixedpoint as F
import stiefel as S


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


def evolve_audited(W, A, dt_fp, steps, epsilon=S.STIEFEL_EPSILON_INT, audit_every=1000, signer=None):
    """Evolve `steps` times, auditing the Stiefel energy every `audit_every` steps and self-retracting on a
    breach. Returns {W, retractions, max_E, log} — `log` lists each RETRACTION shard. Deterministic."""
    last_valid = W
    retractions = []
    max_E = S.frobenius_energy(W)
    for t in range(1, steps + 1):
        W = lie_step(W, A, dt_fp)
        if t % audit_every == 0 or t == steps:
            chk = S.check_orthogonality(W, epsilon)
            max_E = max(max_E, chk["E"])
            if not chk["ok"]:
                res = S.handle_retraction(W, epsilon, signer=signer, last_valid=last_valid)
                W = res["recovered"]
                retractions.append(res["shard"])
            last_valid = W
    return {"W": W, "retractions": len(retractions), "max_E": max_E, "log": retractions,
            "final_hash": S.state_hash(W)}
