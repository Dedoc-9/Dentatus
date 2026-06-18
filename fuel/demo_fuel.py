"""
fuel/demo_fuel.py — the Absolute Integer Standard: exact-fuel bounded execution, fail-closed, proof-emitting.

  A. EXACT EXECUTION   — run the syracuse program; the step count and fuel used are exact integers.
  B. FAIL-CLOSED       — too little fuel halts at the last completed step (out of fuel); div-by-zero errors.
  C. DETERMINISM       — two runs of the same program produce byte-identical results (no float, no drift).
  D. CRUCIBLE HAMMER   — a reverse-generated hard seed is executed to an exact halt within budget.
  E. PROOF             — the run mints a tessera shard a stranger replays offline; tampering is caught.

Run:  PYTHONHASHSEED=0 python3 demo_fuel.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_WB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_WB, "syracuse"))
sys.path.insert(0, os.path.join(_WB, "crucible"))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
import vm as V
import programs as P
import proof as PR
import orbit as SY
import forest as C
from signing import Ed25519Signer, ed25519_available

PROG = P.syracuse_program()


def main():
    print("A) EXACT EXECUTION (syracuse stopping-time program, pure integer):")
    for n in (3, 27, 97):
        r = V.run(PROG, {"n": n, "s": 0}, fuel_limit=100000)
        print("   n=%-3d -> halt=%-5s steps=%-4d fuel_used=%-5d s=%d  (syracuse S=%d)"
              % (n, r["reason"], r["steps"], r["fuel_used"], r["regs"]["s"], SY.gates(n)["stopping_time"]))

    print("\nB) FAIL-CLOSED:")
    r = V.run(PROG, {"n": 27, "s": 0}, fuel_limit=50)
    print("   fuel=50 (too little): reason=%s  partial s=%d  fuel_left=%d  error=%s"
          % (r["reason"], r["regs"]["s"], r["fuel_left"], r["error"]))
    z = V.run([["div", "x", "x", 0]], {"x": 5}, fuel_limit=10)
    print("   division by zero    : reason=%s  error=%s\n" % (z["reason"], z["error"]))

    print("C) DETERMINISM (no float can drift this):")
    a = V.run(PROG, {"n": 27, "s": 0}, 100000)
    b = V.run(PROG, {"n": 27, "s": 0}, 100000)
    print("   two runs byte-identical:", a == b, "\n")

    print("D) CRUCIBLE HAMMER (reverse-generated hard seed forced through fuel):")
    hard = C.seed_just_under(40, value_ceiling=10 ** 7)
    r = V.run(PROG, {"n": hard["n"], "s": 0}, 100000)
    print("   n=%d altitude=%dx -> s=%d  fuel_used=%d  (exact, matches syracuse S=%d)\n"
          % (hard["n"], hard["altitude"], r["regs"]["s"], r["fuel_used"], hard["stopping_time"]))

    print("E) PROOF — a fuel run emits a tessera shard, a stranger verifies it offline:")
    signer = Ed25519Signer() if ed25519_available() else None
    shard = PR.prove(PROG, {"n": hard["n"], "s": 0}, 100000, signer=signer)
    print("   shard: %d VM steps  signed=%s  path_hash=%s" % (shard["steps"], shard["signature"] is not None, shard["path_hash"][:16]))
    print("   stranger replays    :", PR.verify_proof(shard))
    print("   tampered (steps -5) :", PR.verify_proof(dict(shard, steps=shard["steps"] - 5))[1])
    print("\n   Halting is exact integer fuel, never an estimate. integrity != truth.")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("\n[fuel] set PYTHONHASHSEED=0 (the step/proof hashes must match across machines).\n\n")
        raise SystemExit(2)
    main()
