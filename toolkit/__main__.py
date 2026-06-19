"""Entry point.

    python3 -m toolkit               the full proof (all asserted properties)
    python3 -m toolkit tournament    compare() + robustness() tables
    python3 -m toolkit certify       certificate for future_surface
"""
import sys

from .benchmarks import run
from .tournament import compare, robustness
from .certify import certify
from .evaluate import evaluate
from .manifest import manifest
from .stage import stage
from .benchmarks import make_world
from . import policies


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "proof"
    if cmd == "proof":
        run()
    elif cmd == "tournament":
        pols = [policies.future_surface, policies.weighted_product, policies.min_gate,
                policies.magnitude, policies.random_priority]
        print(compare(pols, worlds=1000).table())
        print()
        print(robustness(pols).table())
    elif cmd == "certify":
        print(certify(policies.future_surface).report())
    elif cmd == "evaluate":
        print(evaluate(policies.future_surface).report())
    elif cmd == "manifest":
        print(manifest(policies.future_surface).to_json())
    elif cmd == "stage":
        action = stage(make_world(seed=2))
        print(action.report())
        if "--authorize" in argv and action.staged:
            import json as _json
            print("\nAUTHORIZED:\n" + _json.dumps(action.authorize(by="operator"), indent=2, sort_keys=True))
    else:
        print("usage: python -m toolkit [proof|tournament|certify|evaluate|manifest|stage]")


if __name__ == "__main__":
    main(sys.argv)
