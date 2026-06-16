"""
dentatus.core — frozen Physics Oracle facade over engine/ (AGPL-3.0).

Re-exports ONLY the public observational + transformation surface of the immutable core.
This is the single deterministic import path for the engine. The engine package itself
(`engine/`) is never touched; this module is a thin, stable contract so that:

  * engine internals can evolve under AGPL-3.0 without breaking callers, and
  * game layers depend on `dentatus.core` (stable) rather than `engine.*` (internal).

Nothing here mutates engine state. All evolving state is caller-tracked primary data
(SeedMemory, bze_ema, cumulative_motion) passed in and out — the oracle is stateless.
"""
# --- state / schema ---
from engine.state import (
    MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT, PROTOCOL_VERSION,
)
# --- validity / firewall / covariance ---
from engine.validity import (
    is_manifold_501, is_manifold_501_perclaim, EPS_MANIFOLD_502,
    is_valid_covariance_401, cholesky_from_stalk_401, kappa_integral,
    citadel_entropy_508, is_citadel_508, CITADEL_FLOOR_508,
    bethe_citadel_509, is_bethe_citadel_509, BETHE_A0_509,
)
# --- operators: partition+homeostasis, manifold observation, spectral, persistence, tracking ---
from engine.operators import (
    apply_gamma_503_recursive, phi_fb_manifold,
    phi_ent_observe, spectral_ent_project,
    persist_scene_504, seed_memory_init_504, seed_memory_hash_504, spatial_key_504,
    estimate_global_motion_505, world_frame_key_505,
    track_correspondence_505, track_dag_hash_505,
    face_adjacent_501, build_L_sheaf_503,
    _BETA_Z_313, _GAMMA_INF_A_409, _GAMMA_INF_D_409, _TAU_WARMUP_409,
    _ALPHA_DISC_409, _ALPHA_MAINT_409, _BETA_THRESHOLD_409, _BETA_Z_MIN_409,
    _GAMMA_INF_ENT_503, _K_FIEDLER_503, _ALPHA_PERSIST_504,
)

# Frozen schema constants (the contract the semantic layer compiles to)
STALK_DIM = 18
SECTOR_A = slice(0, 4)     # photometric: mass, r, g, b
SECTOR_B = slice(4, 8)     # affine: x, y, z, w
SECTOR_C = slice(8, 12)    # curvature: nx, ny, nz, kappa
SECTOR_D = slice(12, 18)   # covariance: log_l11, log_l22, log_l33, l21, l31, l32
FIREWALL_EPSILON = EPS_MANIFOLD_502   # 0.8

ENGINE_PROTOCOL = "exp505-v1"

__all__ = [
    "MuState", "Claim", "Provenance", "now_iso", "ALPHA_DEFAULT", "PROTOCOL_VERSION",
    "is_manifold_501", "is_manifold_501_perclaim", "EPS_MANIFOLD_502",
    "is_valid_covariance_401", "cholesky_from_stalk_401", "kappa_integral",
    "citadel_entropy_508", "is_citadel_508", "CITADEL_FLOOR_508",
    "bethe_citadel_509", "is_bethe_citadel_509", "BETHE_A0_509",
    "apply_gamma_503_recursive", "phi_fb_manifold", "phi_ent_observe", "spectral_ent_project",
    "persist_scene_504", "seed_memory_init_504", "seed_memory_hash_504", "spatial_key_504",
    "estimate_global_motion_505", "world_frame_key_505",
    "track_correspondence_505", "track_dag_hash_505",
    "face_adjacent_501", "build_L_sheaf_503",
    "STALK_DIM", "SECTOR_A", "SECTOR_B", "SECTOR_C", "SECTOR_D", "FIREWALL_EPSILON",
    "ENGINE_PROTOCOL",
]
