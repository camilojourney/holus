"""Tests for idea_runner platform-aware format instructions."""

from holus.agents.marketing.idea_runner import FORMAT_INSTRUCTIONS, _get_format_instructions


class TestGetFormatInstructions:
    def test_linkedin_video_script_unchanged(self):
        result = _get_format_instructions("video_script", "linkedin")
        base = FORMAT_INSTRUCTIONS["video_script"]
        assert result == base  # No enrichment for LinkedIn

    def test_instagram_video_script_has_caption_and_hashtags(self):
        result = _get_format_instructions("video_script", "instagram")
        assert "CAPTION" in result
        assert "HASHTAGS" in result
        assert "Instagram" in result

    def test_tiktok_video_script_has_enrichment(self):
        result = _get_format_instructions("video_script", "tiktok")
        assert "HASHTAGS" in result
        assert "TikTok" in result

    def test_text_post_not_enriched(self):
        result = _get_format_instructions("text_post", "instagram")
        base = FORMAT_INSTRUCTIONS["text_post"]
        assert result == base  # text_post already handles hashtags

    def test_unknown_format_falls_back_to_text_post(self):
        result = _get_format_instructions("unknown_format", "linkedin")
        assert result == FORMAT_INSTRUCTIONS["text_post"]
