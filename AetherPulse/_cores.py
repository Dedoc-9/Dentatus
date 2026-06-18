"""
AetherPulse/_cores.py — read-only access to the workbench (Sibling Law). AetherPulse is a STANDALONE project.

This is the Stage-1 REFERENCE KERNEL in Python: it defines the exact deterministic semantics a future native
(Rust/C++ SIMD) engine must match bit-for-bit. It borrows aether.fixedpoint (integer arithmetic), tessera +
chronicle signing (conformance proofs), and stasis (canonical bytes + Merkle batch). Nothing is edited or
vendored.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
for _sub in ("chronicle", "aether", "tessera", "stasis", "crucible", "syracuse"):
    _p = os.path.join(ROOT, _sub)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import fixedpoint as fp                 # aether/fixedpoint.py
import shard as tessera                 # tessera/shard.py
import canon as canon                   # stasis/canon.py
import batch as merkle                  # stasis/batch.py

SCALE = fp.SCALE
to_fp = fp.to_fp
fp_mul = fp.fp_mul
