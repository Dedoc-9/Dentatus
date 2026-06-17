"""
assay/assess.py — the meta-audit recorder. Binds quality assessments to the DECISIONS they assess.

Each assessment names a `target_hash` (the committed_hash of a chronicle / llm_toolkit decision receipt)
and is itself chained + signed, so the ASSESSMENT LOG is as tamper-evident as the decisions it covers.
This is the integrity discipline applied one level up: we cannot prove a decision was correct/fair/wise,
but we can make every such judgment an unforgeable, attributable, (for metrics) recomputable record.

Two assessment kinds:
  * "metric"   -> deterministic (metrics.py). The court RECOMPUTES it; a fudged number is caught.
  * "judgment" -> signed opinion (judgment.py). The court verifies attribution + rubric binding.
"""
import os, sys, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "llm_toolkit"))
import agent_core as core
from agent_core import GENESIS, HmacSigner

import metrics as M


class AssayRecorder:
    """Append-only, hash-chained log of assessments, attested by an assay-authority signer."""

    def __init__(self, signer, prev_hash=GENESIS, seq=0):
        self.signer = signer if hasattr(signer, "sign") else HmacSigner(signer)
        self.prev = prev_hash
        self.seq = seq

    def _commit(self, frame):
        sh = core.state_hash(frame)
        committed = hashlib.sha256(("%s|%s" % (sh, self.prev)).encode()).hexdigest()
        sig = self.signer.sign(committed.encode())
        receipt = {"frame": frame, "state_hash": sh, "committed_hash": committed,
                   "signature": sig, "algo": self.signer.algo}
        self.prev = committed
        self.seq += 1
        return receipt

    def record_metric(self, target_hash, dimension, metric_name, evidence):
        """Compute a deterministic metric over `evidence` and bind it to `target_hash`. dimension in
        {'correct','fair'}. The metric's SOURCE hash is stored so the court proves the metric is unchanged."""
        fn = M.METRICS[metric_name]
        value = core._canon(fn(evidence))
        verdict = M.metric_verdict(dimension, value)
        frame = {"seq": self.seq, "kind": "metric", "target_hash": target_hash, "dimension": dimension,
                 "metric_name": metric_name, "metric_hash": core.source_hash(fn),
                 "evidence": evidence, "value": value, "verdict": verdict, "prev": self.prev}
        return self._commit(frame)

    def record_judgment(self, target_hash, judgment_record):
        """Store a pre-signed assessor judgment (from judgment.make_judgment) bound to `target_hash`."""
        frame = {"seq": self.seq, "kind": "judgment", "target_hash": target_hash, "dimension": "wise",
                 "judgment": judgment_record, "prev": self.prev}
        return self._commit(frame)
