"""
salience/predictor.py — the CHEAP possibility predictor (O(local), no shadow rollout).

True possibility pressure (airlock/horizon) costs ~56x a sim step — far too expensive to compute per frame
per region. A conventional engine never ray-traces the future to schedule; it uses cheap features that
*correlate* with it. So does this: a small, fitted, O(local) estimator of possibility pressure from local
features only (actor count, candidate/reachable-transition count, interaction pairs, geometry, constraint
headroom). Occasional expensive `horizon` rollouts act as GROUND TRUTH to CALIBRATE the cheap weights.

The win is not accuracy — it is that a slightly-worse signal that is ~1000x cheaper can keep a Possibility
Atlas FRESH, while true possibility can only refresh rarely and goes stale in a changing world. Stdlib only.
"""


def features(actor_count, candidate_count, interaction_pairs, geometry, constraint_headroom=0):
    """The O(local) feature vector — everything here is a cheap local read, never a shadow rollout."""
    return [actor_count, candidate_count, interaction_pairs, geometry, constraint_headroom]


def _solve(A, b):
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c])); M[c], M[p] = M[p], M[c]
        if abs(M[c][c]) < 1e-12: M[c][c] = 1e-12
        for r in range(n):
            if r != c:
                f = M[r][c] / M[c][c]
                for k in range(c, n + 1): M[r][k] -= f * M[c][k]
    return [M[i][n] / M[i][i] for i in range(n)]


def calibrate(feature_rows, true_pressures, ridge=1e-6):
    """Fit cheap features → true possibility (sparse expensive ground truth). Returns a weight vector with
    intercept. This is the only place `true` possibility is consulted — at calibration, not at runtime."""
    Xd = [[1.0] + list(x) for x in feature_rows]
    p = len(Xd[0])
    A = [[sum(Xd[r][i] * Xd[r][j] for r in range(len(Xd))) + (ridge if i == j and i > 0 else 0.0)
          for j in range(p)] for i in range(p)]
    b = [sum(Xd[r][i] * true_pressures[r] for r in range(len(Xd))) for i in range(p)]
    return _solve(A, b)


def predict(weights, feats):
    """Estimate possibility pressure from local features — O(local), no rollout. Clamped non-negative."""
    x = [1.0] + list(feats)
    return max(sum(weights[i] * x[i] for i in range(len(weights))), 0.0)
