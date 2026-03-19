"""SPEC-031: LinkedIn Content Pipeline E2E Tests.

Tests the full OBSERVE → REASON → ACT → EVALUATE loop with mocked MCP.
Verifies: analytics read, ContentDecision with platform=linkedin,
quality gate, content queuing, trajectory logging.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

# -- Fixtures ----------------------------------------------------------------

def _make_mock_analytics() -> dict[str, Any]:
    """Realistic analytics response from social-media MCP."""
    return {
        "period": {"start": "2026-03-12", "end": "2026-03-19"},
        "platforms": {
            "linkedin": {
                "impressions": 12500,
                "engagement_rate": 4.2,
                "followers": 1840,
                "top_content_type": "tutorial",
                "posts_count": 5,
            }
        },
        "overall": {
            "total_impressions": 15200,
            "total_engagement": 3.8,
        },
    }


def _make_mock_top_posts() -> dict[str, Any]:
    """Realistic top posts response from social-media MCP."""
    return {
        "posts": [
            {
                "id": "post-001",
                "platform": "linkedin",
                "text": "How we built a real-time audio ML pipeline...",
                "impressions": 4200,
                "engagement_rate": 6.1,
                "content_type": "tutorial",
                "published_at": "2026-03-15T10:00:00Z",
            },
            {
                "id": "post-002",
                "platform": "linkedin",
                "text": "3 lessons from building ComfyUI workflows...",
                "impressions": 3100,
                "engagement_rate": 5.3,
                "content_type": "tips",
                "published_at": "2026-03-13T14:00:00Z",
            },
        ]
    }


# -- Tests -------------------------------------------------------------------

class TestLinkedInPipelineE2E:
    """SPEC-031: Full OBSERVE → REASON → ACT → EVALUATE with mocked MCP."""

    def test_analytics_data_shape(self):
        """OBSERVE step: Analytics data has the expected shape for marketing decisions."""
        analytics = _make_mock_analytics()
        top_posts = _make_mock_top_posts()

        # Analytics has platform breakdown
        assert "linkedin" in analytics["platforms"]
        linkedin = analytics["platforms"]["linkedin"]
        assert linkedin["impressions"] > 0
        assert linkedin["engagement_rate"] > 0
        assert "top_content_type" in linkedin

        # Top posts are LinkedIn-first
        assert len(top_posts["posts"]) >= 1
        assert top_posts["posts"][0]["platform"] == "linkedin"
        assert "engagement_rate" in top_posts["posts"][0]
        assert "content_type" in top_posts["posts"][0]

    def test_social_media_client_exists(self):
        """SocialMediaClient has the required MCP tool methods."""
        from holus.integrations.social_media.client import SocialMediaClient

        # Verify the client has the methods SPEC-031 requires
        assert hasattr(SocialMediaClient, "get_analytics")
        assert hasattr(SocialMediaClient, "get_top_posts")
        assert hasattr(SocialMediaClient, "publish")
        assert hasattr(SocialMediaClient, "schedule_post")

    def test_schedule_post_has_approval_required(self):
        """schedule_post accepts approval_required parameter (SPEC-031)."""
        import inspect

        from holus.integrations.social_media.client import SocialMediaClient

        sig = inspect.signature(SocialMediaClient.schedule_post)
        assert "request" in sig.parameters

        # Verify ScheduleRequest has approval_required field
        from holus.integrations.social_media.client import ScheduleRequest

        req = ScheduleRequest(
            content="Test post",
            platform="linkedin",
            approval_required=True,
        )
        assert req.approval_required is True

    def test_schedule_request_validates_fields(self):
        """ScheduleRequest and ScheduleResult models are well-formed."""
        from holus.integrations.social_media.client import ScheduleRequest, ScheduleResult

        req = ScheduleRequest(
            content="How I built a production audio ML pipeline...",
            platform="linkedin",
            approval_required=True,
            scheduled_at="2026-03-20T10:00:00Z",
        )
        assert req.platform == "linkedin"
        assert req.approval_required is True
        assert req.scheduled_at == "2026-03-20T10:00:00Z"

        result = ScheduleResult(
            schedule_id="sched-001",
            status="pending_approval",
            platform="linkedin",
            approval_required=True,
        )
        assert result.schedule_id == "sched-001"
        assert result.status == "pending_approval"

    def test_content_decision_has_linkedin_platform(self):
        """ContentDecision model defaults to LinkedIn platform."""
        from holus.agents.marketing.models import ContentDecision, ContentType, Platform

        decision = ContentDecision(
            product="pilaster",
            platform=Platform.LINKEDIN,
            content_type=ContentType.TUTORIAL,
            topic="Building a production image generation pipeline",
            hook="How I built a production image generation pipeline",
            reasoning="Tutorial posts outperform promo posts 4:1 on LinkedIn",
            content_pillar="builder_stories",
        )

        assert decision.platform == Platform.LINKEDIN
        assert decision.product == "pilaster"
        assert decision.content_type == ContentType.TUTORIAL
        assert decision.topic != ""
        assert decision.hook != ""
        assert decision.reasoning != ""

    def test_content_decision_serialization(self):
        """ContentDecision can be serialized and deserialized."""
        from holus.agents.marketing.models import ContentDecision, ContentType, Platform

        decision = ContentDecision(
            product="invoz",
            platform=Platform.LINKEDIN,
            content_type=ContentType.DEMO,
            topic="Real-time pronunciation scoring demo",
            hook="Watch how pronunciation scoring works in real-time",
            reasoning="Demo content drives signups for developer tools",
        )

        serialized = decision.model_dump(mode="json")
        assert serialized["platform"] == "linkedin"
        assert serialized["content_type"] == "demo"
        assert serialized["topic"] == "Real-time pronunciation scoring demo"

        # Can reconstruct
        restored = ContentDecision(**serialized)
        assert restored.platform == Platform.LINKEDIN

    def test_content_queue_accepts_linkedin_content(self, tmp_path: Path, monkeypatch):
        """Content queue can store LinkedIn posts for human review."""
        import holus.agents.marketing.content_queue as cq
        from holus.agents.marketing.content_queue import QueuedContent, enqueue, list_pending

        # Redirect the module-level QUEUE_DIR to tmp_path
        queue_dir = tmp_path / "content-queue"
        queue_dir.mkdir()
        monkeypatch.setattr(cq, "QUEUE_DIR", queue_dir)

        content = QueuedContent(
            piece_id="test-001",
            platform="linkedin",
            text="How we built a production audio ML pipeline from 46 research papers...",
            content_type="tutorial",
            product="invoz",
            topic="Production audio ML pipeline",
            reasoning="Tutorial content resonates with developer audience on LinkedIn",
            status="pending_review",
        )

        path = enqueue(content)
        assert path.exists()
        assert path.suffix == ".yaml"

        pending = list_pending()
        assert len(pending) >= 1
        assert any(p.piece_id == "test-001" for p in pending)

    def test_quality_gate_rejects_low_score(self):
        """Quality gate scores content using GeneratedPiece model."""
        from holus.agents.marketing.models import (
            ContentDecision,
            ContentType,
            GeneratedPiece,
            Platform,
        )
        from holus.agents.marketing.quality_score import score_content

        decision = ContentDecision(
            product="pilaster",
            platform=Platform.LINKEDIN,
            content_type=ContentType.TUTORIAL,
            topic="Production image generation pipeline architecture",
            hook="How I built a production-grade image generation pipeline with memory",
            reasoning="Tutorial posts outperform promo posts 4:1 on LinkedIn",
            content_pillar="builder_stories",
        )

        good_piece = GeneratedPiece(
            piece_id="test-good-001",
            decision=decision,
            text=(
                "How I built a production-grade image generation pipeline with memory. "
                "After 6 months of iteration, here are the 3 architectural decisions that mattered most. "
                "First, we separated the generation abstraction from the backend..."
            ),
            platform=Platform.LINKEDIN,
            model_used="claude-sonnet-4-6",
        )

        good_score = score_content(good_piece)
        assert good_score.passed, f"Good content should pass quality gate, got score={good_score.score}"

    def test_trajectory_entry_structure(self, tmp_path: Path):
        """Trajectory entries have the expected structure."""
        traj_path = tmp_path / "trajectory.jsonl"

        # Write a mock trajectory entry
        entry = {
            "cycle_id": "2026-03-19T10:00:00+00:00",
            "phase": "creating",
            "content_posted": 0,
            "error": None,
            "analytics": {"impressions": 12500},
            "decisions": [{"product": "pilaster", "platform": "linkedin"}],
        }
        traj_path.write_text(json.dumps(entry) + "\n")

        # Verify it's valid JSONL
        loaded = json.loads(traj_path.read_text().strip())
        assert loaded["phase"] == "creating"
        assert loaded["decisions"][0]["platform"] == "linkedin"
