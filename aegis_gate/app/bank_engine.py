"""
aegis_gate/app/bank_engine.py — a pure-integer financial state machine.

DESIGN RULE: money is integer CENTS. No floats touch a balance, ever. Floats are not associative under
rounding, so two replays of the "same" float arithmetic can diverge in the last bit; a ledger built on
that cannot be content-addressed. Cents-as-int keeps every transition bit-exact and conservation-exact.

The engine is a PURE FUNCTION over an immutable snapshot:

    accounts_post = apply_transfer(accounts_pre, src, dst, amount_cents)

It returns a NEW dict and never mutates the input. "Rollback" is therefore not an undo operation — it is
simply declining to adopt the returned post-state. The recorder (chronicle) refuses to log a transfer
that breaks a precommitted invariant, so an unsafe write never enters the ledger in the first place.

State shape (mock bank database):
    accounts = { acct_id: {"balance_cents": int, "verified": bool, "routing": str} }

world_H = state_hash(accounts) is the content address of the entire bank state after a transition. It is
recomputed from the post-state on replay, so any single altered digit in a stored balance changes world_H
and the replay court rejects the chain.
"""
from _workbench import state_hash, InvariantViolation


# ----------------------------------------------------------------------- invariants (fail-closed)
def _check_amount(amount_cents):
    if not isinstance(amount_cents, int) or isinstance(amount_cents, bool):
        raise InvariantViolation("amount must be an integer number of cents, got %r" % type(amount_cents).__name__)
    if amount_cents <= 0:
        raise InvariantViolation("amount must be strictly positive, got %d" % amount_cents)


def _check_accounts_nonneg(accounts):
    for aid, a in accounts.items():
        if a["balance_cents"] < 0:
            raise InvariantViolation("negative balance on %s (%d) — no overdraft permitted" % (aid, a["balance_cents"]))


def total_cents(accounts):
    """Conserved quantity. apply_transfer must leave this unchanged (no money created/destroyed)."""
    return sum(a["balance_cents"] for a in accounts.values())


def world_hash(accounts):
    """Content address of the full bank state. Balances are ints, so this is bit-stable across machines."""
    canon = {aid: {"balance_cents": a["balance_cents"], "verified": bool(a["verified"]),
                   "routing": a["routing"]} for aid, a in accounts.items()}
    return state_hash(canon)


# ----------------------------------------------------------------------- the one transition
def apply_transfer(accounts_pre, src, dst, amount_cents):
    """Move amount_cents from src to dst. PURE: returns a new accounts dict; never mutates the input.

    Fail-closed: raises InvariantViolation on a bad amount, unknown account, or insufficient funds. The
    caller adopts the result only if it is also allowed by policy AND passes the recorder's invariant."""
    _check_amount(amount_cents)
    if src not in accounts_pre:
        raise InvariantViolation("unknown source account %r" % src)
    if dst not in accounts_pre:
        raise InvariantViolation("unknown destination account %r" % dst)
    if src == dst:
        raise InvariantViolation("source and destination are the same account %r" % src)
    if accounts_pre[src]["balance_cents"] < amount_cents:
        raise InvariantViolation("insufficient funds in %s (%d < %d) — no overdraft" %
                                 (src, accounts_pre[src]["balance_cents"], amount_cents))

    post = {aid: dict(a) for aid, a in accounts_pre.items()}   # deep-enough copy (leaf values are scalars)
    post[src]["balance_cents"] -= amount_cents
    post[dst]["balance_cents"] += amount_cents

    _check_accounts_nonneg(post)
    if total_cents(post) != total_cents(accounts_pre):          # conservation (cannot trip with int math, asserted anyway)
        raise InvariantViolation("conservation breached: %d -> %d" % (total_cents(accounts_pre), total_cents(post)))
    return post


def dollars(cents):
    """Display helper ONLY — never feeds a balance or a hash. Presentation is the one place floats are OK."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return "%s$%d.%02d" % (sign, cents // 100, cents % 100)
