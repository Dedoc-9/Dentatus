"""
game/agency/replay.py — EXP-520 Replay / Time-Travel Debugger (Fork tau).

The provenance DAG is turned into a TIME MACHINE by event-sourcing: the world's history is a command
log (the deterministic inputs that drove each phase change) plus sparse full-state checkpoints. Any
historical mu is reconstructed by restoring the nearest preceding checkpoint and replaying the recorded
commands forward.

Replay is VERIFIED, not trusted: each reconstructed step's engine H_t must equal the H recorded at
capture time. A match is cryptographic proof that the engine is deterministic and the history
un-tampered; a mismatch raises immediately (ReplayMismatch). This makes "the past" a reproducible
mathematical coordinate, and turns CompactingWorld.BeyondWindowError into a COLD RESTORE.

Clean room: core (MuState/Claim) + game.injection only; no engine.* import. Engine FROZEN.
"""
import os, sys, copy
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_REALITY = os.path.dirname(os.path.dirname(_HERE))
if _REALITY not in sys.path:
    sys.path.insert(0, _REALITY)
from dentatus import core as _core
from injection import inject_phase_change_517

PROTOCOL = "exp520-v1"


class ReplayMismatch(Exception):
    """A reconstructed state's H_t does not match the recorded H_t (non-determinism or tamper)."""


def _active_claim(mu):
    cid = next(iter(mu.active))
    return mu.claims[cid]


class TimeMachine:
    """Event-sourced history: command log + sparse checkpoints -> reconstruct(any H)."""

    def __init__(self, root_mu, checkpoint_every=8):
        if not root_mu._sealed:
            root_mu.seal()
        self.commands = []                 # ordered melt commands (event log)
        self.checkpoints = {0: root_mu}    # seq -> full MuState (genesis at 0)
        self.h_index = {root_mu.H: 0}      # engine H_t -> seq
        self.live = root_mu
        self.checkpoint_every = int(checkpoint_every)

    # ---- capture (forward) ------------------------------------------------
    def step(self, beta_Z, strain, n_fragments, n_gamma, **kw):
        """Execute one phase-change command against the live state; journal it. Returns the record.
        Only a 'melted' outcome advances history (and the seq); else the world is unchanged."""
        parent = _active_claim(self.live)
        new_mu, child, rec = inject_phase_change_517(self.live, parent, beta_Z, strain,
                                                     n_fragments, n_gamma, **kw)
        if not rec.get("injected"):
            return rec
        seq = len(self.commands) + 1
        self.commands.append({"seq": seq,
                              "inputs": {"beta_Z": beta_Z, "strain": strain,
                                         "n_fragments": n_fragments, "n_gamma": n_gamma, **kw},
                              "result_H": new_mu.H, "child_id": child.id})
        self.live = new_mu
        self.h_index[new_mu.H] = seq
        if seq % self.checkpoint_every == 0:
            self.checkpoints[seq] = new_mu
        return rec

    # ---- reconstruct (time-travel) ---------------------------------------
    def _nearest_checkpoint(self, seq):
        cps = [s for s in self.checkpoints if s <= seq]
        return max(cps)

    def reconstruct(self, target, verify=True):
        """Reconstruct the historical MuState at a target (an engine H_t string, or an int seq).
        Restores the nearest preceding checkpoint and replays commands forward, VERIFYING each step's
        H_t against the recorded value. Returns the reconstructed (sealed) MuState."""
        seq = self.h_index[target] if isinstance(target, str) else int(target)
        if seq not in range(0, len(self.commands) + 1):
            raise KeyError("seq %r not in history [0..%d]" % (seq, len(self.commands)))
        c0 = self._nearest_checkpoint(seq)
        mu = self.checkpoints[c0]                       # functional engine -> safe to step from
        steps = 0
        for i in range(c0, seq):
            cmd = self.commands[i]                       # commands are 1-indexed by seq; list 0-indexed
            parent = _active_claim(mu)
            mu, child, rec = inject_phase_change_517(mu, parent, cmd["inputs"]["beta_Z"],
                                                     cmd["inputs"]["strain"], cmd["inputs"]["n_fragments"],
                                                     cmd["inputs"]["n_gamma"],
                                                     **{k: v for k, v in cmd["inputs"].items()
                                                        if k not in ("beta_Z", "strain", "n_fragments", "n_gamma")})
            steps += 1
            if verify and mu.H != cmd["result_H"]:
                raise ReplayMismatch("seq %d: replay H %s != recorded %s" % (cmd["seq"], mu.H[:12], cmd["result_H"][:12]))
        return mu, {"from_checkpoint": c0, "steps_replayed": steps, "target_seq": seq, "H": mu.H}

    def verify_history(self):
        """Replay the entire history from genesis, asserting every recorded H reproduces. Returns the
        number of verified transitions (proof of end-to-end determinism)."""
        mu = self.checkpoints[0]
        for cmd in self.commands:
            parent = _active_claim(mu)
            mu, _, _ = inject_phase_change_517(mu, parent, cmd["inputs"]["beta_Z"], cmd["inputs"]["strain"],
                                              cmd["inputs"]["n_fragments"], cmd["inputs"]["n_gamma"],
                                              **{k: v for k, v in cmd["inputs"].items()
                                                 if k not in ("beta_Z", "strain", "n_fragments", "n_gamma")})
            if mu.H != cmd["result_H"]:
                raise ReplayMismatch("seq %d mismatch" % cmd["seq"])
        return len(self.commands)


def cold_restore(time_machine, target_H, verify=True):
    """Fork tau answer to EXP-518 BeyondWindowError: reconstruct a state that fell outside the skeleton
    undo window directly from the DAG + checkpoints."""
    mu, info = time_machine.reconstruct(target_H, verify=verify)
    info["cold_restore"] = True
    return mu, info
