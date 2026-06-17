"""
integration/parity_proof.py — coupled vs uncoupled primitives produce IDENTICAL content addresses.

Coupled   = the shared, imported primitives (llm_toolkit/agent_core) reused across modules (DRY).
Uncoupled = a vendored, standalone copy (vendored_core) that imports nothing from the workbench.

We run both over a battery of awkward payloads (nested dicts, floats that drift on GPUs, unicode, tuples)
and assert byte-identical canonical_bytes, identical state_hash, and — for completeness — an identical
Ed25519 signature over a committed hash. If all match, extraction is lossless: a component can be lifted
out and vendored with zero change to its verifiable identity.

Run:  PYTHONHASHSEED=0 python3 parity_proof.py
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "llm_toolkit"))

import agent_core as coupled                 # the shared/imported primitives
import vendored_core as uncoupled            # the standalone vendored copy
from agent_guard import Ed25519Signer, ed25519_available

BATTERY = [
    {"a": 1, "b": [2, 3], "c": {"x": True, "y": None}},
    {"logprobs": [-0.0001234567, -1.0 / 3.0, 2.0 / 3.0], "score": 0.85},
    {"unicode": "réfund — naïve façade ✓", "nested": {"deep": {"deeper": [1.5, "z", {"k": 0.1 + 0.2}]}}},
    {"tuple_becomes_list": (1, 2, 3), "mixed": [1, "two", 3.0, False]},
    {"z": 1, "a": 2, "m": 3},                 # key-order sensitivity
]


def main():
    coupled.require_deterministic_hashing("integration.parity")
    print("Coupled (imported agent_core)  vs  Uncoupled (vendored_core)\n" + "-" * 64)
    all_ok = True
    for i, payload in enumerate(BATTERY):
        cb_c, cb_u = coupled.canonical_bytes(payload), uncoupled.canonical_bytes(payload)
        sh_c, sh_u = coupled.state_hash(payload), uncoupled.state_hash(payload)
        match = (cb_c == cb_u) and (sh_c == sh_u)
        all_ok &= match
        print("  case %d  bytes=%s  hash=%s  %s"
              % (i, "EQ" if cb_c == cb_u else "NE", sh_c[:12], "OK" if match else "MISMATCH"))

    # source_hash parity over the same function object
    sh_fn_c = coupled.source_hash(main)
    sh_fn_u = uncoupled.source_hash(main)
    src_ok = (sh_fn_c == sh_fn_u)
    all_ok &= src_ok
    print("  source_hash(main): coupled=%s uncoupled=%s  %s" % (sh_fn_c, sh_fn_u, "OK" if src_ok else "MISMATCH"))

    # signature parity: same committed bytes + same key -> identical Ed25519 signature
    if ed25519_available():
        signer = Ed25519Signer.generate()
        committed_c = coupled.state_hash({"committed": BATTERY})
        committed_u = uncoupled.state_hash({"committed": BATTERY})
        sig_c = signer.sign(committed_c.encode())
        sig_u = signer.sign(committed_u.encode())
        sig_ok = (sig_c == sig_u) and (committed_c == committed_u)
        all_ok &= sig_ok
        print("  ed25519 over committed hash: %s" % ("IDENTICAL" if sig_ok else "MISMATCH"))

    print("-" * 64)
    print("RESULT: %s — extraction is lossless; coupling is convenience, not correctness."
          % ("PARITY HOLDS" if all_ok else "PARITY BROKEN"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
