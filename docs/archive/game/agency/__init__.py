"""dentatus game-layer agency package (EXP-603). Decoupled: reaches the core ONLY via
dentatus.api (L1 handshake); never imports engine.*. Optional witness emission via the
sibling executable-epistemics toolkit (witness_core)."""
from .loop import AgencyLatch, run_reality_search
__all__ = ["AgencyLatch", "run_reality_search"]
