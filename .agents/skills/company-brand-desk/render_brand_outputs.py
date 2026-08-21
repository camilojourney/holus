#!/usr/bin/env python3
"""Render deterministic outputs for company-brand-desk."""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.company_os import render_desk_outputs_cli


if __name__ == "__main__":
    raise SystemExit(render_desk_outputs_cli("brand"))
