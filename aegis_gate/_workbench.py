"""
aegis_gate/_workbench.py — read-only access to frozen workbench primitives (the Sibling Law).

aegis_gate is a STANDALONE application. It defines its own state machine, policy, and agent. It does
NOT edit or vendor the cores; it imports them read-only by putting their directories on sys.path. The
only primitives borrowed are chronicle's recorder/court/capture/signing/store (content-addressing,
replay verification, capture seam, attestation) and selfaudit's pinned core baseline (for the drift
panel). If a core file changes, selfaudit's baseline catches it — this module never patches a core.

Honest boundary: nothing here proves a transfer is *correct* or *legal*. It proves a recorded decision
is unforged, exactly reproducible, and rule-faithful. Integrity is not truth. (workbench AGENTS.md S3)
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)                       # Reality_Engine/

# chronicle ships the primitives we reuse; only chronicle/ defines a `core` module, so there is no
# module-name collision with the rest of the workbench.
_CHRONICLE = os.path.join(ROOT, "chronicle")
if _CHRONICLE not in sys.path:
    sys.path.insert(0, _CHRONICLE)

import core                                          # noqa: E402  chronicle/core.py
import court                                         # noqa: E402  chronicle/court.py
import capture as capture                            # noqa: E402  chronicle/capture.py
import signing                                       # noqa: E402  chronicle/signing.py
import store                                         # noqa: E402  chronicle/store.py

# re-export the exact names the app uses, so app code reads `from _workbench import ...`
state_hash = core.state_hash
canonical_bytes = core.canonical_bytes
ruleset_hash = core.ruleset_hash
Recorder = core.Recorder
InvariantViolation = core.InvariantViolation
verify_chain = court.verify_chain
Capture = capture.Capture
captured_view = capture.captured_view
HmacSigner = signing.HmacSigner
Ed25519Signer = signing.Ed25519Signer
Ed25519Verifier = signing.Ed25519Verifier
ed25519_available = signing.ed25519_available
JsonlStore = store.JsonlStore

# selfaudit's pinned baseline + the two frozen-core files the drift panel re-hashes.
SELFAUDIT_BASELINE = os.path.join(ROOT, "selfaudit", "core_baseline.json")


def frozen_core_files():
    """The subset of cores aegis_gate leans on, as (key, abspath). Keys match selfaudit's baseline."""
    keys = ["chronicle/core.py", "chronicle/court.py", "chronicle/capture.py",
            "chronicle/signing.py", "chronicle/store.py"]
    return [(k, os.path.join(ROOT, k)) for k in keys]
