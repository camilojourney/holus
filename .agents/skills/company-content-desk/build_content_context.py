#!/usr/bin/env python3
"""Build deterministic context for company-content-desk."""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.company_os import build_desk_context_cli


if __name__ == "__main__":
    raise SystemExit(build_desk_context_cli("content"))
