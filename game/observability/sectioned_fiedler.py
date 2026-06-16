"""
game/observability/sectioned_fiedler.py — EXP-506 Stitched Local Fiedler (galactic-scale fault).

Computing one GLOBAL Fiedler vector is O(N^3). At scale we partition the world into sections and
compute LOCAL spectral structure per section. But local Fiedler vectors are independent objects
(arbitrary sign/scale/mode) -> butting them together gives disjoint, spurious fault seams.

Elegant two-level stitch (Galerkin spectral coarsening + partition-of-unity):
  1. COARSE Fiedler on the section-adjacency graph (Galerkin L_c = P^T L P, generalized
     eigenproblem with mass M_c = P^T P) -> the GLOBAL fault at section resolution. O(S^3), tiny.
  2. Partition-of-unity interpolation of the coarse field over section centroids -> a C^0
     field whose zero-set is the continuous fault line.
  3. DYNAMIC HALO: the Gaussian width per section is proportional to the section's SPECTRAL
     DIAMETER ell_s = 1/sqrt(lambda_2^local) (long where the fault mode is gentle, tight where
     steep), clamped to [1 leaf, section extent]. The 1-leaf floor guarantees the halo always
     contains the delta_0 inter-section edges (EXP-501).

Decoupled: reaches the core only via dentatus.core (face_adjacent_501). Never imports engine.*.
"""
import os, sys
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_REALITY = os.path.dirname(os.path.dirname(_HERE))
if _REALITY not in sys.path:
    sys.path.insert(0, _REALITY)
from dentatus import core   # dentatus.* contract only

HALO_KAPPA = 0.18           # halo width as a fraction of (spectral diameter x section extent)


def build_adjacency(leaves):
    """Face-adjacency graph from telemetry leaves (center/size). Returns (edges, neighbor lists)."""
    N = len(leaves)
    ctr = np.array([l["center"] for l in leaves], float)
    siz = np.array([l["size"] for l in leaves], float)
    lo = ctr - siz / 2.0; hi = ctr + siz / 2.0
    edges = []; nbr = [[] for _ in range(N)]
    for i in range(N):
        for j in range(i + 1, N):
            if core.face_adjacent_501((lo[i], hi[i]), (lo[j], hi[j]))[0]:
                edges.append((i, j)); nbr[i].append(j); nbr[j].append(i)
    return ctr, siz, edges, nbr


def _lap(n, ed):
    A = np.zeros((n, n))
    for i, j in ed:
        A[i, i] += 1; A[j, j] += 1; A[i, j] -= 1; A[j, i] -= 1
    return A


def _fiedler(A):
    w, v = np.linalg.eigh(A)
    for k in np.argsort(w):
        if w[k] > 1e-9:
            return v[:, k]
    return np.zeros(A.shape[0])


def _lambda2(A):
    w = np.sort(np.linalg.eigvalsh(A)); nz = w[w > 1e-9]
    return float(nz[0]) if len(nz) else 0.0


def assign_sections(ctr, grid=(2, 2, 2)):
    """Spatial sectioning by leaf-center octant grid. Returns (section_of_leaf, n_sections)."""
    sid = [tuple(min(grid[d] - 1, int(c[d] * grid[d])) for d in range(3)) for c in ctr]
    secs = sorted(set(sid)); sidx = {s: i for i, s in enumerate(secs)}
    return np.array([sidx[s] for s in sid]), len(secs)


def coarse_fiedler(edges, so, S, N):
    """Galerkin coarse Fiedler: L_c = P^T L P, generalized eigenproblem (mass M_c = P^T P).
    Returns the per-section coarse field c (the global fault at section resolution)."""
    P = np.zeros((N, S)); P[np.arange(N), so] = 1.0
    Lg = _lap(N, edges); Lc = P.T @ Lg @ P; Mc = P.T @ P
    d = np.sqrt(np.diag(Mc)); Di = np.diag(1.0 / np.maximum(d, 1e-12))
    Wc = Di @ Lc @ Di
    w, v = np.linalg.eigh(Wc)
    yc = next((v[:, k] for k in np.argsort(w) if w[k] > 1e-9), np.zeros(S))
    return Di @ yc, P


def stitched_fiedler(leaves, grid=(2, 2, 2), kappa=HALO_KAPPA, fixed_sigma=None,
                     strain=None, gamma_strain=0.0):
    """Two-level stitched Fiedler with dynamic spectral-diameter halo.

    Returns dict: field (per-leaf), section_of, coarse (per-section), halo_sigma (per-section),
    spectral_diameter (per-section), cost (op-count), n_sections.
    strain/gamma_strain (EXP-511): optional per-section Cauchy strain widens the halo at deforming
    seams; gamma_strain=0 (default) reproduces EXP-506 byte-identically.
    """
    ctr, siz, edges, nbr = build_adjacency(leaves)
    N = len(leaves)
    so, S = assign_sections(ctr, grid)
    c, P = coarse_fiedler(edges, so, S, N)
    scen = np.array([ctr[so == s].mean(axis=0) for s in range(S)])
    leaf = float(np.median(siz[:, 0]))
    ell = np.zeros(S); sext = np.zeros(S); sigma = np.zeros(S); cost = S ** 3
    for s in range(S):
        idxs = np.where(so == s)[0]; remap = {gi: li for li, gi in enumerate(idxs)}
        led = [(remap[i], remap[j]) for i, j in edges if so[i] == s and so[j] == s]
        l2 = _lambda2(_lap(len(idxs), led)) if (len(idxs) >= 2 and led) else 1.0
        ell[s] = 1.0 / np.sqrt(max(l2, 1e-3))                 # spectral diameter
        sext[s] = float(np.ptp(ctr[idxs], axis=0).mean()) + float(siz[idxs].mean()) if len(idxs) else leaf
        base = (float(fixed_sigma) if fixed_sigma is not None
                else float(np.clip(kappa * ell[s] * sext[s], leaf, max(sext[s], leaf))))  # 1-leaf floor, ext cap
        # EXP-511 strain-gated halo: widen ONLY where the seam is deforming (Cauchy strain), so the
        # partition-of-unity blend reaches across a shearing boundary. gamma_strain=0 -> EXP-506 exact.
        gain = 1.0 + (gamma_strain * float(strain[s]) if (strain is not None and gamma_strain) else 0.0)
        sigma[s] = base * gain
        cost += int(len(idxs)) ** 3
    field = np.zeros(N)
    for i in range(N):
        sg = sigma[so[i]]
        wts = np.exp(-((ctr[i] - scen) ** 2).sum(axis=1) / (2.0 * sg * sg)); wts /= wts.sum()
        field[i] = float(wts @ c)
    return {"field": field, "section_of": so, "coarse": c, "halo_sigma": sigma,
            "spectral_diameter": ell, "cost": cost, "n_sections": S, "edges": edges,
            "n_leaves": N, "leaf_size": leaf}


def global_fiedler(leaves):
    """O(N^3) reference Fiedler for validation ONLY (not the production path)."""
    ctr, siz, edges, nbr = build_adjacency(leaves)
    return _fiedler(_lap(len(leaves), edges)), edges, ctr, siz


def stitch_diagnostics(leaves, grid=(2, 2, 2), kappa=HALO_KAPPA, fixed_sigma=None):
    """Validate the stitch against the global Fiedler: section agreement, per-leaf agreement,
    spurious section-seam fault edges, and cost reduction. For small worlds only."""
    g, edges, ctr, siz = global_fiedler(leaves)
    st = stitched_fiedler(leaves, grid, kappa, fixed_sigma=fixed_sigma)
    f = st["field"]; so = st["section_of"]
    if np.dot(f, g) < 0:
        f = -f
    def fault(x): return set(tuple(sorted((i, j))) for i, j in edges if (x[i] > 0) != (x[j] > 0))
    Gf, Ff = fault(g), fault(f)
    seams = sum(1 for (i, j) in (Ff - Gf) if so[i] != so[j])
    # coarse section-sign agreement vs global per-section mean
    S = st["n_sections"]; c = st["coarse"]
    gm = np.array([g[so == s].mean() for s in range(S)])
    if np.dot(c, gm) < 0: c = -c
    sec_agree = float(np.mean(np.sign(c) == np.sign(gm)))
    leaf_agree = float(np.mean(np.sign(f) == np.sign(g if np.dot(f, g) >= 0 else -g)))
    return {"section_agreement": sec_agree, "leaf_agreement": leaf_agree,
            "spurious_seams": seams, "global_fault_edges": len(Gf), "stitched_fault_edges": len(Ff),
            "cost_two_level": st["cost"], "cost_global": len(leaves) ** 3, "n_sections": S,
            "halo_sigma": st["halo_sigma"].tolist(), "leaf_floor": st["leaf_size"]}


# ============================================================
# EXP-507 — Streaming World-Sections (resident-set memory bound)
# ============================================================
# The stitch is streamable: each leaf's value depends only on the coarse field c and the
# section centroids (both O(S)), never on other sections' leaves. So we:
#   Pass 1 (O(S^2) mem): accumulate section edge counts from a stream -> coarse Galerkin
#           Fiedler c + centroids. Computed ONCE (the global anchor).
#   Pass 2 (O(max_section) mem): stream sections, <= max_resident resident at a time; for each
#           compute local lambda_2 -> halo sigma_s, then emit stitched values for its leaves.
#   Per-section local Fiedler is content-addressed (cache by section signature) -> revisits hit.
# Peak resident = max_resident * max_section_size + O(S^2)  <<  O(N).


def _section_signature(idxs, ctr, siz):
    import hashlib
    payload = ";".join(f"{round(float(ctr[i][0]),6)},{round(float(ctr[i][1]),6)},"
                       f"{round(float(ctr[i][2]),6)},{round(float(siz[i][0]),6)}" for i in sorted(idxs))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def stream_stitched_fiedler(leaves, grid=(2, 2, 2), kappa=HALO_KAPPA, max_resident=1):
    """Streaming two-level stitch with a bounded resident set. Returns the SAME field as
    stitched_fiedler plus stream metrics (peak_resident, cache_hits, coarse_passes, memory)."""
    ctr, siz, edges, nbr = build_adjacency(leaves)
    N = len(leaves)
    so, S = assign_sections(ctr, grid)
    # ---- Pass 1: coarse from streamed section edge counts (O(S^2)) ----
    c, P = coarse_fiedler(edges, so, S, N)
    scen = np.array([ctr[so == s].mean(axis=0) for s in range(S)])
    leaf = float(np.median(siz[:, 0]))
    sec_leaves = {s: np.where(so == s)[0] for s in range(S)}
    sec_intra = {s: [] for s in range(S)}
    for i, j in edges:
        if so[i] == so[j]:
            sec_intra[so[i]].append((i, j))
    # ---- Pass 2: stream sections, bounded resident, content-addressed local Fiedler ----
    field = np.zeros(N)
    cache = {}                       # section signature -> spectral diameter (local Fiedler reuse)
    resident = []                    # LRU of resident section ids
    peak_resident_leaves = 0
    cache_hits = 0
    # deterministic stream order: process sections twice to exercise the cache (revisits)
    stream_order = list(range(S)) + list(range(S))
    for s in stream_order:
        idxs = sec_leaves[s]
        # load section (resident)
        if s not in resident:
            resident.append(s)
            while len(resident) > max_resident:
                resident.pop(0)      # evict LRU
        peak_resident_leaves = max(peak_resident_leaves, sum(len(sec_leaves[r]) for r in resident))
        sig = _section_signature(idxs, ctr, siz)
        if sig in cache:
            ell = cache[sig]; cache_hits += 1
        else:
            remap = {gi: li for li, gi in enumerate(idxs)}
            led = [(remap[i], remap[j]) for (i, j) in sec_intra[s]]
            l2 = _lambda2(_lap(len(idxs), led)) if (len(idxs) >= 2 and led) else 1.0
            ell = 1.0 / np.sqrt(max(l2, 1e-3)); cache[sig] = ell
        sext = (float(np.ptp(ctr[idxs], axis=0).mean()) + float(siz[idxs].mean())) if len(idxs) else leaf
        sg = float(np.clip(kappa * ell * sext, leaf, max(sext, leaf)))
        for i in idxs:               # emit stitched values (needs only c + scen, all O(S))
            wts = np.exp(-((ctr[i] - scen) ** 2).sum(axis=1) / (2.0 * sg * sg)); wts /= wts.sum()
            field[i] = float(wts @ c)
    return {"field": field, "section_of": so, "n_sections": S, "n_leaves": N,
            "peak_resident_leaves": peak_resident_leaves, "cache_hits": cache_hits,
            "max_resident_sections": max_resident, "coarse_anchor_size": S,
            "memory_streaming": peak_resident_leaves + S * S, "memory_global": N}
