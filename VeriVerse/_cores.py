"""
VeriVerse/_cores.py — read-only access to the workbench (Sibling Law). VeriVerse is a STANDALONE product.

Borrowed primitives: stasis (canonical bytes + Merkle batch), crucible/syracuse (provable feature
provenance via Collatz seeds), aether.fixedpoint (integer arithmetic for physics), tessera + chronicle
signing (signed, replayable chunk shards). Nothing here is edited or vendored.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)

for _sub in ("chronicle", "stasis", "crucible", "syracuse", "aether", "tessera"):
    _p = os.path.join(ROOT, _sub)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import canon as canon                 # stasis/canon.py
import batch as merkle                # stasis/batch.py
import orbit as syracuse              # syracuse/orbit.py
import forest as crucible             # crucible/forest.py
import fixedpoint as fp               # aether/fixedpoint.py
