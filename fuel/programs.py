"""
fuel/programs.py — a tiny label-resolving assembler + canonical programs for the integer VM.

Programs are lists of integer ops (see vm.py). `assemble` lets you write readable label-based jumps; it
resolves labels to instruction indices. `syracuse_program` is the flagship: it computes a number's
compressed-Syracuse stopping time entirely in integers, so feeding it a `crucible` hard seed exercises the
fuel engine on the most chaotic deterministic workload available.
"""


def assemble(asm):
    """asm: list of tuples. ("label", NAME) marks a position; jump targets that are label names resolve to
    indices. Target positions are arg[2] for jz/jnz and arg[1] for jmp (data operands are left untouched)."""
    prog, labels = [], {}
    for item in asm:
        if item[0] == "label":
            labels[item[1]] = len(prog)
        else:
            prog.append(list(item))
    for op in prog:
        if op[0] in ("jz", "jnz") and isinstance(op[2], str) and op[2] in labels:
            op[2] = labels[op[2]]
        elif op[0] == "jmp" and isinstance(op[1], str) and op[1] in labels:
            op[1] = labels[op[1]]
    return prog


def syracuse_program():
    """Compute s = compressed-Syracuse stopping time of register `n`. Halts when n reaches 1.
    Registers: n (input, mutated to 1), s (step count), t/r (scratch)."""
    return assemble([
        ("label", "LOOP"),
        ("set", "t", "n"), ("sub", "t", "t", 1), ("jz", "t", "END"),   # if n == 1 -> END
        ("mod", "r", "n", 2), ("jz", "r", "EVEN"),                     # if n even -> EVEN
        ("mul", "n", "n", 3), ("add", "n", "n", 1), ("div", "n", "n", 2), ("jmp", "INC"),  # odd: (3n+1)/2
        ("label", "EVEN"), ("div", "n", "n", 2),                       # even: n/2
        ("label", "INC"), ("add", "s", "s", 1), ("jmp", "LOOP"),
        ("label", "END"), ("halt",),
    ])


def sum_to_program():
    """Compute s = 0+1+...+(k) for register `k` (a simple bounded counter loop), for a non-Collatz example."""
    return assemble([
        ("label", "LOOP"),
        ("jz", "k", "END"),
        ("add", "s", "s", "k"), ("sub", "k", "k", 1), ("jmp", "LOOP"),
        ("label", "END"), ("halt",),
    ])
