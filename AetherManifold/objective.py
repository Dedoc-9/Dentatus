"""
AetherManifold/objective.py — sample objectives with exact integer gradients (no autodiff, no float).

`procrustes(A, B)`: f(X) = ‖A·X − B‖²_F over X ∈ St(n,k); Euclidean gradient G = 2·Aᵀ(A·X − B). All
fixed-point. The minimum is 0 when A·X can equal B exactly on the manifold (the classic orthogonal
Procrustes / model-fitting problem).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cores import F


def fp(num, den=1):
    return F.to_fp(num, den)


def identity(n):
    return [[F.SCALE if i == j else 0 for j in range(n)] for i in range(n)]


def procrustes(A, B):
    At = [list(r) for r in zip(*A)]

    def grad(X):
        R = F.sub(F.matmul(A, X), B)
        return F.scalar(fp(2), F.matmul(At, R))

    def energy(X):
        R = F.sub(F.matmul(A, X), B)
        return sum(R[i][j] * R[i][j] for i in range(len(R)) for j in range(len(R[0])))

    return grad, energy
