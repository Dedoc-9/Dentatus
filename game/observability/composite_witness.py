"""
game/observability/composite_witness.py — EXP-525 Composite Attestation (integrity / anti-cheat).

Binds the engine identity H_t to the game layer's own deterministic state, WITHOUT touching the frozen
engine (Charter II.3 / EXP-523 witness pattern). Two functions, two purposes:

  composite_address(H_t, game_stats)        -> PUBLIC tamper-evidence. A hash of deterministic, fully
                                               disclosed inputs. Anyone (incl. a replay) can recompute
                                               it; that is the point. It proves the rendered game state
                                               matches the authoritative engine step. It is NOT a lock
                                               (no secret => no monopoly; a competitor can reproduce it).

  session_attest(H_t, game_stats, secret)   -> the REAL moat. An HMAC under a SERVER-HELD secret. A
  verify_attest(...)                           client cannot forge a valid attestation, so an
                                               authoritative server can refuse to commit a manifest that
                                               is not server-signed. The engine stays open and runnable;
                                               only the *authoritative service* is gated, which is a
                                               service moat, not a cripple on the AGPL core.

Replay (EXP-520) is preserved: game_sufficient_stats are appended to the command log, so reconstruct()
reproduces the exact composite_address bit-for-bit. The engine `_compute_H` is unchanged.

Clean room: stdlib only; no engine.* import. Engine FROZEN.
"""
import hashlib, hmac, json

PROTOCOL = "exp525-v1"
NDIGITS = 6


def game_sufficient_stats(state, ndigits=NDIGITS):
    """Canonical, deterministic projection of arbitrary game-layer state to loggable sufficient
    statistics. Floats rounded, keys sorted -> reproducible across runs/processes (for replay)."""
    out = {}
    for k in sorted(state.keys()):
        v = state[k]
        if isinstance(v, float):
            out[k] = round(v, ndigits)
        elif isinstance(v, (list, tuple)):
            out[k] = [round(x, ndigits) if isinstance(x, float) else x for x in v]
        else:
            out[k] = v
    return out


def _canon(H_t, game_stats, protocol):
    return json.dumps({"H_t": H_t, "game": game_sufficient_stats(game_stats), "pv": protocol},
                      sort_keys=True, separators=(",", ":")).encode()


def composite_address(H_t, game_stats, protocol=PROTOCOL):
    """Public composite identity: binds engine H_t to game sufficient-stats. Tamper-evident, NOT secret.
    Changing any bound game statistic changes the address -> proves client state matches the engine step."""
    return hashlib.sha256(_canon(H_t, game_stats, protocol)).hexdigest()[:16]


def session_attest(H_t, game_stats, server_secret, protocol=PROTOCOL):
    """Server-signed attestation (HMAC-SHA256 under a secret the client never holds). Only an authority
    that knows `server_secret` can mint a valid attestation -> the real, forgery-resistant gate."""
    if isinstance(server_secret, str):
        server_secret = server_secret.encode()
    return hmac.new(server_secret, _canon(H_t, game_stats, protocol), hashlib.sha256).hexdigest()


def verify_attest(H_t, game_stats, server_secret, sig, protocol=PROTOCOL):
    """Constant-time verification of a server attestation."""
    expect = session_attest(H_t, game_stats, server_secret, protocol)
    try:
        return hmac.compare_digest(expect, sig)
    except Exception:
        return False
