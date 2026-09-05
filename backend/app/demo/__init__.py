"""Demo safety net package (spec section 37)."""

from app.demo.mode import DemoMode, DemoModeConfig, DemoModeManager, demo_mode_manager
from app.demo.trace_player import TracePlayer
from app.demo.trace_recorder import TraceRecorder, get_golden_trace_definitions, seed_golden_traces

__all__ = [
    "DemoMode",
    "DemoModeConfig",
    "DemoModeManager",
    "demo_mode_manager",
    "TracePlayer",
    "TraceRecorder",
    "get_golden_trace_definitions",
    "seed_golden_traces",
]
