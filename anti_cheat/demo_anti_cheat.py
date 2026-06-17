"""
anti_cheat/demo_anti_cheat.py — server-authoritative match forensics end to end.

Run:  PYTHONHASHSEED=0 python3 demo_anti_cheat.py

  A. SEAL        — a legitimate engagement (both players in a mutually-visible sector) seals to the ledger.
  B. WALLBANG    — a hit claimed across an occlusion boundary is refused fail-closed; nothing seals.
  C. TELEPORT    — a hit between non-adjacent, non-visible sectors is refused.
  D. CULLING     — the server packet for a player OMITS occluded enemies (anti-wallhack prevention).
  E. REPLAY      — the Replay Court re-verifies the sealed ticks bit-for-bit on the public key.
  F. TAMPER      — editing a sealed tick is caught.

Honest scope: catches geometric impossibilities vs a pinned visibility graph, NOT aimbot on visible
targets. Culling prevents wallhacks; the ledger proves an impossible hit was refused. Integrity != truth.
"""
import os, sys, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import match_forensics as MF
# frozen chronicle (match_forensics already put ../chronicle on the path)
import core
from court import verify_chain, print_verdict
from signing import Ed25519Signer, Ed25519Verifier, ed25519_available, HmacSigner

# Pinned tactical map: Spawn<->Courtyard visible; Courtyard<->B-Site visible; Spawn |X| B-Site occluded.
TACTICAL_MAP = {"Spawn": ["Courtyard"], "Courtyard": ["B-Site"]}


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("[anti_cheat] run with PYTHONHASHSEED=0\n"); raise SystemExit(2)

    if ed25519_available():
        signer = Ed25519Signer.generate(); verifier = Ed25519Verifier(signer.public_material())
        keynote = "Ed25519 (third-party verifiable; swap chronicle.hardware_signing for TPM)"
    else:
        signer = HmacSigner(b"server_key"); verifier = signer; keynote = "HMAC fallback (single trust domain)"
    mf = MF.MatchForensics(TACTICAL_MAP, signer)
    print("[anti_cheat] server flight recorder up — signer: %s\n" % keynote)

    print("A) SEAL legitimate engagement (both in Courtyard):")
    r1 = mf.record_tick("TICK-001", "Courtyard", "Courtyard", claimed_hit=True, claimed_damage=35, aim_angle=45.0)
    print("   sealed  is_hit=%s dmg=%s visible=%s  +%s" %
          (r1["frame"]["outputs"]["is_hit"], r1["frame"]["outputs"]["damage"],
           r1["frame"]["outputs"]["visible"], r1["committed_hash"][:10]))
    ledger = [r1]

    print("\nB) WALLBANG: claim a 100-dmg headshot from Spawn into occluded B-Site:")
    try:
        mf.record_tick("TICK-002", "Spawn", "B-Site", claimed_hit=True, claimed_damage=100)
        print("   sealed (should NOT happen)")
    except core.InvariantViolation as e:
        print("   REFUSED fail-closed: %s" % e)

    print("\nC) TELEPORT: hit between Spawn and B-Site (non-adjacent, non-visible):")
    try:
        mf.record_tick("TICK-003", "Spawn", "B-Site", claimed_hit=True, claimed_damage=42)
        print("   sealed (should NOT happen)")
    except core.InvariantViolation as e:
        print("   REFUSED fail-closed (impossible geometry)")

    print("\nD) CULLING (anti-wallhack prevention): packet for a Spawn player omits occluded enemies:")
    enemies = [{"id": "E1", "sector": "Courtyard"}, {"id": "E2", "sector": "B-Site"}]
    vis = MF.visible_enemies("Spawn", enemies)
    print("   enemies in world: %s" % [e["id"] for e in enemies])
    print("   sent to client  : %s   (E2 in B-Site is occluded -> never enters client RAM)" % [e["id"] for e in vis])

    print("\nE) REPLAY COURT verifies the sealed ledger on the public key:")
    print_verdict(verify_chain(ledger, verifier, MF.server_resolve, MF.hit_invariant), len(ledger))

    print("\nF) TAMPER: flip TICK-001's sealed enemy_sector to fake an occluded kill:")
    bad = copy.deepcopy(ledger); bad[0]["frame"]["inputs"]["enemy_sector"] = "B-Site"
    print_verdict(verify_chain(bad, verifier, MF.server_resolve, MF.hit_invariant), len(bad))

    print("\n   NOTE: geometric impossibilities only; culling prevents wallhacks, the ledger proves refusal.")
    print("   Integrity != truth — a sealed tick is consistent + unforged, not proof of no cheating.")
