# SPDX-License-Identifier: AGPL-3.0-only
"""
AetherPulse/snapshot.py — the L1/L2/L3 seam: only the logic layer is deterministic; visuals read, never write.

Three layers, one rule. **L1 (logic)** — position/velocity/health — is bit-exact and hashed (`kernel`). **L2
(visual)** — particles, lighting, screen-shake — and **L3 (UI/HUD)** — score, damage numbers — receive a
READ-ONLY snapshot of L1 and may differ between clients without breaking anything; that difference is
benign OBSERVABLE drift, never a consensus fault. The load-bearing invariant is **no write-back**: the
render/UI path cannot mutate the next tick's L1 state. This is exactly the workbench's exact-gate (L1) /
observable (L2+L3) split, applied to a frame loop.

Anti-cheat falls out for free: a memory-injection that edits L1 is caught because the recomputed L1 hash
diverges from the server/quorum-expected hash. Editing L2/L3 changes nothing that is gated — it is visible
desync, not an accepted state.

HONEST BOUND: this detects and rejects L1 tampering and replays the run; it does not make state "immutable"
or prevent the attempt before execution, and it does not eliminate network lag.
"""
import os
import sys
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kernel as K


def l1_snapshot(world):
    """An immutable, deep-copied READ-ONLY view of L1 for the render/UI threads (double-buffer frame_N).
    Because it is a copy, anything the render layer does to it cannot reach frame_N+1."""
    bodies = [{"id": b["id"], "pos": list(b["pos"]), "vel": list(b["vel"]), "half": list(b["half"])}
              for b in sorted(world["bodies"], key=lambda b: b["id"])]
    return {"tick": world["tick"], "bodies": bodies, "l1_hash": K.state_hash(world)}


def render_observe(snapshot, client_seed):
    """L2/L3 derivation from the read-only snapshot. Returns ONLY visuals/UI observables — never state. Two
    clients with different `client_seed` may produce different particles/shake from the SAME L1 (benign)."""
    p = int.from_bytes(hashlib.sha256(("%d|%d" % (snapshot["tick"], client_seed)).encode()).digest()[:2], "big") % 50
    return {"l1_hash": snapshot["l1_hash"],          # the gate: must match across clients
            "particles": p, "screen_shake": p // 10,  # L2 observables: may differ freely
            "damage_number_anim_frame": p % 8}        # L3 observable


def l1_agrees(observe_a, observe_b):
    """Consensus check across two clients' frames: the L1 hash (the gate) must match; L2/L3 may differ."""
    return observe_a["l1_hash"] == observe_b["l1_hash"]


def detect_l1_injection(world, expected_l1_hash):
    """Server-authoritative: recompute the L1 hash; a memory-injected position/velocity diverges -> rejected.
    Returns (ok, recomputed_hash)."""
    h = K.state_hash(world)
    return (h == expected_l1_hash), h
