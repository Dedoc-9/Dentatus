"""
airlock/_cores.py — read-only workbench access (Sibling Law). The airlock is a STANDALONE membrane.

It borrows `stasis` (canonical-bytes well-formedness gate), `chronicle` (content-addressed + signed shards),
and `quorum` (multi-witness reproduction). The deterministic KERNEL is NOT imported here — it is injected as
an adapter (so the membrane is kernel-agnostic and avoids the aether/AetherPulse `kernel` name collision).
Nothing is edited or vendored.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
for _sub in ("chronicle", "stasis", "quorum"):
    _p = os.path.join(ROOT, _sub)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import core                      # chronicle/core.py — canonical_bytes, state_hash
import canon                     # stasis/canon.py   — is_canonical, canon_hash, CanonizationError
