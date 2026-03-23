"""Test package setup for MCP unit tests."""

from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

agents_package = types.ModuleType("holus.agents")
agents_package.__path__ = [str(SRC / "holus" / "agents")]
sys.modules.setdefault("holus.agents", agents_package)
