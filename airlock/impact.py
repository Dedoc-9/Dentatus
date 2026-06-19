"""
airlock/impact.py — impact density as a predicate for VALIDATION DEPTH (never for outcome).

The refinement of the severity dial: how carefully a *mutable* transition is resolved should scale with how
much future it touches. A shot at a wall barely changes the reachable future; a shot at the one player
holding the artifact changes inventory, victory, economy, AI, narrative. Same bullet, different future
geometry — so the airlock *measures it more carefully*, it does NOT change what happens.

THE NEW SIBLING LAW (a corollary of telemetry ≠ control / possibility → allocation, never physics):

    impact_density → validation depth (shadow depth · witness strength · rollback budget · net priority)   ALLOWED
    impact_density → committed outcome                                                                      FORBIDDEN

`impact_density` (true, expensive) = the downstream divergence a transition CAUSES vs the world's natural
evolution. `cheap_impact` (O(apply), generic) = the magnitude of its immediate effect — a cheap predicate.
`validation_policy` turns a (cheap) impact estimate into an airlock SEVERITY tier, so high-impact transitions
get deep validation and low-impact ones stay cheap — while the committed outcome is provably invariant to the
tier (severity changes admissibility depth, never the kernel — see airlock severity tests). Stdlib only.
"""


def impact_density(world, txn, adapter, horizon=14):
    """TRUE impact: ‖ advance(apply(world,txn)) − advance(world) ‖ over `horizon` ticks — how much downstream
    future the transition diverges. Expensive (2·horizon kernel steps). Used as ground truth / calibration."""
    def advance(w):
        for _ in range(horizon):
            w = adapter.K.step(w)
        return w
    natural = advance(world)
    try:
        acted = advance(adapter.apply(world, txn))
    except adapter.ApplyError:
        return 0
    return adapter.delta_norm(natural, acted)


def cheap_impact(world, txn, adapter):
    """CHEAP, generic predicate: the magnitude of the transition's IMMEDIATE effect, ‖apply(world,txn) − world‖
    — one apply, no rollout. A fast proxy for how much future the transition touches."""
    try:
        return adapter.delta_norm(world, adapter.apply(world, txn))
    except adapter.ApplyError:
        return 0


def validation_policy(threshold, impact_fn=None, low="game", high="strict"):
    """Return a severity policy `(world, txn) -> tier` for `airlock.membrane.propose(severity=...)`: high
    impact ⇒ `high` (deep validation), low impact ⇒ `low` (cheap). Uses `cheap_impact` unless `impact_fn`
    given. This drives VALIDATION DEPTH only; the committed outcome is invariant to the tier (the law)."""
    def policy(world, txn, adapter=None):
        # membrane calls policy(world, txn); bind the adapter via closure when building, or fall back.
        fn = impact_fn or (lambda w, t: cheap_impact(w, t, policy._adapter))
        return high if fn(world, txn) >= threshold else low
    policy._adapter = None
    return policy


def bind(policy, adapter):
    """Bind an adapter into a validation policy so the membrane can call policy(world, txn)."""
    policy._adapter = adapter
    return policy
