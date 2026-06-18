"""
fuel/vm.py — a deterministic, integer-only bounded-execution engine. The Absolute Integer Standard.

No float ever touches a value or a halting decision. Execution is a pure integer register machine; every
instruction costs integer **fuel**; when the remaining fuel is less than the next instruction's cost the
machine HALTS fail-closed (`out of fuel`) at the last completed step. Halting is therefore not an estimate
("approximately finished") — it is exact integer arithmetic, identical on every machine. Division by zero,
a bad jump, or a runaway loop all terminate fail-closed; nothing diverges, nothing drifts.

Each executed step transforms an integer state, and the state is content-addressable, so a whole run is
replayable -- `vm_step` / `vm_done` are written as a `tessera` rule, so `fuel.prove()` mints a real tessera
shard a stranger can replay offline (see proof.py).

HONEST BOUNDS:
  * This is a SMALL deterministic VM with a fixed integer op-set -- not a production smart-contract VM, not
    Turing-complete-with-guarantees beyond what is implemented. "No float drift" is real and total *within
    this engine*; it does not by itself create distributed consensus (compose with `quorum` for that).
  * Exact fuel is exact accounting of THIS op-set's costs -- it bounds logical work, not wall-clock or RAM
    (an OS can still OOM; that is `ration`'s honest bound too).
  * integrity != truth: a proof shows the program ran exactly these steps, never that the program is correct.

Stdlib only; imports chronicle read-only via the proof layer (Sibling Law).
"""

# weighted integer costs -- exact, no float "gas estimation"
COST = {"set": 1, "add": 1, "sub": 1, "mul": 2, "div": 2, "mod": 2, "jz": 1, "jnz": 1, "jmp": 1, "halt": 1}


def _val(operand, regs):
    """An operand is either an immediate int or a register name (str). Missing registers read 0."""
    return operand if isinstance(operand, int) and not isinstance(operand, bool) else regs.get(operand, 0)


def vm_step(state):
    """Execute ONE instruction. Pure: returns a NEW state dict; never mutates the input. Fail-closed on
    out-of-fuel / bad pc / div0 / unknown op (sets halted=True with a reason, optionally error=True)."""
    if state["halted"]:
        return state
    prog = state["prog"]
    pc = state["pc"]
    fuel = state["fuel"]
    if pc < 0 or pc >= len(prog):
        return {**state, "halted": True, "reason": "pc out of range", "error": True}
    op = prog[pc]
    code = op[0]
    cost = COST.get(code)
    if cost is None:
        return {**state, "halted": True, "reason": "unknown op %r" % code, "error": True}
    if fuel < cost:
        return {**state, "halted": True, "reason": "out of fuel"}      # last completed step is the valid state
    regs = dict(state["regs"])
    fuel -= cost
    npc = pc + 1

    if code == "set":
        regs[op[1]] = _val(op[2], regs)
    elif code == "add":
        regs[op[1]] = _val(op[2], regs) + _val(op[3], regs)
    elif code == "sub":
        regs[op[1]] = _val(op[2], regs) - _val(op[3], regs)
    elif code == "mul":
        regs[op[1]] = _val(op[2], regs) * _val(op[3], regs)
    elif code in ("div", "mod"):
        d = _val(op[3], regs)
        if d == 0:
            return {**state, "fuel": fuel, "halted": True, "reason": "division by zero", "error": True}
        regs[op[1]] = (_val(op[2], regs) // d) if code == "div" else (_val(op[2], regs) % d)
    elif code == "jz":
        if _val(op[1], regs) == 0:
            npc = op[2]
    elif code == "jnz":
        if _val(op[1], regs) != 0:
            npc = op[2]
    elif code == "jmp":
        npc = op[1]
    elif code == "halt":
        return {**state, "pc": pc, "fuel": fuel, "regs": regs, "halted": True, "reason": "halt"}
    return {"prog": prog, "pc": npc, "regs": regs, "fuel": fuel, "halted": False, "reason": None,
            "error": state.get("error", False)}


def vm_done(state):
    return bool(state["halted"])


def seed_state(program, init_regs, fuel_limit):
    """Build the initial VM state (the tessera seed). Program rides IN the state, so it is content-addressed
    and part of every step hash -- a shard binds the exact program AND the exact inputs."""
    return {"prog": [list(op) for op in program], "pc": 0, "regs": dict(init_regs),
            "fuel": int(fuel_limit), "halted": False, "reason": None, "error": False}


def run(program, init_regs, fuel_limit):
    """Execute to halt (clean, out-of-fuel, or error). Returns a summary. Bounded: steps <= fuel_limit since
    every op costs >= 1 fuel, so this always terminates."""
    state = seed_state(program, init_regs, fuel_limit)
    steps = 0
    while not vm_done(state):
        state = vm_step(state)
        steps += 1
        if steps > fuel_limit + 2:                          # safety: cannot happen (fuel bounds it), asserted anyway
            raise RuntimeError("fuel accounting invariant violated")
    return {"halted": True, "reason": state["reason"], "error": state.get("error", False),
            "steps": steps - 1, "fuel_used": fuel_limit - state["fuel"], "fuel_left": state["fuel"],
            "regs": state["regs"]}
