"""SPEC-013: Validate launchd plist configurations.

Regression test: marketing interval must be 1800s (30 min), not 21600s (6h).
"""

from __future__ import annotations

import plistlib
from pathlib import Path

PLIST_DIR = Path(__file__).parent.parent.parent.parent / "infra" / "launchd"


def _load_plist(name: str) -> dict:
    path = PLIST_DIR / name
    assert path.exists(), f"Plist not found: {path}"
    with path.open("rb") as f:
        return plistlib.load(f)


class TestMarketingPlist:
    """com.holus.marketing.plist — SPEC-013."""

    def test_interval_is_30_minutes(self):
        """Regression: interval must be 1800s (30 min), not 21600s (6h)."""
        plist = _load_plist("com.holus.marketing.plist")
        assert plist["StartInterval"] == 1800, (
            f"Marketing interval should be 1800s (30min), got {plist['StartInterval']}s"
        )

    def test_label_matches_filename(self):
        plist = _load_plist("com.holus.marketing.plist")
        assert plist["Label"] == "com.holus.marketing"

    def test_runs_holus_cli(self):
        plist = _load_plist("com.holus.marketing.plist")
        cmd = " ".join(plist["ProgramArguments"])
        assert "python -m holus" in cmd


class TestHealthPlist:
    """com.holus.health.plist — SPEC-013."""

    def test_interval_is_5_minutes(self):
        plist = _load_plist("com.holus.health.plist")
        assert plist["StartInterval"] == 300, (
            f"Health interval should be 300s (5min), got {plist['StartInterval']}s"
        )


class TestImprovePlist:
    """com.holus.improve.plist — SPEC-013."""

    def test_runs_weekly(self):
        plist = _load_plist("com.holus.improve.plist")
        # Weekly = StartCalendarInterval with Weekday
        assert "StartCalendarInterval" in plist
