# Lattice threat model & trust assumptions

What the 2D attestation lattice (`quorum/` lateral ⊕ `pact/` temporal), together with `guard_server/`
privilege isolation, **does** and **does not** mechanically resist — and the custody choices that decide
whether it withstands a single-authority intervention.

**Motivating case (used neutrally).** In June 2026 the US Commerce Department directed Anthropic to suspend
foreign-national access to the Fable 5 and Mythos 5 models under export controls; Anthropic complied while
disputing the rationale, and several allied governments framed frontier-model access as "critical
infrastructure." This document does **not** assess whether that intervention was justified. It uses it only
as a clean example of one adversary class: an **overt, lawful, single-authority compulsion of the operator
who legitimately holds the keys and the compute** — not a hack, forgery, or silent tamper.

**Standing caveat.** Everything below concerns *integrity and accountability of a running system*. None of
it certifies that a decision was correct, fair, or lawful. Integrity is not truth; consensus is not truth.

## The three boundaries, and what each actually defends

| Boundary | Mechanism | Defends against | Fault it raises |
|---|---|---|---|
| Privilege isolation (`guard_server`) | out-of-process PEP; policy + signing key behind a boundary the agent calls but cannot weaken | the **agent** subverting or loosening policy | `TransitionRefused` / signed request-bound verdict |
| Lateral (`quorum`) | k-of-n independently-keyed witnesses must produce the same exact 256-bit hash | a single honest-but-wrong or singly-compromised node; silent divergence | no certificate; fork set + named dissent |
| Temporal (`pact`) | each certified round cross-attested to the prior under a pinned notary key | retroactive history rewrite / injection | `CovenantBreach` / broken link, attributed to the exact step |

Note the precise scope of `guard_server`: it defends the policy boundary **from the agent**, not from the
**policy authority**. It stops a jailbroken agent from weakening the rule; it does nothing when the entity
that legitimately pins the rule is itself compelled to change it. That distinction is the crux of the Fable
5 class.

## The adversary ladder

Ordered by capability; the line marks where the architecture stops defending.

| # | Adversary | Outcome |
|---|---|---|
| 1 | External attacker, no keys | **Blocked** — signatures + pinned registry reject every unauthenticated vote/receipt |
| 2 | Jailbroken local agent | **Bounded** — the agent holds no authority; its proposal must pass the local invariant *and* match independent witnesses, or it is refused fail-closed |
| 3 | Single compromised node / insider | **Detected & attributed** — diverges laterally (no quorum) or breaks the covenant; the exact node/link is named |
| 4 | Colluding minority (`< k`) | **Detected, not gated** — outvoted; surfaces as the dissent ghost / rising `S_t`, never flips a certificate |
| — | — | **— defense ceiling —** |
| 5 | Colluding `≥ k` quorum, or a colluding notary, or the key-pinner/operator | **Not defended** — they *are* the trust root; the certificate proves agreement among the named keys, and they hold the named keys |
| 6 | Sovereign compelling the operator (Fable 5 class) | **Not defended by code** — inherits #5: can re-pin keys, compel ≥k witnesses if one operator runs them, or pull the compute entirely |

## What the lattice changes about the Fable 5 class — and what it can't

**It changes the *shape* of the intervention, if witnesses are genuinely independent.** With witnesses
distributed across separate operators and jurisdictions, a single authority can no longer covertly rewrite
history or flip state. Any such act becomes (a) **tamper-evident** to anyone holding the pinned public keys,
and (b) **multi-party** — it must compel a quorum of jurisdictions, not one company. A silent, unilateral,
unattributable kill-switch becomes a visible, attributable, quorum-gated one. That is precisely the
"critical infrastructure / not one nation's kill-switch" posture the allied governments were reaching for.

**It cannot do three things, and these are hard limits:**

1. **It cannot override compulsion of the key-holder.** A sovereign who can lawfully order the operator can
   order it to re-pin the registry, stop signing, or hand over keys. The architecture trusts the key-pinner
   by assumption; whoever can compel the key-pinner inherits that trust.
2. **It cannot keep compute online.** The Fable 5 suspension acted at the **weights / inference / GPU**
   layer. `quorum` and `pact` certify *decisions and state transitions* — they do not host the model or
   replicate the hardware. You cannot consensus-certify a model into running when the entity operating the
   compute is ordered to stop. A compute-layer kill-switch is out of this lattice's band.
3. **It cannot manufacture independence.** Witness independence is the load-bearing assumption, and it is a
   legal/operational fact about *who runs the nodes*, not a property the code can establish or verify (the
   tally cannot detect a Sybil operator behind several "witnesses").

## The decisive variable: witness & key custody

Resistance to a single-authority intervention is won or lost here — in governance, not in `quorum/`. The
same code is intervention-evident or intervention-trivial depending entirely on these choices:

| Custody question | Collapses the defense | Strengthens it |
|---|---|---|
| Who **runs** the witnesses? | one operator runs all → under compulsion the quorum collapses to one node | N independent legal entities |
| **Where** are they hosted? | one jurisdiction → one sovereign reaches all | jurisdictions chosen so no single one holds ≥k |
| Who **pins** the registry / holds private keys? | operator holds all → operator (and whoever compels it) is the trust root | split custody; registry changes are themselves lattice-events |
| Who is the **notary** for the temporal spine? | single notary → single compulsion point | rotating or multi-party notary |
| `k` vs `n` and geography | k reachable within one jurisdiction | k > any single jurisdiction's node count |
| Who may **re-pin / rotate** keys? | silent re-pinning authority = silent seizure | re-pin requires its own quorum and is logged as a visible event |

Design stance that follows (optional, honest):

- Distribute witnesses across independent entities and jurisdictions; choose `k` so no single jurisdiction
  controls a quorum.
- Make **registry and notary changes themselves lattice events**, so re-pinning keys is tamper-evident
  rather than a quiet back door — turning "seize the trust root" into a publicly visible act.
- Publish the pinned public keys widely, so any third party (an ally, a regulator, an independent auditor)
  can verify the whole 2D trail without the operator's cooperation. This is what converts a kill-switch
  from a private action into a publicly attributable one.
- Accept the compute-layer limit explicitly: if *availability under intervention* matters, that is an
  infrastructure problem (multi-region / multi-operator hosting, escrowed weights), separate from and
  unaddressed by this lattice.

## Bottom line

`guard_server`, `quorum`, and `pact` are *in order with each other* — they compose cleanly and pass (17/17
suites). They make a single-authority intervention **evident, attributable, and quorum-gated** instead of
silent and unilateral — a real and defensible improvement, and exactly the property at stake in the Fable 5
debate. They do **not** make a system intervention-proof: a sovereign who can compel the operator or pull
the compute is outside what code can resist, and the independence that would blunt such an actor is a
custody decision the math cannot make for you.
