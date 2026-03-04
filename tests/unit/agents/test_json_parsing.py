"""Tests for json_parsing.py — JSON decoding, response extraction, and content decision parsing.

Covers:
  - try_json_loads() — safe JSON parse with None on failure
  - decode_json_payload() — extract JSON from LLM text (direct, fenced, bare)
  - extract_response_text() — extract text from Claude API response objects
  - coerce_decision() — coerce raw dict to ContentDecision with alias resolution
  - parse_content_decisions() — end-to-end: response text → list[ContentDecision]
  - PLATFORM_ALIASES — all aliases map to valid Platform values
  - CONTENT_TYPE_ALIASES — all aliases map to valid ContentType values
"""

from __future__ import annotations

from unittest.mock import MagicMock

from holus.agents.marketing.json_parsing import (
    CONTENT_TYPE_ALIASES,
    PLATFORM_ALIASES,
    coerce_decision,
    decode_json_payload,
    extract_response_text,
    parse_content_decisions,
    try_json_loads,
)
from holus.agents.marketing.models import ContentDecision, ContentType, Platform

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_text_block(text: str) -> MagicMock:
    """Build a mock Claude API text content block."""
    block = MagicMock()
    block.text = text
    return block


def _make_response(blocks: list[MagicMock]) -> MagicMock:
    """Build a mock Claude API response with the given content blocks."""
    response = MagicMock()
    response.content = blocks
    return response


def _make_decision_dict(**overrides: object) -> dict:
    """Build a minimal valid content decision dict."""
    base: dict = {
        "product": "pilaster",
        "platform": "linkedin",
        "content_type": "tutorial",
        "content_pillar": "builder_stories",
        "topic": "AI image generation",
        "hook": "I built something.",
        "framework": "original",
        "reasoning": "Educational content works well.",
        "priority": 1,
        "estimated_engagement": "medium",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tests: try_json_loads()
# ---------------------------------------------------------------------------


class TestTryJsonLoads:
    """Tests for try_json_loads — safe JSON parsing."""

    def test_valid_json_object(self) -> None:
        """Valid JSON object is parsed to a dict."""
        result = try_json_loads('{"key": "value"}')
        assert result == {"key": "value"}

    def test_valid_json_array(self) -> None:
        """Valid JSON array is parsed to a list."""
        result = try_json_loads("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_valid_json_string(self) -> None:
        """Valid JSON string literal is parsed."""
        result = try_json_loads('"hello"')
        assert result == "hello"

    def test_valid_json_number(self) -> None:
        """Valid JSON number is parsed."""
        result = try_json_loads("42")
        assert result == 42

    def test_valid_json_bool(self) -> None:
        """Valid JSON boolean is parsed."""
        result = try_json_loads("true")
        assert result is True

    def test_invalid_json_returns_none(self) -> None:
        """Invalid JSON returns None instead of raising."""
        result = try_json_loads("not json at all")
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        """Empty string is not valid JSON — returns None."""
        result = try_json_loads("")
        assert result is None

    def test_partial_json_returns_none(self) -> None:
        """Incomplete JSON object returns None."""
        result = try_json_loads('{"key": ')
        assert result is None

    def test_nested_object(self) -> None:
        """Nested JSON objects are parsed correctly."""
        result = try_json_loads('{"a": {"b": [1, 2]}}')
        assert result == {"a": {"b": [1, 2]}}


# ---------------------------------------------------------------------------
# Tests: decode_json_payload()
# ---------------------------------------------------------------------------


class TestDecodeJsonPayload:
    """Tests for decode_json_payload — JSON extraction from LLM response text."""

    def test_direct_json_object(self) -> None:
        """Plain JSON object is parsed directly."""
        result = decode_json_payload('{"key": "value"}')
        assert result == {"key": "value"}

    def test_direct_json_array(self) -> None:
        """Plain JSON array is parsed directly."""
        result = decode_json_payload("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_fenced_code_block_with_json_tag(self) -> None:
        """JSON inside ```json ... ``` fenced block is extracted."""
        text = '```json\n{"platform": "linkedin"}\n```'
        result = decode_json_payload(text)
        assert result == {"platform": "linkedin"}

    def test_fenced_code_block_without_lang_tag(self) -> None:
        """JSON inside plain ``` ... ``` fenced block is extracted."""
        text = '```\n[{"a": 1}]\n```'
        result = decode_json_payload(text)
        assert result == [{"a": 1}]

    def test_bare_object_in_mixed_text(self) -> None:
        """JSON object embedded in surrounding text is extracted."""
        text = 'Sure! Here is the decision: {"platform": "twitter"} Hope that helps!'
        result = decode_json_payload(text)
        assert result == {"platform": "twitter"}

    def test_bare_array_in_mixed_text(self) -> None:
        """Bare JSON array within mixed text is extracted."""
        text = 'LLM response: [{"platform": "twitter"}, {"platform": "linkedin"}] end.'
        result = decode_json_payload(text)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_empty_string_returns_none(self) -> None:
        """Empty string returns None."""
        result = decode_json_payload("")
        assert result is None

    def test_whitespace_only_returns_none(self) -> None:
        """Whitespace-only string returns None."""
        result = decode_json_payload("   \n\t  ")
        assert result is None

    def test_no_json_at_all_returns_none(self) -> None:
        """Plain text with no JSON returns None."""
        result = decode_json_payload("This is just some text without any JSON.")
        assert result is None

    def test_fenced_block_found_before_bare_extraction(self) -> None:
        """Fenced block JSON is found before bare object extraction."""
        text = 'Some text and ```json\n{"correct": true}\n``` done.'
        result = decode_json_payload(text)
        assert result == {"correct": True}

    def test_invalid_fenced_block_falls_through_to_bare(self) -> None:
        """Invalid fenced block falls through to bare object extraction."""
        text = '```json\nnot valid json\n```\n{"fallback": true}'
        result = decode_json_payload(text)
        assert result == {"fallback": True}

    def test_direct_parse_preferred_for_pure_json(self) -> None:
        """Entire text that is valid JSON uses direct parse path."""
        text = '{"direct": true}'
        result = decode_json_payload(text)
        assert result == {"direct": True}

    def test_no_json_in_fenced_block_returns_none(self) -> None:
        """Fenced block with invalid JSON and no bare JSON → None."""
        text = "```\nnot json\n```"
        result = decode_json_payload(text)
        assert result is None


# ---------------------------------------------------------------------------
# Tests: extract_response_text()
# ---------------------------------------------------------------------------


class TestExtractResponseText:
    """Tests for extract_response_text — Claude API response text extraction."""

    def test_single_text_block(self) -> None:
        """Extracts text from a single text block."""
        response = _make_response([_make_text_block("Hello, world!")])
        assert extract_response_text(response) == "Hello, world!"

    def test_multiple_text_blocks_joined(self) -> None:
        """Multiple text blocks are joined with newlines."""
        response = _make_response([_make_text_block("Line one."), _make_text_block("Line two.")])
        result = extract_response_text(response)
        assert "Line one." in result
        assert "Line two." in result

    def test_empty_content_list_returns_empty_string(self) -> None:
        """Empty content list returns empty string."""
        response = _make_response([])
        assert extract_response_text(response) == ""

    def test_non_string_text_attribute_skipped(self) -> None:
        """Blocks with non-string .text (e.g., None) are skipped."""
        tool_block = MagicMock()
        tool_block.text = None  # Not a string
        text_block = _make_text_block("actual text")
        response = _make_response([tool_block, text_block])
        result = extract_response_text(response)
        assert result == "actual text"

    def test_no_content_attribute_returns_empty_string(self) -> None:
        """Object with no .content attribute returns empty string."""
        response = object()  # Plain object, no .content attribute
        assert extract_response_text(response) == ""

    def test_strips_leading_trailing_whitespace(self) -> None:
        """Result is stripped of leading/trailing whitespace."""
        response = _make_response([_make_text_block("  \n text here \n  ")])
        assert extract_response_text(response) == "text here"

    def test_integer_text_attribute_skipped(self) -> None:
        """Block with integer .text is skipped — only strings are included."""
        bad_block = MagicMock()
        bad_block.text = 42  # Not a string
        response = _make_response([bad_block])
        assert extract_response_text(response) == ""


# ---------------------------------------------------------------------------
# Tests: coerce_decision()
# ---------------------------------------------------------------------------


class TestCoerceDecision:
    """Tests for coerce_decision — raw dict to ContentDecision with alias resolution."""

    def test_valid_full_dict(self) -> None:
        """Valid dict with all fields produces a ContentDecision."""
        result = coerce_decision(_make_decision_dict())
        assert isinstance(result, ContentDecision)
        assert result.product == "pilaster"
        assert result.platform == Platform.LINKEDIN

    def test_non_dict_string_returns_none(self) -> None:
        """String input returns None."""
        assert coerce_decision("string") is None

    def test_non_dict_int_returns_none(self) -> None:
        """Integer input returns None."""
        assert coerce_decision(42) is None

    def test_none_input_returns_none(self) -> None:
        """None input returns None."""
        assert coerce_decision(None) is None

    def test_non_dict_list_returns_none(self) -> None:
        """List input returns None."""
        assert coerce_decision([1, 2]) is None

    def test_missing_fields_use_defaults(self) -> None:
        """Missing optional fields use defaults defined in coerce_decision."""
        result = coerce_decision({"product": "genpeli", "topic": "Demo", "reasoning": "Good"})
        assert isinstance(result, ContentDecision)
        assert result.platform == Platform.LINKEDIN  # default
        assert result.content_type == ContentType.TUTORIAL  # default
        assert result.priority == 1  # default

    def test_empty_dict_uses_all_defaults(self) -> None:
        """Empty dict uses all defaults from coerce_decision."""
        result = coerce_decision({})
        assert isinstance(result, ContentDecision)
        assert result.product == "pilaster"
        assert result.platform == Platform.LINKEDIN
        assert result.priority == 1

    def test_platform_alias_x_maps_to_twitter(self) -> None:
        """Platform alias 'x' maps to Platform.TWITTER."""
        result = coerce_decision(_make_decision_dict(platform="x"))
        assert result is not None
        assert result.platform == Platform.TWITTER

    def test_platform_alias_yt_shorts_maps_to_youtube(self) -> None:
        """Platform alias 'yt_shorts' maps to Platform.YOUTUBE."""
        result = coerce_decision(_make_decision_dict(platform="yt_shorts"))
        assert result is not None
        assert result.platform == Platform.YOUTUBE

    def test_platform_alias_youtube_shorts_maps_to_youtube(self) -> None:
        """Platform alias 'youtube_shorts' maps to Platform.YOUTUBE."""
        result = coerce_decision(_make_decision_dict(platform="youtube_shorts"))
        assert result is not None
        assert result.platform == Platform.YOUTUBE

    def test_content_type_alias_technical_post_maps_to_educational(self) -> None:
        """Content type alias 'technical_post' maps to ContentType.EDUCATIONAL."""
        result = coerce_decision(_make_decision_dict(content_type="technical_post"))
        assert result is not None
        assert result.content_type == ContentType.EDUCATIONAL

    def test_content_type_alias_before_after_maps_to_demo(self) -> None:
        """Content type alias 'before_after' maps to ContentType.DEMO."""
        result = coerce_decision(_make_decision_dict(content_type="before_after"))
        assert result is not None
        assert result.content_type == ContentType.DEMO

    def test_invalid_priority_string_defaults_to_1(self) -> None:
        """Priority that can't be converted to int defaults to 1."""
        result = coerce_decision(_make_decision_dict(priority="not-a-number"))
        assert result is not None
        assert result.priority == 1

    def test_none_priority_defaults_to_1(self) -> None:
        """Priority of None defaults to 1."""
        result = coerce_decision(_make_decision_dict(priority=None))
        assert result is not None
        assert result.priority == 1

    def test_valid_priority_2_preserved(self) -> None:
        """Valid priority value 2 is preserved."""
        result = coerce_decision(_make_decision_dict(priority=2))
        assert result is not None
        assert result.priority == 2

    def test_invalid_estimated_engagement_returns_none(self) -> None:
        """ContentDecision with invalid estimated_engagement fails validation → None."""
        result = coerce_decision(_make_decision_dict(estimated_engagement="very_high"))
        assert result is None

    def test_platform_lookup_is_case_insensitive(self) -> None:
        """Platform value is lowercased before alias lookup."""
        result = coerce_decision(_make_decision_dict(platform="LINKEDIN"))
        assert result is not None
        assert result.platform == Platform.LINKEDIN


# ---------------------------------------------------------------------------
# Tests: parse_content_decisions()
# ---------------------------------------------------------------------------


class TestParseContentDecisions:
    """Tests for parse_content_decisions — end-to-end text → list[ContentDecision]."""

    def test_single_json_object(self) -> None:
        """Single JSON object produces one ContentDecision."""
        text = '{"product": "pilaster", "topic": "AI art", "reasoning": "Good"}'
        result = parse_content_decisions(text)
        assert len(result) == 1
        assert isinstance(result[0], ContentDecision)

    def test_json_array_of_decisions(self) -> None:
        """JSON array of dicts produces multiple ContentDecisions."""
        text = (
            '[{"product": "pilaster", "topic": "A", "reasoning": "R"},'
            ' {"product": "genpeli", "topic": "B", "reasoning": "S"}]'
        )
        result = parse_content_decisions(text)
        assert len(result) == 2
        assert result[0].product == "pilaster"
        assert result[1].product == "genpeli"

    def test_empty_string_returns_empty_list(self) -> None:
        """Empty string returns empty list."""
        assert parse_content_decisions("") == []

    def test_non_json_response_returns_empty_list(self) -> None:
        """Plain text with no JSON returns empty list."""
        assert parse_content_decisions("Sorry, I cannot help with that.") == []

    def test_whitespace_only_returns_empty_list(self) -> None:
        """Whitespace-only input returns empty list."""
        assert parse_content_decisions("   \n  ") == []

    def test_fenced_block_with_array(self) -> None:
        """JSON array inside fenced block is parsed correctly."""
        text = (
            '```json\n[{"product": "invoz", "topic": "API demo", "reasoning": "Dev audience"}]\n```'
        )
        result = parse_content_decisions(text)
        assert len(result) == 1
        assert result[0].product == "invoz"

    def test_non_dict_items_in_array_are_dropped(self) -> None:
        """Non-dict items in array (strings, ints) are filtered out."""
        text = (
            '[{"product": "pilaster", "topic": "Good", "reasoning": "Works",'
            ' "estimated_engagement": "high"}, "not a dict", 42]'
        )
        result = parse_content_decisions(text)
        assert len(result) == 1
        assert result[0].product == "pilaster"

    def test_all_returned_items_are_content_decisions(self) -> None:
        """All returned items are ContentDecision instances."""
        text = (
            '[{"product": "pilaster", "topic": "T1", "reasoning": "R1"},'
            ' {"product": "genpeli", "topic": "T2", "reasoning": "R2"}]'
        )
        result = parse_content_decisions(text)
        assert all(isinstance(d, ContentDecision) for d in result)

    def test_validation_errors_silently_dropped(self) -> None:
        """Items that fail Pydantic validation are silently dropped."""
        text = (
            '[{"product": "pilaster", "topic": "T", "reasoning": "R",'
            ' "estimated_engagement": "invalid_value"},'
            ' {"product": "genpeli", "topic": "T2", "reasoning": "R2"}]'
        )
        result = parse_content_decisions(text)
        assert len(result) == 1
        assert result[0].product == "genpeli"


# ---------------------------------------------------------------------------
# Tests: PLATFORM_ALIASES constant
# ---------------------------------------------------------------------------


class TestPlatformAliases:
    """Validate that PLATFORM_ALIASES maps all aliases to valid Platform members."""

    def test_all_values_are_platform_members(self) -> None:
        """Every value in PLATFORM_ALIASES is a valid Platform enum member."""
        valid_platforms = set(Platform)
        for alias, platform in PLATFORM_ALIASES.items():
            assert platform in valid_platforms, f"{alias!r} maps to invalid Platform: {platform!r}"

    def test_x_alias_maps_to_twitter(self) -> None:
        """'x' alias maps to Platform.TWITTER."""
        assert PLATFORM_ALIASES["x"] == Platform.TWITTER

    def test_yt_shorts_alias_maps_to_youtube(self) -> None:
        """'yt_shorts' alias maps to Platform.YOUTUBE."""
        assert PLATFORM_ALIASES["yt_shorts"] == Platform.YOUTUBE

    def test_youtube_shorts_alias_maps_to_youtube(self) -> None:
        """'youtube_shorts' alias maps to Platform.YOUTUBE."""
        assert PLATFORM_ALIASES["youtube_shorts"] == Platform.YOUTUBE

    def test_canonical_platform_names_present(self) -> None:
        """Canonical names (linkedin, twitter, etc.) are included."""
        for name in ("linkedin", "twitter", "tiktok", "instagram", "facebook", "threads"):
            assert name in PLATFORM_ALIASES, f"Missing canonical alias: {name!r}"

    def test_no_none_values(self) -> None:
        """No alias maps to None."""
        for alias, platform in PLATFORM_ALIASES.items():
            assert platform is not None, f"{alias!r} maps to None"


# ---------------------------------------------------------------------------
# Tests: CONTENT_TYPE_ALIASES constant
# ---------------------------------------------------------------------------


class TestContentTypeAliases:
    """Validate that CONTENT_TYPE_ALIASES maps all aliases to valid ContentType members."""

    def test_all_values_are_content_type_members(self) -> None:
        """Every value in CONTENT_TYPE_ALIASES is a valid ContentType enum member."""
        valid_types = set(ContentType)
        for alias, ctype in CONTENT_TYPE_ALIASES.items():
            assert ctype in valid_types, f"{alias!r} maps to invalid ContentType: {ctype!r}"

    def test_technical_post_maps_to_educational(self) -> None:
        """'technical_post' alias maps to ContentType.EDUCATIONAL."""
        assert CONTENT_TYPE_ALIASES["technical_post"] == ContentType.EDUCATIONAL

    def test_before_after_maps_to_demo(self) -> None:
        """'before_after' alias maps to ContentType.DEMO."""
        assert CONTENT_TYPE_ALIASES["before_after"] == ContentType.DEMO

    def test_canonical_content_type_names_present(self) -> None:
        """Canonical content type names are included as aliases."""
        canonical = (
            "tutorial",
            "demo",
            "tips",
            "thread",
            "case_study",
            "carousel",
            "video_reel",
            "announcement",
            "educational",
        )
        for name in canonical:
            assert name in CONTENT_TYPE_ALIASES, f"Missing canonical alias: {name!r}"

    def test_no_none_values(self) -> None:
        """No alias maps to None."""
        for alias, ctype in CONTENT_TYPE_ALIASES.items():
            assert ctype is not None, f"{alias!r} maps to None"
