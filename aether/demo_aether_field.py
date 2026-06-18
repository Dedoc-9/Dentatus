"""
aether/demo_aether_field.py — Stage D: self-describing generator field A(W,t,θ) + Magnus-2 (Bτ) +
the BCH bracket hierarchy + the dimensionless meta-observability M̂ / regime classifier.
Run under PYTHONHASHSEED=0.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixedpoint as F
import field as FD
import evolve as E

q = F.to_fp
A0 = [[0, q(3, 1), 0], [q(-3, 1), 0, 0], [0, 0, 0]]
B0 = [[0, 0, q(2, 1)], [0, 0, 0], [q(-2, 1), 0, 0]]


def main():
    print("A) THE GENERATOR FIELD A(W,t,θ) (constant ⇒ Bτ dormant; moving ⇒ Bτ live):")
    const = FD.GeneratorField(A0, B0, k_state=0, k_sched=0)
    move = FD.GeneratorField(A0, B0, k_state=q(2, 1), rc=(0, 1), k_sched=q(1, 2), period=400)
    W = F.identity(3)
    _, cb1, _, _ = FD.bracket_hierarchy(const.A(W, 0), const.A(W, 1))
    Ak = move.A(W, 0); Ak1 = move.A(E.lie_step(W, Ak, q(1, 1000)), 1)
    _, b1, b2, b3 = FD.bracket_hierarchy(Ak, Ak1)
    print("   constant: β₁=%d   moving: β₁=%d β₂=%d β₃=%d" % (cb1, b1, b2, b3))
    print("   (A reads only W, t, θ — never the ghost. Forward path is causally pure.)\n")

    print("B) EVOLVE under the moving field with Magnus-2 + meta-observability:")
    r = E.evolve_field_audited(F.identity(3), move, q(1, 1000), 30000,
                               audit_every=1000, measure_every=10, integrator="magnus2")
    print("   30000 steps: retractions=%d  β₁_max=%d  representation_pressure_max=%.2f"
          % (r["retractions"], r["beta1_max"], r["rep_pressure_max"] / F.SCALE))
    print("   regime histogram (declared coarse-grain boundaries):", r["regimes"])
    print("   structural Hₜ (θ⊕Z⊕S⊕W⊕pv):", r["structural_hash"][:16], " pv:", r["protocol_version"])

    print("\nC) THE FOUR-AXIS FINDING (honest): ghost ≠ representation pressure.")
    print("   The ghost measures GEOMETRIC fidelity (staying on Stiefel); representation pressure")
    print("   β₂/β₁ measures DYNAMICAL truncation. Magnus-2 moves them in OPPOSITE directions, so")
    print("   they are non-redundant channels — exactly why the meta-layer needs both axes.")
    print("\n   Honest bound: a clean Magnus-2 ACCURACY win needs an exact-orthogonal (Cayley/exp)")
    print("   application; with the additive (I+Ω) map the payoff is regime-dependent and inconclusive.")
    print("   What is solid: the bracket hierarchy, representation pressure, and regime classifier are")
    print("   deterministic OBSERVABLES — they never switch the integrator, only report its adequacy.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[aether] set PYTHONHASHSEED=0 (field state hashes must match across machines).\n\n")
        raise SystemExit(2)
    main()
