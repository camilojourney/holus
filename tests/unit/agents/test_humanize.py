"""Tests for the humanization pipeline.

Covers:
  - load_personal_context: file loading and error handling
  - select_personal_context: filtering by product, topic, count
  - format_personal_context: output format
  - humanize_text: LLM call structure, voice examples, fallback on error
  - turing_test: score parsing, correct/wrong identification, fallback on error
  - _parse_turing_response: JSON parsing edge cases
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from holus.agents.marketing.humanize import (
    HAIKU_MODEL,
    HUMANIZE_SYSTEM_PROMPT,
    _parse_turing_response,
    format_personal_context,
    humanize_text,
    load_personal_context,
    select_personal_context,
    turing_test,
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


def _make_proxy_response(content: str) -> MagicMock:
    """Build a mock requests.Response for the LLM proxy."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [{"message": {"content": content}}],
    }
    resp.raise_for_status = MagicMock()
    return resp


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
        # Should include genpeli-specific entries + opinion that mentions genpeli
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
        # At least the debugging anecdote should be present
        texts = [e["text"] for e in result]
        assert any("off-by-one" in t for t in texts)

    @patch("holus.agents.marketing.humanize.load_personal_context")
    def test_combined_product_and_topic_filter(self, mock_load: MagicMock) -> None:
        """Product and topic filters work together."""
        mock_load.return_value = SAMPLE_CONTEXT
        result = select_personal_context(product="holus", topics=["debugging"], count=10)
        assert len(result) >= 1
        # The debugging anecdote should rank highest
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
        # Should fall back to full pool
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
        # Should contain truncated text with ...
        assert "..." in result
        # Each bullet should not exceed 210 chars (200 + "- " prefix + "...")
        for line in result.split("\n"):
            if line.startswith("- "):
                # "- " + 200 chars + "..." = 206
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
        # The no-text and empty-text entries should not appear as bullets
        bullet_count = result.count("\n- ")
        assert bullet_count == 1


# ---------------------------------------------------------------------------
# Tests: humanize_text
# ---------------------------------------------------------------------------


class TestHumanizeText:
    """Tests for humanize_text."""

    @patch("holus.agents.marketing.humanize.requests.post")
    def test_calls_proxy_with_correct_payload(self, mock_post: MagicMock) -> None:
        """Verifies the LLM proxy is called with Haiku model and correct prompts."""
        mock_post.return_value = _make_proxy_response("Rewritten text here.")
        result = humanize_text("Original AI text.")

        assert result == "Rewritten text here."
        mock_post.assert_called_once()

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload is not None
        assert payload["model"] == HAIKU_MODEL
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][0]["content"].startswith(HUMANIZE_SYSTEM_PROMPT[:50])
        assert payload["messages"][1]["role"] == "user"
        assert "Original AI text." in payload["messages"][1]["content"]

    @patch("holus.agents.marketing.humanize.requests.post")
    def test_includes_voice_examples_in_prompt(self, mock_post: MagicMock) -> None:
        """Voice examples are appended to the system prompt when provided."""
        mock_post.return_value = _make_proxy_response("Styled text.")
        examples = ["Example post one.", "Example post two."]
        humanize_text("Some text.", voice_examples=examples)

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        system_content = payload["messages"][0]["content"]
        assert "Voice Examples" in system_content
        assert "Example post one." in system_content
        assert "Example post two." in system_content

    @patch("holus.agents.marketing.humanize.requests.post")
    def test_falls_back_to_original_on_http_error(self, mock_post: MagicMock) -> None:
        """Returns original text when the HTTP call fails."""
        mock_post.side_effect = ConnectionError("proxy down")
        result = humanize_text("Original text stays.")
        assert result == "Original text stays."

    @patch("holus.agents.marketing.humanize.requests.post")
    def test_falls_back_to_original_on_empty_response(self, mock_post: MagicMock) -> None:
        """Returns original text when LLM returns empty content."""
        mock_post.return_value = _make_proxy_response("")
        result = humanize_text("Original text stays.")
        assert result == "Original text stays."

    @patch("holus.agents.marketing.humanize.requests.post")
    def test_uses_temperature_0_7(self, mock_post: MagicMock) -> None:
        """Humanization uses temperature 0.7 for creative output."""
        mock_post.return_value = _make_proxy_response("Creative output.")
        humanize_text("Input text.")

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["temperature"] == 0.7


# ---------------------------------------------------------------------------
# Tests: turing_test
# ---------------------------------------------------------------------------


class TestTuringTest:
    """Tests for turing_test."""

    @patch("holus.agents.marketing.humanize.requests.post")
    def test_correctly_identified_returns_confidence(self, mock_post: MagicMock) -> None:
        """When the model correctly identifies the AI post, return its confidence."""
        # We need to figure out which position the candidate ends up at.
        # Since random.randint is used, we patch it to control placement.
        with patch("holus.agents.marketing.humanize.random.randint", return_value=1):
            # Candidate at position 2 (1-indexed: inserted at index 1)
            response_json = json.dumps({"ai_post": 2, "confidence": 0.85})
            mock_post.return_value = _make_proxy_response(response_json)

            score = turing_test(
                candidate="This is the AI post.",
                real_posts=["Real post one.", "Real post two.", "Real post three."],
            )
            assert score == pytest.approx(0.85)

    @patch("holus.agents.marketing.humanize.requests.post")
    def test_wrong_identification_returns_zero(self, mock_post: MagicMock) -> None:
        """When the model picks the wrong post, return 0.0 (undetectable)."""
        with patch("holus.agents.marketing.humanize.random.randint", return_value=0):
            # Candidate at position 1 (1-indexed)
            response_json = json.dumps({"ai_post": 3, "confidence": 0.9})
            mock_post.return_value = _make_proxy_response(response_json)

            score = turing_test(
                candidate="AI content.",
                real_posts=["Real one.", "Real two."],
            )
            assert score == 0.0

    @patch("holus.agents.marketing.humanize.requests.post")
    def test_falls_back_on_http_failure(self, mock_post: MagicMock) -> None:
        """Returns 0.5 when the LLM call fails."""
        mock_post.side_effect = ConnectionError("network error")
        score = turing_test("AI text.", real_posts=["Real text."])
        assert score == 0.5

    def test_falls_back_on_empty_real_posts(self) -> None:
        """Returns 0.5 when no real posts are provided."""
        score = turing_test("AI text.", real_posts=[])
        assert score == 0.5

    @patch("holus.agents.marketing.humanize.requests.post")
    def test_prompt_includes_all_posts(self, mock_post: MagicMock) -> None:
        """All posts (real + candidate) appear in the user message."""
        with patch("holus.agents.marketing.humanize.random.randint", return_value=0):
            response_json = json.dumps({"ai_post": 1, "confidence": 0.5})
            mock_post.return_value = _make_proxy_response(response_json)

            turing_test(
                candidate="Candidate post.",
                real_posts=["Real A.", "Real B."],
            )

            call_kwargs = mock_post.call_args
            payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
            user_content = payload["messages"][1]["content"]
            assert "Candidate post." in user_content
            assert "Real A." in user_content
            assert "Real B." in user_content
            assert "Post 1" in user_content
            assert "Post 2" in user_content
            assert "Post 3" in user_content

    @patch("holus.agents.marketing.humanize.requests.post")
    def test_uses_temperature_zero(self, mock_post: MagicMock) -> None:
        """Turing test uses temperature 0.0 for deterministic evaluation."""
        with patch("holus.agents.marketing.humanize.random.randint", return_value=0):
            response_json = json.dumps({"ai_post": 1, "confidence": 0.5})
            mock_post.return_value = _make_proxy_response(response_json)

            turing_test("AI text.", real_posts=["Real text."])

            call_kwargs = mock_post.call_args
            payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
            assert payload["temperature"] == 0.0


# ---------------------------------------------------------------------------
# Tests: _parse_turing_response
# ---------------------------------------------------------------------------


class TestParseTuringResponse:
    """Tests for _parse_turing_response edge cases."""

    def test_correct_pick_returns_confidence(self) -> None:
        """Correct identification returns the confidence value."""
        raw = json.dumps({"ai_post": 2, "confidence": 0.75})
        assert _parse_turing_response(raw, candidate_pos=2) == pytest.approx(0.75)

    def test_wrong_pick_returns_zero(self) -> None:
        """Wrong identification returns 0.0."""
        raw = json.dumps({"ai_post": 1, "confidence": 0.9})
        assert _parse_turing_response(raw, candidate_pos=3) == 0.0

    def test_handles_markdown_fenced_json(self) -> None:
        """Strips markdown code fences before parsing."""
        raw = '```json\n{"ai_post": 2, "confidence": 0.6}\n```'
        assert _parse_turing_response(raw, candidate_pos=2) == pytest.approx(0.6)

    def test_clamps_confidence_to_0_1(self) -> None:
        """Confidence values outside [0, 1] are clamped."""
        raw = json.dumps({"ai_post": 1, "confidence": 1.5})
        assert _parse_turing_response(raw, candidate_pos=1) == 1.0

        raw = json.dumps({"ai_post": 1, "confidence": -0.3})
        assert _parse_turing_response(raw, candidate_pos=1) == 0.0

    def test_returns_0_5_on_malformed_json(self) -> None:
        """Returns 0.5 on invalid JSON."""
        assert _parse_turing_response("not json at all", candidate_pos=1) == 0.5

    def test_returns_0_5_on_missing_fields(self) -> None:
        """Returns 0.5 when required fields are missing."""
        raw = json.dumps({"something": "else"})
        # ai_post defaults to 0, which won't match candidate_pos=1,
        # so this returns 0.0 (wrong pick), not 0.5
        assert _parse_turing_response(raw, candidate_pos=1) == 0.0

    def test_handles_string_confidence(self) -> None:
        """Handles confidence provided as string instead of float."""
        raw = json.dumps({"ai_post": 2, "confidence": "0.8"})
        assert _parse_turing_response(raw, candidate_pos=2) == pytest.approx(0.8)
