"""Tests for the humanization pipeline.

Covers:
  - load_personal_context: file loading and error handling
  - select_personal_context: filtering by product, topic, count
  - format_personal_context: output format
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

from holus.agents.marketing.humanize import (
    format_personal_context,
    load_personal_context,
    select_personal_context,
)

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_CONTEXT: dict[str, list[dict[str, Any]]] = {
    "anecdotes": [
        {
            "id": "anecdote-001",
            "text": "The agent registry had a path off-by-one bug.",
            "products": ["holus"],
            "topics": ["debugging", "agent-registry"],
            "updated": "2026-03-26",
        },
        {
            "id": "anecdote-002",
            "text": "Sentence-aware truncation for repurposed content.",
            "products": ["holus"],
            "topics": ["content-repurposing", "text-processing"],
            "updated": "2026-03-26",
        },
    ],
    "metrics": [
        {
            "id": "metric-001",
            "text": "Holus has ~28,800 lines of Python source code.",
            "products": ["holus"],
            "topics": ["codebase-size", "engineering-velocity"],
            "updated": "2026-03-26",
        },
    ],
    "opinions": [
        {
            "id": "opinion-001",
            "text": "MCP over REST for silo communication.",
            "products": ["holus", "genpeli", "pilaster"],
            "topics": ["architecture", "mcp", "api-design"],
            "updated": "2026-03-26",
        },
    ],
    "project_facts": [
        {
            "id": "fact-001",
            "text": "Genpeli is an AI video editing pipeline for human footage.",
            "products": ["genpeli"],
            "topics": ["product-description", "video-editing"],
            "updated": "2026-03-26",
        },
        {
            "id": "fact-002",
            "text": "Pilaster is an AI image generation platform with memory.",
            "products": ["pilaster"],
            "topics": ["product-description", "image-generation"],
            "updated": "2026-03-26",
        },
    ],
}


# ---------------------------------------------------------------------------
# Tests: load_personal_context
# ---------------------------------------------------------------------------


class TestLoadPersonalContext:
    """Tests for load_personal_context."""

    @patch("holus.agents.marketing.humanize.PERSONAL_CONTEXT_PATH")
    def test_loads_valid_json(self, mock_path: MagicMock) -> None:
        """Loads and returns parsed JSON when file exists."""
        mock_path.read_text.return_value = json.dumps(SAMPLE_CONTEXT)
        result = load_personal_context()
        assert "anecdotes" in result
        assert len(result["anecdotes"]) == 2

    @patch("holus.agents.marketing.humanize.PERSONAL_CONTEXT_PATH")
    def test_returns_empty_on_missing_file(self, mock_path: MagicMock) -> None:
        """Returns empty dict when file does not exist."""
        mock_path.read_text.side_effect = FileNotFoundError("not found")
        result = load_personal_context()
        assert result == {}

    @patch("holus.agents.marketing.humanize.PERSONAL_CONTEXT_PATH")
    def test_returns_empty_on_malformed_json(self, mock_path: MagicMock) -> None:
        """Returns empty dict when file contains invalid JSON."""
        mock_path.read_text.return_value = "not valid json {"
        result = load_personal_context()
        assert result == {}


# ---------------------------------------------------------------------------
# Tests: select_personal_context
# ---------------------------------------------------------------------------


class TestSelectPersonalContext:
    """Tests for select_personal_context."""

    @patch("holus.agents.marketing.humanize.load_personal_context")
    def test_returns_correct_count(self, mock_load: MagicMock) -> None:
        """Returns up to *count* entries."""
        mock_load.return_value = SAMPLE_CONTEXT
        result = select_personal_context(count=2)
        assert len(result) <= 2

    @patch("holus.agents.marketing.humanize.load_personal_context")
    def test_returns_all_when_count_exceeds_pool(self, mock_load: MagicMock) -> None:
        """Returns all entries if count exceeds available entries."""
        mock_load.return_value = SAMPLE_CONTEXT
        total = sum(len(v) for v in SAMPLE_CONTEXT.values())
        result = select_personal_context(count=100)
        assert len(result) == total

    @patch("holus.agents.marketing.humanize.load_personal_context")
    def test_filters_by_product(self, mock_load: MagicMock) -> None:
        """Filters entries to those matching the specified product."""
        mock_load.return_value = SAMPLE_CONTEXT
        result = select_personal_context(product="genpeli", count=10)
        for entry in result:
            products = [p.lower() for p in entry.get("products", [])]
            assert "genpeli" in products

    @patch("holus.agents.marketing.humanize.load_personal_context")
    def test_filters_by_pilaster(self, mock_load: MagicMock) -> None:
        """Pilaster filter returns pilaster-tagged entries."""
        mock_load.return_value = SAMPLE_CONTEXT
        result = select_personal_context(product="pilaster", count=10)
        for entry in result:
            products = [p.lower() for p in entry.get("products", [])]
            assert "pilaster" in products

    @patch("holus.agents.marketing.humanize.load_personal_context")
    def test_filters_by_topics(self, mock_load: MagicMock) -> None:
        """Filters entries that overlap with the given topics."""
        mock_load.return_value = SAMPLE_CONTEXT
        result = select_personal_context(topics=["debugging"], count=10)
        texts = [e["text"] for e in result]
        assert any("off-by-one" in t for t in texts)

    @patch("holus.agents.marketing.humanize.load_personal_context")
    def test_combined_product_and_topic_filter(self, mock_load: MagicMock) -> None:
        """Product and topic filters work together."""
        mock_load.return_value = SAMPLE_CONTEXT
        result = select_personal_context(product="holus", topics=["debugging"], count=10)
        assert len(result) >= 1
        assert "off-by-one" in result[0]["text"]

    @patch("holus.agents.marketing.humanize.load_personal_context")
    def test_returns_empty_when_context_unavailable(self, mock_load: MagicMock) -> None:
        """Returns empty list when personal context cannot be loaded."""
        mock_load.return_value = {}
        result = select_personal_context(product="holus")
        assert result == []

    @patch("holus.agents.marketing.humanize.load_personal_context")
    def test_falls_back_to_full_pool_on_no_product_match(self, mock_load: MagicMock) -> None:
        """Returns entries from full pool if no product matches."""
        mock_load.return_value = SAMPLE_CONTEXT
        result = select_personal_context(product="nonexistent", count=3)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# Tests: format_personal_context
# ---------------------------------------------------------------------------


class TestFormatPersonalContext:
    """Tests for format_personal_context."""

    def test_formats_entries_as_bullet_list(self) -> None:
        """Entries are formatted as markdown bullet points."""
        entries = [
            {"text": "First fact about the system."},
            {"text": "Second fact about debugging."},
        ]
        result = format_personal_context(entries)
        assert "## Your Real Experiences" in result
        assert "- First fact about the system" in result
        assert "- Second fact about debugging" in result
        assert "Use at least ONE" in result

    def test_empty_entries_returns_empty_string(self) -> None:
        """Empty list returns empty string."""
        assert format_personal_context([]) == ""

    def test_truncates_long_text(self) -> None:
        """Long entry text is truncated to ~200 chars with ellipsis."""
        entries = [{"text": "x" * 300}]
        result = format_personal_context(entries)
        assert "..." in result
        for line in result.split("\n"):
            if line.startswith("- "):
                assert len(line) <= 210

    def test_skips_entries_without_text(self) -> None:
        """Entries missing 'text' field are skipped."""
        entries: list[dict[str, Any]] = [
            {"text": "Valid entry."},
            {"id": "no-text"},
            {"text": ""},
        ]
        result = format_personal_context(entries)
        assert "- Valid entry" in result
        bullet_count = result.count("\n- ")
        assert bullet_count == 1
