"""
quorum/ghost.py — the dissent accumulator (the only place the ghost PERSISTS across rounds).

tally() emits a per-round residual G_t = {witnesses whose hash != modal} and its ratio
g_t = |G_t| / n_t  (the certificate's observables["divergence"], in [0,1]). ghost.py accumulates that
residual into a single slow scalar via an exponential moving average, exactly as the workbench's ghost
formalism prescribes:

    S_{t+1} = alpha * S_t + (1 - alpha) * g_t

S_t is a PURE OBSERVABLE -- a 'dissent pressure'. Dual-arithmetic separation is preserved: the forward
axis (the exact integer tally that certifies a round) and this dual residual axis (S_t) are NOT collapsed
into one number. S_t NEVER gates a certificate; a round certifies or not on the exact integer count alone.

HONEST BOUND: a rising S_t signals that honest, outvoted witnesses are disagreeing more often -- an
early, measurable drift signal (e.g. an upstream model-weight update quietly forking one node). It does
NOT say which side is correct. Consensus is not truth; dissent is not truth either. S_t is a sensor.
"""


class GhostAccumulator:
    """EMA over the per-round divergence ratio. alpha in [0,1): higher = slower/longer memory."""

    def __init__(self, alpha=0.9, s0=0.0):
        if not (0.0 <= alpha < 1.0):
            raise ValueError("alpha must be in [0,1) (it is the EMA retention weight, an explicit choice)")
        self.alpha = float(alpha)
        self.S = float(s0)
        self.t = 0
        self.history = []                                    # [{round, g_t, S}] -- replayable trace

    def update(self, certificate):
        """Fold one round's dissent ratio into S_t. Reads the certificate's divergence observable; never
        reads back its own S into the tally (no feedback into the gate)."""
        g_t = float(certificate["observables"]["divergence"])
        self.S = self.alpha * self.S + (1.0 - self.alpha) * g_t
        self.t += 1
        self.history.append({"round": certificate.get("round"), "g_t": g_t, "S": self.S})
        return self.S

    def pressure(self):
        """Current dissent pressure S_t (pure scalar)."""
        return self.S

    def spiking(self, threshold):
        """True iff S_t has crossed a declared alert threshold. The threshold is a chosen model cut, like
        k -- it does not make the signal a verdict; it only routes attention."""
        return self.S >= float(threshold)
