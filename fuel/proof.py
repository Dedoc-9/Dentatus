"""
fuel/proof.py — a fuel run emits a `tessera` shard (Sibling 16), because the VM step IS a tessera rule.

`vm.vm_step` / `vm.vm_done` are pure, source-bindable functions over an integer state that carries the
program in its seed. So minting a proof of a bounded execution is exactly minting a tessera over that rule
-- a stranger replays the same VM step from the same seed and confirms the program ran exactly these steps,
used exactly this fuel, and halted exactly here. No trust in the executor required.
"""
import os
import sys

_WB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_WB, "tessera"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shard as T                                            # tessera/shard.py
import vm                                                    # fuel/vm.py


def prove(program, init_regs, fuel_limit, signer=None, meta=None):
    """Run the program under fuel and return a tessera shard binding the program + inputs + exact path."""
    seed = vm.seed_state(program, init_regs, fuel_limit)
    return T.mint(vm.vm_step, vm.vm_done, seed, max_steps=fuel_limit + 2, signer=signer, meta=meta)


def verify_proof(shard, verifier=None):
    """Re-run the VM from the shard's seed and confirm the claimed execution. (ok, detail)."""
    return T.verify(shard, vm.vm_step, vm.vm_done, verifier=verifier)
