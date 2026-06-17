"""MCL Observability (EXP-604). Decoupled game-layer telemetry: builds a content-addressed
telemetry bundle from the L1 API for the WebGL dashboard, and an SSE push adapter. Reaches the
core only via dentatus.api; never imports engine.*."""
from .telemetry import export_bundle
__all__ = ["export_bundle"]
