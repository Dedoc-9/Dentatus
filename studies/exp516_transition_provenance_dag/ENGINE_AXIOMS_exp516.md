# EXP-516 — Transition Log → Provenance DAG (Fork ο)

**Protocol** `exp516-v1` · **Declaration hash** `e028deae2adcaeb6126e399577835413a735594ddd3569b82271912553cdf85f`
**Scope** NO engine edits. `game/agency/transition_dag.py` consumes `dentatus.core`
(`Claim`, `Provenance`, `now_iso`) + `game.agency.phase_change`. Engine FROZEN.

---

## A1 — Phase changes become first-class lineage

EXP-515 produced witnessed transitions but left them as loose records. Fork ο threads each into the
engine's **Claim provenance DAG**: a melted manifold is a genuine child `Claim` whose `Provenance`
points to the pre-melt node.

    node  : Claim,  id = SHA256(provenance ⊕ payload ⊕ t ⊕ protocol)[:16]   (EXP-601, timestamp-excluded)
    edge  : { parent, child, operator_id = "PhaseChange:<mode>", witness }
    payload(child) = H_after            # the P_yz-invariant material eigenvalue hash (EXP-515)
    t(child)       = t(parent) + 1

```python
prov  = core.Provenance(parent_ids=(parent.id,), operator_id="PhaseChange:minimal", timestamp=now_iso())
child = core.Claim(provenance=prov, payload=witness["H_after"], stalk=new_stalk, t=parent.t + 1)
```

Because `Claim.id` is content-addressed and excludes the wall-clock timestamp, the lineage
`diamond → glass → fluid` is deterministic and cryptographically traceable (Fork A [3], [10]).

## A2 — Time-travel queries

    ancestry(id)  -> [root … id]                 # walk parent edges back to a root
    lineage(id)   -> [witnessed transitions]      # the "how did this become this" record

Verified (Fork A [5]): a diamond sheared twice yields `ancestry = [diamond, glass, softer]` with
`lineage` chi `[(0.05→0.63), (0.63→0.84)]` — a verifiable history, not a single snapshot.

## A3 — Growth discipline (only real transitions extend history)

The DAG grows **only** on a `melted` outcome. `stable` (already admissible) and `unsurvivable`
(`χ_required > 1`) add no node and no edge (Fork A [6], [7]) — history records *transitions*, not
non-events. Recording is append-only: later records never mutate prior nodes/edges or the parent Claim
(Fork A [9]), and the whole structure serialises (`to_dict`).

## A4 — Clean room & backreaction

Built entirely through the `dentatus.core` facade (`Claim`/`Provenance` are exported, as `api.py`
itself uses them) — no `engine.*` import, engine frozen. The transition DAG is an **audit lineage**: it
constructs valid Claim nodes but does not inject them into a live `MuState` (that would be the dual
channel mutating world state). The reported→enacted→**recorded** chain stays in the game layer,
preserving the engine as a stateless oracle.

## A5 — P_yz invariance

Child payloads are the material **eigenvalue** hashes, and `Claim.id` excludes the stalk, so every
child id, witness hash, and the entire ancestry are reflection-invariant (Fork B, all 5).

---

## DEV NOTE — Ghost #50: audit-vs-live gap & destination-addressed convergence

1. **Audit lineage ≠ live state.** The DAG records valid Claim nodes for each transition, but the
   engine's running `MuState` does not contain them — injecting the melted claim (rewiring entailments,
   recomputing `H_t`) is a separate, heavier operation deliberately *not* done here, to keep the engine
   frozen and `H_verified` uncontaminated by a game-layer policy. The residual is the gap between the
   audit DAG and the live world; closing it (a witnessed `MuState` insertion at the L1 boundary) is
   Fork ρ. Until then, the DAG answers "how did this material come to be?" but is not itself the world.

2. **Content-addressing by destination ⇒ confluence merges.** A child id is fixed by
   `(parent.id, operator_id, H_after, t)`. Two *different* shears that melt the same parent to the same
   resulting eigenvalue spectrum produce the **same** child id — distinct paths converge to one node.
   This is the EXP-confluence property surfacing in the lineage (a feature: identical materials are
   identical states), but it means **path information lives in the edges, not the node identity**. If a
   future query needs to distinguish *how* a state was reached (not just *that* it was), it must read
   the edge witnesses, not the node id. The `t*`/χ/strain of a transition are edge metadata by design.

## Suggested improvements / forks

- **Fork ρ (live MuState injection).** A witnessed L1 operation that inserts the melted Claim into the
  running world (re-wires Sector-D entailments, recomputes `H_t`), closing the audit-vs-live gap with
  full hash continuity.
- **Fork σ (merge-aware lineage).** Make `ancestry` return the *multi-parent* DAG (not just the
  single-parent walk) so convergent melt histories are visible as merges, not collapsed.
- **Fork τ (replay / time-travel debugger).** Given any `H`, reconstruct the exact stalk sequence and
  re-run forward — deterministic replay over the content-addressed lineage.

## Foreign-language note (rhetoric → code)

The lineage is a *Stammbaum* (genealogical tree) of *Materiezustände* (material states), each
*Übergang* (transition) a *bezeugte* (witnessed), *inhaltsadressierte* (content-addressed) edge. Because
identity is fixed by the *Zielzustand* (destination state), convergent *Übergänge* *verschmelzen*
(merge) — *Konfluenz*. The *Stammbaum* is for *Wirtschaftsprüfung* (auditing) and *Zeitreise*
(time-travel), but it is not yet the *lebende Welt* (live world): that is the *Audit-gegen-Live-Lücke*
of Ghost #50.
