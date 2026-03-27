"""Tests for content_generator.py — the core generation module.

Covers:
  - generate_piece: text_post, thread, carousel, video_script, instagram_caption
  - JSON parse failure fallback
  - Personal context injection
  - Few-shot context loading
  - Constitutional AI revision loop integration
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

from holus.agents.marketing.content_generator import (
    GENERATOR_SYSTEM,
    generate_piece,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_TEXT_POST_JSON = json.dumps(
    {
        "text": "Most agent architectures are just API wrappers.\n\nI spent 3 months building a real one.",
        "headline": "Agent architecture hot take",
        "hashtags": ["#AI", "#Agents"],
        "hook_score": "8",
        "voice_check": "PASS",
    }
)

VALID_THREAD_JSON = json.dumps(
    {
        "text": "Tweet 1: Most agent architectures...\n---\nTweet 2: Here's why...",
        "headline": "Agent thread",
        "hashtags": ["#AI"],
        "hook_score": "7",
        "voice_check": "PASS",
    }
)

VALID_CAROUSEL_JSON = json.dumps(
    {
        "slides": [
            {
                "type": "hook",
                "variables": {
                    "headline": "Stop building wrappers",
                    "subheadline": "Here's the real way.",
                },
            },
            {
                "type": "body",
                "variables": {
                    "title": "Step one",
                    "body": "Do the thing.",
                    "bullet_points": ["a", "b", "c"],
                },
            },
            {"type": "cta", "variables": {"headline": "What agent pattern are you using?"}},
        ],
        "design": {
            "theme": "dark",
            "font_pairing": "tech",
            "gradient": "dark_navy",
            "effect": "none",
        },
        "caption": "Swipe to learn agent architecture. Swipe ->",
        "hook_score": "9",
        "voice_check": "PASS",
    }
)

VALID_VIDEO_SCRIPT_JSON = json.dumps(
    {
        "text": "HOOK: Most people build agents wrong.\nSETUP: Let me show you why.\nBODY: ...\nCTA: Drop a comment.",
        "headline": "Video script: agents",
        "hashtags": ["#AI"],
        "hook_score": "8",
        "voice_check": "PASS",
    }
)

VALID_IG_CAPTION_JSON = json.dumps(
    {
        "text": "Building AI agents is harder than it looks.\n\nHere's what 3 months taught me.\n\n#AI #Agents #BuildInPublic",
        "headline": "IG caption: agents",
        "hashtags": ["#AI", "#Agents", "#BuildInPublic"],
        "hook_score": "7",
        "voice_check": "PASS",
    }
)


def _base_decision(**overrides: Any) -> dict[str, Any]:
    base = {
        "format": "text_post",
        "platform": "linkedin",
        "angle": "Agent architecture vs API wrappers",
        "product": "pilaster",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. test_generate_piece_text_post
# ---------------------------------------------------------------------------


@patch("holus.agents.marketing.revision_loop.requests.post")
@patch("holus.agents.marketing.content_generator._load_personal_context", return_value="")
@patch("holus.agents.marketing.content_generator._load_few_shot_context", return_value="")
@patch(
    "holus.agents.marketing.content_generator._load_prompt",
    return_value=(GENERATOR_SYSTEM, "layer3:fallback"),
)
@patch("holus.agents.marketing.content_generator._call")
def test_generate_piece_text_post(
    mock_call: MagicMock,
    mock_prompt: MagicMock,
    mock_few: MagicMock,
    mock_personal: MagicMock,
    mock_rev_post: MagicMock,
) -> None:
    """Text post: LLM returns valid JSON, fields are extracted correctly."""
    mock_call.return_value = VALID_TEXT_POST_JSON
    rev_resp = MagicMock()
    rev_resp.status_code = 200
    rev_resp.json.return_value = {"choices": [{"message": {"content": "PASS"}}]}
    mock_rev_post.return_value = rev_resp

    result = generate_piece("Raw idea about agents", _base_decision())

    assert result["headline"] == "Agent architecture hot take"
    assert "API wrappers" in result["text"]
    assert result["hashtags"] == ["#AI", "#Agents"]
    assert result["hook_score"] == "8"
    assert result["voice_check"] == "PASS"

    # Verify LLM was called with correct model and temperature
    mock_call.assert_called_once()
    args = mock_call.call_args
    assert args[0][0] == "anthropic/claude-sonnet-4-6"
    assert args[1]["temperature"] == 0.4 or args[0][3] == 0.4


# ---------------------------------------------------------------------------
# 2. test_generate_piece_thread
# ---------------------------------------------------------------------------


@patch("holus.agents.marketing.revision_loop.requests.post")
@patch("holus.agents.marketing.content_generator._load_personal_context", return_value="")
@patch("holus.agents.marketing.content_generator._load_few_shot_context", return_value="")
@patch(
    "holus.agents.marketing.content_generator._load_prompt",
    return_value=(GENERATOR_SYSTEM, "layer3:fallback"),
)
@patch("holus.agents.marketing.content_generator._call")
def test_generate_piece_thread(
    mock_call: MagicMock,
    mock_prompt: MagicMock,
    mock_few: MagicMock,
    mock_personal: MagicMock,
    mock_rev_post: MagicMock,
) -> None:
    """Thread format: user message includes thread-specific format instructions."""
    mock_call.return_value = VALID_THREAD_JSON
    rev_resp = MagicMock()
    rev_resp.status_code = 200
    rev_resp.json.return_value = {"choices": [{"message": {"content": "PASS — all good."}}]}
    mock_rev_post.return_value = rev_resp

    decision = _base_decision(format="thread", platform="twitter")
    result = generate_piece("Thread idea", decision)

    # Result should parse correctly
    assert "Tweet 1" in result["text"]
    assert result["headline"] == "Agent thread"

    # The user message should contain thread format instructions
    user_msg = mock_call.call_args[0][2]
    assert "thread" in user_msg.lower()
    assert "280 chars" in user_msg or "Twitter" in user_msg


# ---------------------------------------------------------------------------
# 3. test_generate_piece_carousel
# ---------------------------------------------------------------------------


@patch("holus.agents.marketing.content_generator._load_personal_context", return_value="")
@patch("holus.agents.marketing.content_generator._load_few_shot_context", return_value="")
@patch(
    "holus.agents.marketing.content_generator._load_prompt",
    return_value=(GENERATOR_SYSTEM, "layer3:fallback"),
)
@patch("holus.agents.marketing.content_generator._call")
def test_generate_piece_carousel(
    mock_call: MagicMock, mock_prompt: MagicMock, mock_few: MagicMock, mock_personal: MagicMock
) -> None:
    """Carousel: LLM returns slide-based JSON, parsed correctly."""
    mock_call.return_value = VALID_CAROUSEL_JSON

    decision = _base_decision(format="carousel_outline")
    result = generate_piece("Carousel idea", decision)

    assert "slides" in result
    assert len(result["slides"]) == 3
    assert result["slides"][0]["type"] == "hook"
    assert result["design"]["theme"] == "dark"

    # User message should include carousel instructions
    user_msg = mock_call.call_args[0][2]
    assert "carousel" in user_msg.lower()
    assert "1080x1350" in user_msg


# ---------------------------------------------------------------------------
# 4. test_generate_piece_video_script
# ---------------------------------------------------------------------------


@patch("holus.agents.marketing.content_generator._load_personal_context", return_value="")
@patch("holus.agents.marketing.content_generator._load_few_shot_context", return_value="")
@patch(
    "holus.agents.marketing.content_generator._load_prompt",
    return_value=(GENERATOR_SYSTEM, "layer3:fallback"),
)
@patch("holus.agents.marketing.content_generator._call")
def test_generate_piece_video_script(
    mock_call: MagicMock, mock_prompt: MagicMock, mock_few: MagicMock, mock_personal: MagicMock
) -> None:
    """Video script: format instructions include spoken word sections."""
    mock_call.return_value = VALID_VIDEO_SCRIPT_JSON

    decision = _base_decision(format="video_script")
    result = generate_piece("Video idea", decision)

    assert "HOOK" in result["text"]
    assert result["headline"] == "Video script: agents"

    # User message should include video script instructions
    user_msg = mock_call.call_args[0][2]
    assert "video_script" in user_msg or "Video script" in user_msg
    assert "60-90 seconds" in user_msg


# ---------------------------------------------------------------------------
# 5. test_generate_piece_instagram_caption
# ---------------------------------------------------------------------------


@patch("holus.agents.marketing.revision_loop.requests.post")
@patch("holus.agents.marketing.content_generator._load_personal_context", return_value="")
@patch("holus.agents.marketing.content_generator._load_few_shot_context", return_value="")
@patch(
    "holus.agents.marketing.content_generator._load_prompt",
    return_value=(GENERATOR_SYSTEM, "layer3:fallback"),
)
@patch("holus.agents.marketing.content_generator._call")
def test_generate_piece_instagram_caption(
    mock_call: MagicMock,
    mock_prompt: MagicMock,
    mock_few: MagicMock,
    mock_personal: MagicMock,
    mock_rev_post: MagicMock,
) -> None:
    """Instagram caption: IG-specific constraints (800-1500 chars, hashtag block)."""
    mock_call.return_value = VALID_IG_CAPTION_JSON
    rev_resp = MagicMock()
    rev_resp.status_code = 200
    rev_resp.json.return_value = {"choices": [{"message": {"content": "PASS"}}]}
    mock_rev_post.return_value = rev_resp

    decision = _base_decision(format="instagram_caption", platform="instagram")
    result = generate_piece("IG idea", decision)

    assert "#AI" in result["text"] or "#AI" in result["hashtags"]
    assert result["headline"] == "IG caption: agents"

    # User message should include IG-specific format instructions
    user_msg = mock_call.call_args[0][2]
    assert "Instagram" in user_msg or "instagram_caption" in user_msg
    assert "800-1500" in user_msg


# ---------------------------------------------------------------------------
# 6. test_generate_piece_json_parse_failure
# ---------------------------------------------------------------------------


@patch("holus.agents.marketing.revision_loop.requests.post")
@patch("holus.agents.marketing.content_generator._load_personal_context", return_value="")
@patch("holus.agents.marketing.content_generator._load_few_shot_context", return_value="")
@patch(
    "holus.agents.marketing.content_generator._load_prompt",
    return_value=(GENERATOR_SYSTEM, "layer3:fallback"),
)
@patch("holus.agents.marketing.content_generator._call")
def test_generate_piece_json_parse_failure(
    mock_call: MagicMock,
    mock_prompt: MagicMock,
    mock_few: MagicMock,
    mock_personal: MagicMock,
    mock_rev_post: MagicMock,
) -> None:
    """When LLM returns non-JSON, fallback dict is constructed."""
    mock_call.return_value = "This is not JSON at all. Just raw text from the LLM."
    # Mock revision loop LLM call to return PASS (skip revision)
    rev_resp = MagicMock()
    rev_resp.status_code = 200
    rev_resp.json.return_value = {"choices": [{"message": {"content": "PASS — all good."}}]}
    mock_rev_post.return_value = rev_resp

    result = generate_piece("Some raw idea about things", _base_decision())

    # Fallback should use raw text as "text" field
    assert result["text"] == "This is not JSON at all. Just raw text from the LLM."
    # Headline truncated from raw idea
    assert result["headline"] == "Some raw idea about things"[:60]
    assert result["hashtags"] == []
    assert result["hook_score"] == "?"
    assert result["voice_check"] == "?"


# ---------------------------------------------------------------------------
# 7. test_personal_context_injection
# ---------------------------------------------------------------------------


@patch("holus.agents.marketing.revision_loop.requests.post")
@patch(
    "holus.agents.marketing.content_generator._load_prompt",
    return_value=(GENERATOR_SYSTEM, "layer3:fallback"),
)
@patch("holus.agents.marketing.content_generator._call")
def test_personal_context_injection(
    mock_call: MagicMock, mock_prompt: MagicMock, mock_rev_post: MagicMock
) -> None:
    """Personal context is loaded and injected into the user message."""
    personal_block = "<personal_context>\nI once debugged an agent loop for 8 hours straight.\n</personal_context>"
    rev_resp = MagicMock()
    rev_resp.status_code = 200
    rev_resp.json.return_value = {"choices": [{"message": {"content": "PASS"}}]}
    mock_rev_post.return_value = rev_resp

    with (
        patch(
            "holus.agents.marketing.content_generator._load_personal_context",
            return_value=personal_block,
        ) as mock_personal,
        patch(
            "holus.agents.marketing.content_generator._load_few_shot_context",
            return_value="",
        ),
    ):
        mock_call.return_value = VALID_TEXT_POST_JSON
        generate_piece("Idea about debugging", _base_decision(product="holus"))

    # Personal context should appear in the user message sent to LLM
    user_msg = mock_call.call_args[0][2]
    assert "debugged an agent loop" in user_msg

    # _load_personal_context was called with the product
    mock_personal.assert_called_once_with("holus")


# ---------------------------------------------------------------------------
# 8. test_few_shot_context_loading
# ---------------------------------------------------------------------------


@patch("holus.agents.marketing.revision_loop.requests.post")
@patch(
    "holus.agents.marketing.content_generator._load_prompt",
    return_value=(GENERATOR_SYSTEM, "layer3:fallback"),
)
@patch("holus.agents.marketing.content_generator._load_personal_context", return_value="")
@patch("holus.agents.marketing.content_generator._call")
def test_few_shot_context_loading(
    mock_call: MagicMock, mock_personal: MagicMock, mock_prompt: MagicMock, mock_rev_post: MagicMock
) -> None:
    """Few-shot examples are loaded and injected into the user message."""
    few_shot_block = (
        "## Top-Performing Examples\n### Example 1 (5,000 engagement)\nGreat example post text\n"
    )
    rev_resp = MagicMock()
    rev_resp.status_code = 200
    rev_resp.json.return_value = {"choices": [{"message": {"content": "PASS"}}]}
    mock_rev_post.return_value = rev_resp

    with patch(
        "holus.agents.marketing.content_generator._load_few_shot_context",
        return_value=few_shot_block,
    ) as mock_few:
        mock_call.return_value = VALID_TEXT_POST_JSON
        generate_piece("Idea about few-shots", _base_decision(format="text_post"))

    # Few-shot block should appear in the user message
    user_msg = mock_call.call_args[0][2]
    assert "Top-Performing Examples" in user_msg
    assert "Great example post text" in user_msg

    # _load_few_shot_context was called with the format
    mock_few.assert_called_once_with("text_post")


# ---------------------------------------------------------------------------
# 9. test_revision_loop_integration
# ---------------------------------------------------------------------------


@patch("holus.agents.marketing.content_generator._load_personal_context", return_value="")
@patch("holus.agents.marketing.content_generator._load_few_shot_context", return_value="")
@patch(
    "holus.agents.marketing.content_generator._load_prompt",
    return_value=(GENERATOR_SYSTEM, "layer3:fallback"),
)
@patch("holus.agents.marketing.content_generator._call")
@patch("holus.agents.marketing.revision_loop.requests.post")
def test_revision_loop_integration(
    mock_rev_post: MagicMock,
    mock_call: MagicMock,
    mock_prompt: MagicMock,
    mock_few: MagicMock,
    mock_personal: MagicMock,
) -> None:
    """Constitutional AI revision runs for text_post and modifies the text."""
    original_text = "Most agent architectures are just API wrappers."
    revised_text = "Most agent architectures are glorified API wrappers. Here's proof."

    original_json = json.dumps(
        {
            "text": original_text,
            "headline": "Agent hot take",
            "hashtags": ["#AI"],
            "hook_score": "7",
            "voice_check": "PASS",
        }
    )
    mock_call.return_value = original_json

    # Mock revision loop LLM calls: first critique, then revise
    critique_resp = MagicMock()
    critique_resp.status_code = 200
    critique_resp.json.return_value = {
        "choices": [{"message": {"content": "VIOLATION: Hook is too generic."}}]
    }
    revise_resp = MagicMock()
    revise_resp.status_code = 200
    revise_resp.json.return_value = {"choices": [{"message": {"content": revised_text}}]}
    mock_rev_post.side_effect = [critique_resp, revise_resp]

    result = generate_piece("Agent idea", _base_decision(format="text_post"))

    # Text should be the revised version
    assert result["text"] == revised_text
    assert result.get("revised") is True


# ---------------------------------------------------------------------------
# 10. test_revision_loop_skipped_for_carousel
# ---------------------------------------------------------------------------


@patch("holus.agents.marketing.content_generator._load_personal_context", return_value="")
@patch("holus.agents.marketing.content_generator._load_few_shot_context", return_value="")
@patch(
    "holus.agents.marketing.content_generator._load_prompt",
    return_value=(GENERATOR_SYSTEM, "layer3:fallback"),
)
@patch("holus.agents.marketing.content_generator._call")
@patch("holus.agents.marketing.revision_loop.requests.post")
def test_revision_loop_skipped_for_carousel(
    mock_rev_post: MagicMock,
    mock_call: MagicMock,
    mock_prompt: MagicMock,
    mock_few: MagicMock,
    mock_personal: MagicMock,
) -> None:
    """Revision loop should NOT run for carousel format (only text_post, thread, instagram_caption)."""
    mock_call.return_value = VALID_CAROUSEL_JSON

    generate_piece("Carousel idea", _base_decision(format="carousel_outline"))

    # Revision loop should not make any LLM calls for carousel
    mock_rev_post.assert_not_called()


# ---------------------------------------------------------------------------
# 11. test_revision_loop_pass_skips_revision
# ---------------------------------------------------------------------------


@patch("holus.agents.marketing.content_generator._load_personal_context", return_value="")
@patch("holus.agents.marketing.content_generator._load_few_shot_context", return_value="")
@patch(
    "holus.agents.marketing.content_generator._load_prompt",
    return_value=(GENERATOR_SYSTEM, "layer3:fallback"),
)
@patch("holus.agents.marketing.content_generator._call")
@patch("holus.agents.marketing.revision_loop.requests.post")
def test_revision_loop_pass_skips_revision(
    mock_rev_post: MagicMock,
    mock_call: MagicMock,
    mock_prompt: MagicMock,
    mock_few: MagicMock,
    mock_personal: MagicMock,
) -> None:
    """When critique starts with PASS, revision is skipped."""
    mock_call.return_value = VALID_TEXT_POST_JSON

    # Critique returns PASS — no revision needed
    critique_resp = MagicMock()
    critique_resp.status_code = 200
    critique_resp.json.return_value = {
        "choices": [{"message": {"content": "PASS — all rules satisfied."}}]
    }
    mock_rev_post.return_value = critique_resp

    result = generate_piece("Good idea", _base_decision(format="text_post"))

    # Text should remain unchanged (no revision applied)
    assert "revised" not in result
    # Only one LLM call (critique), no revise call
    assert mock_rev_post.call_count == 1
