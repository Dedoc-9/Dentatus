"""
stride/demo_stride.py — migrate deterministic state across a (simulated) machine boundary, verifiably.

Run:  PYTHONHASHSEED=0 python3 demo_stride.py

  A. MIGRATE OK     — sender packs state + its environment fingerprint; a receiver with the MATCHING
                      fingerprint accepts and continues the deterministic execution.
  B. ENV MISMATCH   — a receiver whose environment drifted (one different core hash) refuses fail-closed.
  C. CAPTURE+SEAL   — the volatile network telemetry is captured and sealed into the ledger.
  D. REPLAY         — the Replay Court reproduces the migrated transition bit-for-bit, reading telemetry
                      from the record — never re-opening a socket.

Honest bound: proves structural environment identity + exact recorded network inputs. NOT TLS/encryption,
NOT proof the remote hardware is honest. Integrity != truth.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import transport as T
import core
from court import verify_chain, print_verdict
from signing import HmacSigner

# the migrating computation: a pure step on the transported state
def migrate_logic(inputs):
    s = inputs["state"]
    return {"next_state": {"n": s["n"] + 1, "acc": s["acc"] + s["n"]},
            "link_obs": inputs["_cap"]["link"]}   # network telemetry read from capture


def transport_invariant(inputs, outputs):
    return outputs["next_state"]["n"] >= 1        # trivial sanity gate (sensor demo, not the focus)


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("[stride] run with PYTHONHASHSEED=0\n"); raise SystemExit(2)

    # environment fingerprints (opaque content hashes; in practice = selfaudit frozen-core hashes / workbench_H)
    sender_env = core.state_hash({"chronicle/core.py": "aaaa", "chronicle/signing.py": "bbbb"})
    matching_env = core.state_hash({"chronicle/core.py": "aaaa", "chronicle/signing.py": "bbbb"})
    drifted_env = core.state_hash({"chronicle/core.py": "aaaa", "chronicle/signing.py": "DRIFT"})

    state = {"n": 5, "acc": 0}
    buf = T.pack(state, sender_env)
    print("A) MIGRATE OK (matching environment fingerprint):")
    migrated = T.receive(buf, matching_env)
    print("   receiver accepted state=%s  env match=%s" % (migrated, sender_env[:12] == matching_env[:12]))

    print("\nB) ENV MISMATCH (receiver drifted one core hash):")
    try:
        T.receive(buf, drifted_env)
        print("   accepted (should NOT happen)")
    except T.EnvironmentMismatch as e:
        print("   EnvironmentMismatch -> inbound path refused: %s" % str(e)[:54])

    print("\nC) CAPTURE + SEAL the migrated transition with network telemetry as an observable:")
    rec = core.Recorder(HmacSigner(b"stride"), core.ruleset_hash(migrate_logic, transport_invariant))
    sealed = {"state": migrated, "_cap": {"link": T.capture_link_telemetry(latency_ms=12.84, jitter_ms=3.1, dropped=2, hops=7)}}
    r = rec.record("MIGRATE-001", sealed, migrate_logic(sealed), transport_invariant)
    print("   sealed next_state=%s  link(obs)=%s  +%s"
          % (r["frame"]["outputs"]["next_state"], r["frame"]["outputs"]["link_obs"], r["committed_hash"][:10]))

    print("\nD) REPLAY COURT reproduces the migration (telemetry from the record, no socket reopened):")
    print_verdict(verify_chain([r], b"stride", migrate_logic, transport_invariant), 1)
