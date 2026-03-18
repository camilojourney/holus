"""Tests for content deduplication via TopicIndex."""

import json
from datetime import UTC, datetime

import pytest

from holus.agents.marketing.topic_index import TopicIndex


@pytest.fixture
def queue_dir(tmp_path):
    """Create a temp content-queue with sample items."""
    now = datetime.now(UTC).isoformat()
    items = [
        {"topic": "MCP vs SKILLS — Two Paradigms for AI Agents", "content_type": "text_post", "platform": "linkedin", "generated_at": now, "status": "published"},
        {"topic": "Why AI Agents Fail After Week One", "content_type": "carousel_outline", "platform": "linkedin", "generated_at": now, "status": "pending_review"},
        {"topic": "Building a Self-Improving Content Engine", "content_type": "text_post", "platform": "twitter_x", "generated_at": now, "status": "published"},
    ]
    for i, item in enumerate(items):
        path = tmp_path / f"linkedin-test-{i}.json"
        path.write_text(json.dumps(item))
    return tmp_path


class TestRecentTopics:
    def test_returns_all_topics(self, queue_dir):
        index = TopicIndex(queue_dir=queue_dir)
        topics = index.recent_topics(days=30)
        assert len(topics) == 3

    def test_topic_strings(self, queue_dir):
        index = TopicIndex(queue_dir=queue_dir)
        strings = index.recent_topic_strings(days=30)
        assert "MCP vs SKILLS — Two Paradigms for AI Agents" in strings

    def test_empty_dir(self, tmp_path):
        index = TopicIndex(queue_dir=tmp_path)
        assert index.recent_topics(days=30) == []

    def test_nonexistent_dir(self, tmp_path):
        index = TopicIndex(queue_dir=tmp_path / "nonexistent")
        assert index.recent_topics(days=30) == []


class TestIsDuplicate:
    def test_exact_match(self, queue_dir):
        index = TopicIndex(queue_dir=queue_dir)
        assert index.is_duplicate("MCP vs SKILLS — Two Paradigms for AI Agents")

    def test_similar_topic(self, queue_dir):
        index = TopicIndex(queue_dir=queue_dir)
        assert index.is_duplicate("Why AI Agents Fail After Week 1", threshold=0.5)

    def test_different_topic(self, queue_dir):
        index = TopicIndex(queue_dir=queue_dir)
        assert not index.is_duplicate("How to Deploy PostgreSQL on Railway")

    def test_short_topic_not_duplicate(self, queue_dir):
        index = TopicIndex(queue_dir=queue_dir)
        assert not index.is_duplicate("AI")


class TestPromptContext:
    def test_generates_context(self, queue_dir):
        index = TopicIndex(queue_dir=queue_dir)
        ctx = index.as_prompt_context(days=30)
        assert "RECENTLY PUBLISHED" in ctx
        assert "MCP vs SKILLS" in ctx
        assert "DIFFERENT angle" in ctx

    def test_empty_returns_empty(self, tmp_path):
        index = TopicIndex(queue_dir=tmp_path)
        assert index.as_prompt_context(days=30) == ""
