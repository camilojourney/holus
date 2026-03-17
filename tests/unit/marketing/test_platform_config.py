"""Tests for platform-specific configuration."""

from holus.agents.marketing.platform_config import (
    get_judge_rubric,
    get_platform_config,
    get_reward_weights,
    list_platforms,
)


class TestPlatformConfig:
    def test_linkedin(self):
        config = get_platform_config("linkedin")
        assert config.char_limit == 3000
        assert "comments" in config.reward_weights
        assert config.hashtag_limit == 3

    def test_twitter(self):
        config = get_platform_config("twitter")
        assert config.char_limit == 280
        assert "retweets" in config.reward_weights

    def test_twitter_x_alias(self):
        config = get_platform_config("twitter_x")
        assert config.char_limit == 280

    def test_instagram(self):
        config = get_platform_config("instagram")
        assert "saves" in config.reward_weights
        assert config.hashtag_limit == 15

    def test_tiktok(self):
        config = get_platform_config("tiktok")
        assert "watch_time" in config.reward_weights
        assert "video_script" in config.supported_formats

    def test_unknown_falls_back_to_linkedin(self):
        config = get_platform_config("nonexistent")
        assert config.platform_id == "linkedin"

    def test_list_platforms(self):
        platforms = list_platforms()
        assert "linkedin" in platforms
        assert "instagram" in platforms
        assert len(platforms) >= 6

    def test_judge_rubric_per_platform(self):
        linkedin_rubric = get_judge_rubric("linkedin")
        twitter_rubric = get_judge_rubric("twitter")
        assert "authority_signal" in linkedin_rubric
        assert "ratio_potential" in twitter_rubric
        assert linkedin_rubric != twitter_rubric

    def test_reward_weights_sum_to_one(self):
        for platform in list_platforms():
            weights = get_reward_weights(platform)
            total = sum(weights.values())
            assert abs(total - 1.0) < 0.01, f"{platform} weights sum to {total}"

    def test_all_platforms_have_rubric(self):
        for platform in list_platforms():
            rubric = get_judge_rubric(platform)
            assert len(rubric) > 50, f"{platform} rubric too short"
