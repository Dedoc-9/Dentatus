"""
lockstep/interp.py — render frames as deterministic OBSERVABLES between truth ticks.

A render frame at 240 fps over a 120 Hz truth track falls *between* authoritative ticks. Its on-screen
position is an interpolation, not a state advance -- a presentation artifact that is captured but NEVER
gated into a truth hash. This is the exact-gate / captured-observable split applied to a frame loop:
truth lives at tick boundaries (tick.py); everything a player actually sees in between is observed, not
decided.

Frame f maps to a tick-time  f * truth_rate / render_rate  (in tick units), kept as an exact integer
rational  (n, rem, den)  with  alpha = rem/den in [0,1).  The interpolated position is an INTEGER lerp:

    x_f = x_n + (x_{n+1} - x_n) * rem // den

so even the observable is bit-exact and replayable -- yet it is explicitly excluded from truth_hash, so a
divergence in presentation can never masquerade as a divergence in truth.

THE COARSE-GRAINING NOTE: the tick boundary is a chosen discretization, not an inherent limit. Truth is
defined ONLY at integer ticks; a sub-tick render position is an interpolated observable with no
truth-status. Events "between ticks" are model constructs of the scheduler.

NO BACKREACTION: an interpolated render position must never flow back into the integer sim. The observable
does not perturb the gated state. (interp.py is read-only over a TruthTrack and returns new dicts.)
"""
from tick import LockstepError


def frame_to_tick(f, truth_rate, render_rate):
    """Map render frame index f to (n, rem, den): tick-time = n + rem/den, alpha = rem/den in [0,1)."""
    if truth_rate <= 0 or render_rate <= 0:
        raise LockstepError("rates must be positive integers")
    num = f * truth_rate
    return num // render_rate, num % render_rate, render_rate


def ilerp(a, b, rem, den):
    """Integer linear interpolation: exact, no float. rem/den in [0,1]."""
    return a + (b - a) * rem // den


def interpolate(state_n, state_np1, rem, den, fields):
    return {fld: ilerp(state_n[fld], state_np1[fld], rem, den) for fld in fields}


def render_frame(track, f, truth_rate, render_rate, fields):
    """Produce the observable render frame f over `track`. Interpolation only -- if the bracketing future
    tick is not yet in the truth track, this raises rather than silently EXTRAPOLATING (honest bound:
    extrapolation invents truth that does not exist; ask for it explicitly elsewhere if you must)."""
    n, rem, den = frame_to_tick(f, truth_rate, render_rate)
    if rem == 0:                                             # exact tick boundary: the frame shows truth itself
        if n >= len(track.states):
            raise LockstepError("frame %d maps to tick %d, not yet simulated" % (f, n))
        return {"frame": f, "tick": n, "alpha_num": 0, "alpha_den": den,
                "pos": {fld: track.states[n][fld] for fld in fields}, "extrapolated": False}
    if n + 1 >= len(track.states):
        raise LockstepError("frame %d needs tick %d (not in truth track); no silent extrapolation" % (f, n + 1))
    return {"frame": f, "tick": n, "alpha_num": rem, "alpha_den": den,
            "pos": interpolate(track.states[n], track.states[n + 1], rem, den, fields),
            "extrapolated": False}


def frames_per_tick(truth_rate, render_rate):
    """Observable ratio: how many render frames fall in one truth tick (e.g., 240/120 = 2)."""
    return render_rate / truth_rate


def render_span(track, truth_rate, render_rate, f_start, f_end, fields):
    """All observable frames in [f_start, f_end) that the current truth track can support (interpolation
    only). Returns (frames, n_dropped) where dropped frames would have needed un-simulated future ticks."""
    out, dropped = [], 0
    for f in range(f_start, f_end):
        try:
            out.append(render_frame(track, f, truth_rate, render_rate, fields))
        except LockstepError:
            dropped += 1
    return out, dropped
