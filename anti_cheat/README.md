# anti_cheat — server-authoritative match forensics

A Sibling-Law component: it imports the frozen [`chronicle`](../chronicle/README.md) recorder read-only and
turns an untrusted match log into a cryptographically sealed, independently verifiable record, with an
**exact geometric invariant** enforced at the ledger commit boundary.

## Run it

```bash
PYTHONHASHSEED=0 python3 demo_anti_cheat.py        # seal, wallbang/teleport refused, culling, replay, tamper
PYTHONHASHSEED=0 python3 tests/test_anti_cheat.py  # 9 tests
```

## Two distinct mechanisms (don't conflate them)

1. **Culling (`visible_enemies`) — prevention.** The server omits occluded entities from a player's packet,
   so their positions never enter client RAM. This is what actually defeats wallhacks.
2. **Ledger + invariant — accountability.** A claimed hit across an occlusion boundary (wallbang) or
   between non-visible sectors (teleport) is a geometric impossibility; the precommitted `hit_invariant`
   **refuses to seal it** (fail-closed), and every sealed tick is tamper-evident and replayable on the
   server's public key (so a league/third party can audit without the power to forge).

## What it catches — and does not

| Catches | Does NOT catch |
|---|---|
| Hits across an occlusion boundary (wallbang) | Aimbot on a **legitimately visible** target (geometry permits the shot) |
| Teleport / impossible-position engagements | Anything finer than the macro-sector graph |
| Post-hoc edits of a sealed tick | Cheating by vectors outside the visibility model |

The visibility graph is **server-pinned** (config, not client-supplied) and symmetric-closed (if A sees B,
B sees A; every sector sees itself). The gate is exact set membership — integer/deterministic, replay-safe,
no floats in the commit path.

## Files

| File | Role |
|---|---|
| `match_forensics.py` | pinned visibility graph, `server_resolve` + fail-closed `hit_invariant`, `visible_enemies` culling, `MatchForensics` recorder wrapper |
| `demo_anti_cheat.py` | seal / wallbang / teleport / culling / replay / tamper |
| `tests/test_anti_cheat.py` | visibility, occlusion gate, culling, replay + tamper, third-party verify |

## Honest scope

This does **not** scan client kernel/RAM. It proves *mathematical deviation* on the server-authoritative
ledger and prevents wallhacks by culling — it is not a kernel anti-cheat and does not claim to catch all
cheating. **Integrity is not truth:** a sealed tick is consistent with the pinned geometry and unforged,
not a proof that no cheating occurred. Swap the demo's `Ed25519Signer` for
`chronicle/hardware_signing.HardwareSigner` (Tier 1/2) for TPM-sealed tickets, unchanged.
