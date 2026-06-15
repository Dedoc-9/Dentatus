"""
Clean Room boundary guard. Scans game/ for forbidden direct engine imports.

The game layer must reach the core ONLY via the dentatus.* public contract. Any
`import engine` / `from engine ...` under game/ violates the Clean Room Protocol and
fails this guard (wire it into CI). This keeps the AGPL core decoupled from the game
license boundary and prevents game semantics from contaminating the engine.
"""
import os
import re
import sys

FORBIDDEN = [re.compile(r"^\s*import\s+engine(\.|\s|$)"),
             re.compile(r"^\s*from\s+engine(\.|\s)")]
GAME_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def scan():
    violations = []
    for root, _dirs, files in os.walk(GAME_ROOT):
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(root, fn)
            with open(path, encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    if any(p.match(line) for p in FORBIDDEN):
                        violations.append((path, i, line.rstrip()))
    return violations


def main():
    v = scan()
    if v:
        print("CLEAN ROOM VIOLATION — game/ must not import engine.* directly:")
        for path, i, line in v:
            print(f"  {path}:{i}: {line}")
        sys.exit(1)
    print("Clean Room guard PASS: no direct engine.* imports under game/ (handshake via dentatus.* only)")


if __name__ == "__main__":
    main()
