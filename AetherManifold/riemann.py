"""
AetherManifold/riemann.py — deterministic Riemannian gradient descent on the Stiefel manifold St(n,k).

The classical hazard: on a curved manifold you cannot subtract tangent vectors that live in different tangent
spaces, and naive linear updates "leak" off the manifold (a frame loses orthonormality). The fix, done here
ENTIRELY in fixed-point integers (no float drift):

  * Tangent projection:  P_X(Z) = Z − X · sym(XᵀZ),  sym(A) = (A + Aᵀ)/2    (project a Euclidean gradient
    onto the tangent space T_X St so the step stays geometrically valid).
  * Retraction:          X ← GramSchmidt_int(X − η · P_X(G))                (re-anchor onto the manifold; the
    integer Gram-Schmidt from `aether` self-corrects the constraint each step).

Because every matmul/transpose/symmetrize is the same fixed-point integer op, the whole trajectory is
deterministic and content-addressable — the same seed + η + steps reaches the identical minimum on any
machine, and the path is a replayable shard.

HONEST BOUND: deterministic means *reproducible*, not *infinite precision* — fixed-point quantizes by a
fixed, known rule, so observed instability is attributable to the algorithm + that fixed quantization, not to
random hardware noise. Convergence to a *local* minimum is what's proven; the *global* optimum is not.
(integrity ≠ truth.)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cores import F, ST, canon, SCALE


def transpose(M):
    return [list(r) for r in zip(*M)]


def sym(M):
    return [[(M[i][j] + M[j][i]) // 2 for j in range(len(M[0]))] for i in range(len(M))]


def proj_tangent(X, Z):
    """P_X(Z) = Z − X·sym(XᵀZ). Projects a Euclidean gradient onto T_X St(n,k). Fixed-point."""
    XtZ = F.matmul(transpose(X), Z)          # k×k
    return F.sub(Z, F.matmul(X, sym(XtZ)))   # n×k


def ortho_defect(X):
    """Integer ‖XᵀX − I_k‖_∞ in fixed-point units. 0 for an exactly orthonormal frame; tiny after retraction."""
    G = F.matmul(transpose(X), X)
    k = len(G)
    return max(abs(G[i][j] - (SCALE if i == j else 0)) for i in range(k) for j in range(k))


def retract(X):
    """Re-anchor onto St(n,k) via aether's integer Gram-Schmidt (column-wise; self-correcting)."""
    return ST.gram_schmidt_integer(X)


def state_hash(X):
    return canon.canon_hash({"X": X})


def optimize(X0, grad_fn, eta_fp, steps, energy_fn=None):
    """Riemannian GD. Returns {X, hashes (per step), defects, energies, final_defect}. Deterministic."""
    X = retract([row[:] for row in X0])
    hashes = [state_hash(X)]
    defects = [ortho_defect(X)]
    energies = [energy_fn(X)] if energy_fn else []
    for _ in range(steps):
        rg = proj_tangent(X, grad_fn(X))
        X = retract(F.sub(X, F.scalar(eta_fp, rg)))
        hashes.append(state_hash(X))
        defects.append(ortho_defect(X))
        if energy_fn:
            energies.append(energy_fn(X))
    return {"X": X, "hashes": hashes, "defects": defects, "energies": energies, "final_defect": ortho_defect(X)}
