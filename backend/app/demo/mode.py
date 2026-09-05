"""Demo mode management (spec section 37)."""

from __future__ import annotations

import uuid
from enum import StrEnum

from pydantic import BaseModel


class DemoMode(StrEnum):
    """System demo execution mode."""

    LIVE = "LIVE"
    REPLAY = "REPLAY"


class DemoModeConfig(BaseModel):
    """Configuration state for demo mode."""

    global_mode: DemoMode = DemoMode.LIVE
    close_run_modes: dict[str, DemoMode] = {}


class DemoModeManager:
    """Manages global and per-close-run LIVE vs REPLAY demo execution mode."""

    def __init__(self) -> None:
        self._config = DemoModeConfig()

    def get_mode(self, close_run_id: uuid.UUID | None = None) -> DemoMode:
        """Get the effective demo mode for a close run, falling back to global mode."""
        if close_run_id is not None:
            cr_str = str(close_run_id)
            if cr_str in self._config.close_run_modes:
                return self._config.close_run_modes[cr_str]
        return self._config.global_mode

    def set_mode(self, mode: DemoMode | str, close_run_id: uuid.UUID | None = None) -> DemoMode:
        """Set the demo mode globally or for a specific close run."""
        if isinstance(mode, str):
            mode = DemoMode(mode.upper())
        if close_run_id is not None:
            self._config.close_run_modes[str(close_run_id)] = mode
        else:
            self._config.global_mode = mode
        return mode

    def reset(self) -> None:
        """Reset back to default LIVE mode."""
        self._config = DemoModeConfig()


# Singleton demo mode manager
demo_mode_manager = DemoModeManager()
