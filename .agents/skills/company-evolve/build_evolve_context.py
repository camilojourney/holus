#!/usr/bin/env python3
"""Build deterministic context for company-evolve."""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.company_os import build_evolve_context_cli


if __name__ == "__main__":
    raise SystemExit(build_evolve_context_cli())
