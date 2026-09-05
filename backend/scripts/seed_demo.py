"""Seed the NovaScale AI demo dataset (deterministic)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make the backend package importable when running this script directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data.seed import demo_seed  # noqa: E402

if __name__ == "__main__":
    asyncio.run(demo_seed())
    print("Seed complete.")
