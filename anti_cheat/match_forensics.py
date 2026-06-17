"""
anti_cheat/match_forensics.py — un-falsifiable server-authoritative match forensics (a Sibling-Law module).

Built ON the frozen `chronicle` recorder (imported read-only; never edited). It does NOT scan client
kernel/RAM for cheats. It transforms an untrusted, text-based match log into a cryptographically sealed,
independently verifiable record, and enforces a precommitted geometric invariant at the ledger commit
boundary so an impossible engagement can never be sealed as legitimate.

================================================================================================
WHAT THIS CATCHES (and what it does NOT) — honest scope
================================================================================================
CATCHES (geometric impossibilities against a server-PINNED visibility graph):
  * Shots that land across an occlusion boundary (wallbang through a solid sector) — fail-closed refusal.
  * Teleport / impossible-position engagements (shooter and target in non-adjacent, non-visible sectors).
  * Any post-hoc edit of a sealed tick (Replay Court catches it).

DOES NOT CATCH:
  * Aimbot on a LEGITIMATELY VISIBLE target. If the geometry permits the shot, this gate permits it; pixel-
    perfect aim within the rules is invisible to a topological check (needs separate statistical detection).
  * Anything outside the macro-sector model. The visibility graph is a coarse approximation of real
    occlusion; finer geometry needs a finer graph.

TWO DISTINCT MECHANISMS (do not conflate them):
  1. CULLING (`visible_enemies`) is what actually defeats wallhacks: the server omits occluded entities from
     the client's packet, so their positions never enter client RAM. This is prevention.
  2. The LEDGER + INVARIANT is forensic: it produces tamper-evident PROOF that an occluded "hit" claim was
     refused and never credited. This is accountability, not prevention.

Integrity != truth: a sealed tick proves the engagement was consistent with the pinned visibility graph and
the record is unforged — not that no cheating occurred by some other vector.
"""
import os
import sys

# --- Sibling Law: import the FROZEN chronicle core from ../chronicle (read-only) ---
_WB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
import core                                              # frozen recorder + canonicalizer
from core import Recorder, ruleset_hash, InvariantViolation


# Server-PINNED visibility graph (config, NOT supplied by the client). sector -> sectors it can see.
PINNED_VISIBILITY = {}


def configure_map(graph):
    """Pin the authoritative macro-sector visibility graph. Symmetric closure is enforced so visibility is
    mutual (if A sees B then B sees A) — a one-way map would be an exploitable asymmetry."""
    global PINNED_VISIBILITY
    g = {k: set(v) for k, v in graph.items()}
    for a, sees in list(g.items()):
        for b in sees:
            g.setdefault(b, set()).add(a)
        g[a].add(a)                                      # a sector always sees itself
    PINNED_VISIBILITY = {k: sorted(v) for k, v in g.items()}
    return PINNED_VISIBILITY


def visible(a, b):
    """Exact, deterministic visibility test against the pinned graph (no floats, replay-safe)."""
    return b in PINNED_VISIBILITY.get(a, [])


# ---- module-level so source_hash binds them; these are what the recorder + court run ----
def server_resolve(inputs):
    """Authoritative resolution of a claimed engagement. Deterministic: copies the client's CLAIM and
    annotates the server's visibility verdict. The claim is recorded; the invariant decides if it may seal."""
    return {
        "is_hit": bool(inputs["claimed_hit"]),
        "damage": int(inputs["claimed_damage"]),
        "visible": visible(inputs["player_sector"], inputs["enemy_sector"]),
    }


def hit_invariant(inputs, outputs):
    """FAIL-CLOSED clamp: a hit across an occlusion boundary is a geometric impossibility and may NOT seal."""
    return not (outputs["is_hit"] and not outputs["visible"])


def visible_enemies(player_sector, enemies):
    """The actual anti-wallhack: cull entities the player cannot see so they never reach the client packet.
    `enemies` = [{"id":..,"sector":..}, ...]."""
    return [e for e in enemies if visible(player_sector, e["sector"])]


class MatchForensics:
    """Thin server-side wrapper: pins a map, owns a chronicle Recorder, seals each authoritative tick."""

    def __init__(self, visibility_graph, signer):
        configure_map(visibility_graph)
        self.ruleset = ruleset_hash(server_resolve, hit_invariant)
        self.recorder = Recorder(signer, self.ruleset)

    def record_tick(self, tick_id, player_sector, enemy_sector, claimed_hit, claimed_damage, aim_angle=0.0):
        """Seal one tick. Raises InvariantViolation (fail-closed) on an occluded/impossible hit."""
        inputs = {"player_sector": player_sector, "enemy_sector": enemy_sector,
                  "claimed_hit": bool(claimed_hit), "claimed_damage": int(claimed_damage),
                  "aim_angle": float(aim_angle)}
        outputs = server_resolve(inputs)
        return self.recorder.record(tick_id, inputs, outputs, hit_invariant)
