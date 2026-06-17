"""
stride/transport.py — epistemic state-transport across a machine boundary.

THE PROBLEM: migrating a deterministic state machine to another host (cloud, edge, a different cluster) via
raw snapshots/RPC leaks environment drift — a different library/OS/arch makes the replayed path fork.

THE GATE (exact, fail-closed): a migration carries the sender's ENVIRONMENT FINGERPRINT (an opaque content
hash over the structural baseline the caller chooses — e.g. selfaudit's frozen-core hashes / `workbench_H`)
alongside the canonical state buffer. The receiver compares its OWN fingerprint to the sender's; a single
byte of drift or a missing dependency raises `EnvironmentMismatch` and the inbound path refuses to start.

THE OBSERVABLE (captured, never gated): raw network telemetry — latency, jitter, dropped frames, hop count
— is canonicalized (`format(x, ".12g")`) and burned into the ledger inputs. On a post-migration audit the
Replay Court reads that telemetry from the record; it never opens a live socket or re-transmits.

HONEST BOUND: this proves the two environments were STRUCTURALLY identical at transport time and that the
network inputs were recorded exactly. It is NOT transport security (wrap TLS externally), does not encrypt
in transit, and cannot prove the remote hardware is physically honest. Integrity != truth.

Generic + decoupled: the environment fingerprint is an opaque string the caller supplies, so `stride` does
not hard-depend on any particular baseline source. Stdlib only; frozen chronicle core read-only.
"""
import os
import sys

_WB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
import core


class EnvironmentMismatch(Exception):
    """Raised when the receiver's environment fingerprint != the sender's. Inbound path refuses to start."""


def pack(state, environment_H):
    """Serialize state + the sender's environment fingerprint into a canonical byte buffer (deterministic)."""
    return core.canonical_bytes({"state": state, "env": str(environment_H), "stride_pv": "stride-v1"})


def receive(buffer, local_environment_H):
    """Verify the receiver's local fingerprint exactly matches the sender's; return the migrated state, or
    raise EnvironmentMismatch (fail-closed)."""
    import json
    msg = json.loads(buffer.decode("utf-8"))
    sender = msg.get("env")
    if sender != str(local_environment_H):
        raise EnvironmentMismatch("env drift: sender=%s local=%s" % (sender, local_environment_H))
    return msg["state"]


def capture_link_telemetry(latency_ms, jitter_ms, dropped, hops):
    """Canonicalize the volatile network characteristics as a captured observable (never gated)."""
    return core._canon({"latency_ms": float(latency_ms), "jitter_ms": float(jitter_ms),
                        "dropped": int(dropped), "hops": int(hops)})
