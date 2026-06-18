"""
AetherManifold/_cores.py — read-only access to the workbench (Sibling Law). A standalone research sandbox.

`AetherManifold` is the Manifold-Stable protocol: deterministic Riemannian optimization on the Stiefel
manifold, executed in `aether`'s fixed-point integers so the optimization trajectory is bit-for-bit
reproducible and attestable. It borrows `aether` (fixed-point + Stiefel auditor + integer Gram-Schmidt),
`stasis` (canonical hashing + Merkle), `crucible` (adversarial edge-case seeds), `tessera`/chronicle
(signed trajectory proofs) — all read-only.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
for _sub in ("chronicle", "aether", "stasis", "tessera", "crucible", "syracuse"):
    _p = os.path.join(ROOT, _sub)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import fixedpoint as F          # aether/fixedpoint.py
import stiefel as ST            # aether/stiefel.py  (gram_schmidt_integer, is_orthonormal_exact)
import canon as canon          # stasis/canon.py
import batch as merkle         # stasis/batch.py

SCALE = F.SCALE
