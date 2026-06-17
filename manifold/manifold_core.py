"""
NGGV/manifold_core.py — state-as-manifold built ON TOP of the frozen Chronicle workbench.

This module treats computational state as a GRAPH embedded in a manifold and derives the content address
(`world_H`) from the graph's TOPOLOGY. It reuses the immutable Reality_Engine workbench read-only (we
import it; we never edit it).

DESIGN — the honest split (this is the whole point):
  * DIAMOND-HARD GATE  = EXACT graph predicates (union-find connectivity, bridge detection). Integer
    arithmetic, O(N+E), bit-for-bit deterministic, so it is safe to put inside the commit/replay path and
    use as Chronicle's precommitted invariant. "Would this transition fragment a critical subsystem?" is
    answered exactly, with no eigensolver.
  * SPECTRAL LAYER     = a SOFT, CAPTURED observable (Fiedler value lambda2, algebraic connectivity). It
    is a *margin* / early-warning, NOT a gate. It is computed with numpy, canonicalized, and recorded via
    the capture seam — NEVER inside world_H — because float eigendecomposition is not bit-identical across
    BLAS/LAPACK builds or architectures, and the Fiedler eigenvector's sign is only defined up to +/-1.

INTEGRITY != TRUTH (carried up from the workbench): lambda2 > 0 proves the GRAPH YOU BUILT is connected,
not that the system is safe. The gate is only as honest as the graph construction and the predicate.
"""
import os
import sys

# --- import the FROZEN cores read-only. As a sibling component, chronicle is at ../chronicle. ---
_WB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # Reality_Engine workbench root
sys.path.insert(0, os.path.join(_WB, "chronicle"))
import core as chronicle_core        # canonical_bytes, state_hash, Recorder, ruleset_hash, InvariantViolation


# ============================================================ topology -> identity (deterministic)
def normalize_graph(n, edges):
    """Canonical integer graph: n nodes (0..n-1), undirected edges as sorted unique (a,b) with a<b."""
    es = sorted({(min(a, b), max(a, b)) for a, b in edges if a != b})
    return int(n), es


def laplacian(n, edges):
    """Integer combinatorial Laplacian L = D - A for an UNWEIGHTED graph. All-integer -> no float drift."""
    n, es = normalize_graph(n, edges)
    L = [[0] * n for _ in range(n)]
    for a, b in es:
        L[a][b] -= 1
        L[b][a] -= 1
        L[a][a] += 1
        L[b][b] += 1
    return L


def world_hash(n, edges):
    """Content address of the engine = hash of its TOPOLOGY. Deterministic: integer Laplacian + edge set,
    serialized through the frozen Chronicle canonicalizer."""
    n, es = normalize_graph(n, edges)
    return chronicle_core.state_hash({"n": n, "edges": [list(e) for e in es], "L": laplacian(n, es)})


# ============================================================ EXACT gate (stdlib, replay-safe)
def _components(n, edges):
    p = list(range(n))
    def f(x):
        while p[x] != x:
            p[x] = p[p[x]]; x = p[x]
        return x
    for a, b in edges:
        p[f(a)] = f(b)
    return {f(i) for i in range(n)}


def is_connected(n, edges):
    n, es = normalize_graph(n, edges)
    return n <= 1 or len(_components(n, es)) == 1


def bridges(n, edges):
    """Exact bridge edges (removal disconnects). Iterative Tarjan; integer-only, deterministic."""
    n, es = normalize_graph(n, edges)
    adj = {i: [] for i in range(n)}
    for i, (a, b) in enumerate(es):
        adj[a].append((b, i)); adj[b].append((a, i))
    disc = [-1] * n; low = [0] * n; t = [0]; out = []
    for s in range(n):
        if disc[s] != -1:
            continue
        stack = [(s, -1, iter(adj[s]))]
        disc[s] = low[s] = t[0]; t[0] += 1
        while stack:
            u, pe, it = stack[-1]
            advanced = False
            for v, ei in it:
                if ei == pe:
                    continue
                if disc[v] == -1:
                    disc[v] = low[v] = t[0]; t[0] += 1
                    stack.append((v, ei, iter(adj[v]))); advanced = True; break
                else:
                    low[u] = min(low[u], disc[v])
            if not advanced:
                stack.pop()
                if stack:
                    pu = stack[-1][0]
                    low[pu] = min(low[pu], low[u])
                    if low[u] > disc[pu]:
                        out.append(tuple(sorted((pu, u))))
    return sorted(set(out))


# ============================================================ SPECTRAL observable (captured, never hashed)
def fiedler_value(n, edges, ndigits=9):
    """Algebraic connectivity lambda2 (2nd-smallest Laplacian eigenvalue). FLOAT + numpy: for AUDIT /
    MARGIN only. Rounded for display; must be CAPTURED (not recomputed) on replay. Returns None if numpy
    is unavailable — the gate never depends on this."""
    try:
        import numpy as np
    except Exception:
        return None
    n, es = normalize_graph(n, edges)
    if n == 0:
        return 0.0
    w = np.linalg.eigvalsh(np.array(laplacian(n, es), dtype=float))
    v = float(sorted(w)[1]) if n > 1 else 0.0
    if abs(v) < 1e-9:          # clamp eigensolver noise around the zero eigenvalue (avoids -0.0)
        v = 0.0
    return round(v, ndigits)
