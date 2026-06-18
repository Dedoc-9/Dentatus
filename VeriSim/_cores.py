"""
VeriSim/_cores.py — read-only access to the Dentatus/Chronicle workbench (the Sibling Law).

VeriSim is a STANDALONE project. It defines its own scenarios, runner, and court, and imports the workbench
siblings READ-ONLY by putting their directories on sys.path — it never edits or vendors them. The borrowed
primitives: aether (fixed-point physics), tessera (offline-replayable proof), stasis (canonical bytes,
drift classification, Merkle batch), fuel (bounded integer step budget), crucible (adversarial seeds).

Only chronicle defines a `core` module, so there is no module-name collision across the siblings used here.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)                                # Reality_Engine/

for _sub in ("chronicle", "aether", "tessera", "stasis", "fuel", "crucible", "syracuse"):
    _p = os.path.join(ROOT, _sub)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import fixedpoint as fp                                      # aether/fixedpoint.py
import shard as tessera                                     # tessera/shard.py
import canon as canon                                       # stasis/canon.py
import drift as drift                                       # stasis/drift.py
import batch as merkle                                      # stasis/batch.py

SCALE = fp.SCALE
to_fp = fp.to_fp
fp_mul = fp.fp_mul
