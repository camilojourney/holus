"""Tests for holus.agents.marketing.models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from holus.agents.marketing.models import (
    BrandIdentity,
    BrandPositioning,
    BrandVoice,
    ContentDecision,
    ContentPillar,
    ContentType,
    GeneratedPiece,
    MarketingCycleReport,
    Platform,
)

# ---------------------------------------------------------------------------
# Platform Enum Tests
# ---------------------------------------------------------------------------


def test_platform_enum_values() -> None:
    """Platform enum contains expected social media platforms."""
    assert Platform.LINKEDIN.value == "linkedin"
    assert Platform.TWITTER.value == "twitter"
    assert Platform.TIKTOK.value == "tiktok"
    assert Platform.INSTAGRAM.value == "instagram"
    assert Platform.FACEBOOK.value == "facebook"
    assert Platform.THREADS.value == "threads"
    assert Platform.YOUTUBE.value == "youtube"


def test_platform_from_string() -> None:
    """Platform enum can be created from string values."""
    assert Platform("linkedin") == Platform.LINKEDIN
    assert Platform("twitter") == Platform.TWITTER


# ---------------------------------------------------------------------------
# ContentType Enum Tests
# ---------------------------------------------------------------------------


def test_content_type_enum_values() -> None:
    """ContentType enum contains expected content formats."""
    assert ContentType.TUTORIAL.value == "tutorial"
    assert ContentType.DEMO.value == "demo"
    assert ContentType.TIPS.value == "tips"
    assert ContentType.THREAD.value == "thread"
    assert ContentType.CASE_STUDY.value == "case_study"
    assert ContentType.CAROUSEL.value == "carousel"
    assert ContentType.VIDEO_REEL.value == "video_reel"
    assert ContentType.ANNOUNCEMENT.value == "announcement"
    assert ContentType.EDUCATIONAL.value == "educational"


def test_content_type_from_string() -> None:
    """ContentType enum can be created from string values."""
    assert ContentType("tutorial") == ContentType.TUTORIAL
    assert ContentType("carousel") == ContentType.CAROUSEL


# ---------------------------------------------------------------------------
# ContentDecision Tests
# ---------------------------------------------------------------------------


def test_content_decision_valid() -> None:
    """ContentDecision validates with all required fields."""
    decision = ContentDecision(
        product="pilaster",
        platform=Platform.LINKEDIN,
        content_type=ContentType.TUTORIAL,
        topic="How to generate AI images with Pilaster",
        reasoning="LinkedIn audience is interested in AI tools, tutorials perform well",
    )

    assert decision.product == "pilaster"
    assert decision.platform == Platform.LINKEDIN
    assert decision.content_type == ContentType.TUTORIAL
    assert decision.priority == 1  # default
    assert decision.estimated_engagement == "medium"  # default


def test_content_decision_with_custom_priority() -> None:
    """ContentDecision accepts custom priority values."""
    decision = ContentDecision(
        product="genpeli",
        platform=Platform.TIKTOK,
        content_type=ContentType.VIDEO_REEL,
        topic="Quick video editing tips",
        reasoning="TikTok is where our audience is",
        priority=2,
    )

    assert decision.priority == 2


def test_content_decision_priority_validation() -> None:
    """ContentDecision rejects invalid priority values."""
    with pytest.raises(ValidationError) as exc_info:
        ContentDecision(
            product="invoz",
            platform=Platform.TWITTER,
            content_type=ContentType.THREAD,
            topic="Voice AI trends",
            reasoning="Twitter threads get good engagement",
            priority=5,  # Invalid: must be 1-3
        )

    errors = exc_info.value.errors()
    assert any("priority" in str(e) for e in errors)


def test_content_decision_estimated_engagement_validation() -> None:
    """ContentDecision rejects invalid estimated_engagement values."""
    with pytest.raises(ValidationError) as exc_info:
        ContentDecision(
            product="pilaster",
            platform=Platform.INSTAGRAM,
            content_type=ContentType.CAROUSEL,
            topic="AI art showcase",
            reasoning="Visual content works on Instagram",
            estimated_engagement="very_high",  # Invalid: must be low/medium/high
        )

    errors = exc_info.value.errors()
    assert any("estimated_engagement" in str(e) for e in errors)


def test_content_decision_from_dict() -> None:
    """ContentDecision can be created from a dictionary."""
    data = {
        "product": "genpeli",
        "platform": "linkedin",
        "content_type": "demo",
        "topic": "Automated video editing demo",
        "reasoning": "Show the product in action",
        "priority": 1,
        "estimated_engagement": "high",
    }

    decision = ContentDecision(**data)
    assert decision.product == "genpeli"
    assert decision.platform == Platform.LINKEDIN


def test_content_decision_authority_fields() -> None:
    """ContentDecision accepts authority-engine fields."""
    decision = ContentDecision(
        product="pilaster",
        platform=Platform.LINKEDIN,
        content_type=ContentType.TUTORIAL,
        content_pillar="builder_stories",
        topic="What I learned building Pilaster",
        hook="I built an AI image platform from scratch.",
        framework="builder_journey",
        reasoning="Builder stories resonate with consulting prospects",
        repurpose_notes="Good for Twitter thread",
    )

    assert decision.content_pillar == "builder_stories"
    assert decision.hook == "I built an AI image platform from scratch."
    assert decision.framework == "builder_journey"
    assert decision.repurpose_notes == "Good for Twitter thread"


def test_content_decision_authority_defaults() -> None:
    """ContentDecision has sensible defaults for authority fields."""
    decision = ContentDecision(
        product="genpeli",
        content_type=ContentType.DEMO,
        topic="Video editing automation",
        reasoning="Test",
    )

    assert decision.platform == Platform.LINKEDIN  # default
    assert decision.content_pillar == "builder_stories"  # default
    assert decision.hook == ""  # default
    assert decision.framework == "original"  # default
    assert decision.repurpose_notes == ""  # default


def test_content_decision_authority_serialization() -> None:
    """ContentDecision authority fields serialize correctly."""
    decision = ContentDecision(
        product="invoz",
        content_type=ContentType.EDUCATIONAL,
        content_pillar="ai_frameworks",
        topic="Whisper in production",
        hook="Most Whisper tutorials skip the hard part.",
        framework="contrarian_opener",
        reasoning="Framework content for consulting prospects",
        repurpose_notes="Condense for Twitter",
    )

    data = decision.model_dump(mode="json")
    assert data["content_pillar"] == "ai_frameworks"
    assert data["hook"] == "Most Whisper tutorials skip the hard part."
    assert data["framework"] == "contrarian_opener"
    assert data["repurpose_notes"] == "Condense for Twitter"

    # Roundtrip
    restored = ContentDecision(**data)
    assert restored.content_pillar == decision.content_pillar
    assert restored.hook == decision.hook


# ---------------------------------------------------------------------------
# GeneratedPiece Tests
# ---------------------------------------------------------------------------


def test_generated_piece_valid() -> None:
    """GeneratedPiece validates with all required fields."""
    decision = ContentDecision(
        product="pilaster",
        platform=Platform.LINKEDIN,
        content_type=ContentType.TUTORIAL,
        topic="AI image generation basics",
        reasoning="Educational content",
    )

    piece = GeneratedPiece(
        piece_id="piece-123",
        decision=decision,
        text="Here's how to generate amazing AI images...",
        platform=Platform.LINKEDIN,
        model_used="sonnet-4-6",
    )

    assert piece.piece_id == "piece-123"
    assert piece.decision.product == "pilaster"
    assert piece.text.startswith("Here's how")
    assert piece.status == "pending_review"  # default
    assert piece.post_url is None  # default


def test_generated_piece_with_timestamp() -> None:
    """GeneratedPiece includes auto-generated timestamp."""
    decision = ContentDecision(
        product="invoz",
        platform=Platform.TWITTER,
        content_type=ContentType.TIPS,
        topic="Voice AI tips",
        reasoning="Quick tips perform well",
    )

    before = datetime.now(UTC)
    piece = GeneratedPiece(
        piece_id="piece-456",
        decision=decision,
        text="3 tips for better voice AI...",
        platform=Platform.TWITTER,
        model_used="sonnet-4-6",
    )
    after = datetime.now(UTC)

    assert before <= piece.generated_at <= after


def test_generated_piece_status_validation() -> None:
    """GeneratedPiece rejects invalid status values."""
    decision = ContentDecision(
        product="genpeli",
        platform=Platform.TIKTOK,
        content_type=ContentType.VIDEO_REEL,
        topic="Video editing reel",
        reasoning="TikTok engagement",
    )

    with pytest.raises(ValidationError) as exc_info:
        GeneratedPiece(
            piece_id="piece-789",
            decision=decision,
            text="Video brief...",
            platform=Platform.TIKTOK,
            model_used="sonnet-4-6",
            status="in_review",  # Invalid: not in allowed values
        )

    errors = exc_info.value.errors()
    assert any("status" in str(e) for e in errors)


def test_generated_piece_with_post_url() -> None:
    """GeneratedPiece can store post URL after publishing."""
    decision = ContentDecision(
        product="pilaster",
        platform=Platform.LINKEDIN,
        content_type=ContentType.TUTORIAL,
        topic="Image generation tutorial",
        reasoning="Educational",
    )

    piece = GeneratedPiece(
        piece_id="piece-published",
        decision=decision,
        text="Tutorial content...",
        platform=Platform.LINKEDIN,
        model_used="sonnet-4-6",
        status="published",
        post_url="https://linkedin.com/posts/123456",
    )

    assert piece.status == "published"
    assert piece.post_url == "https://linkedin.com/posts/123456"


# ---------------------------------------------------------------------------
# MarketingCycleReport Tests
# ---------------------------------------------------------------------------


def test_marketing_cycle_report_valid() -> None:
    """MarketingCycleReport validates with all required fields."""
    started = datetime.now(UTC)
    completed = datetime.now(UTC)

    report = MarketingCycleReport(
        cycle_id="cycle-001",
        started_at=started,
        completed_at=completed,
        decisions_made=3,
        pieces_generated=3,
        pieces_published=2,
        products_covered=["pilaster", "genpeli"],
        platforms_used=[Platform.LINKEDIN, Platform.TWITTER],
        total_cost_usd=0.45,
    )

    assert report.cycle_id == "cycle-001"
    assert report.decisions_made == 3
    assert report.pieces_generated == 3
    assert report.pieces_published == 2
    assert len(report.products_covered) == 2
    assert len(report.platforms_used) == 2
    assert report.total_cost_usd == 0.45


def test_marketing_cycle_report_defaults() -> None:
    """MarketingCycleReport uses defaults for optional fields."""
    started = datetime.now(UTC)
    completed = datetime.now(UTC)

    report = MarketingCycleReport(
        cycle_id="cycle-002",
        started_at=started,
        completed_at=completed,
        decisions_made=0,
        pieces_generated=0,
        pieces_published=0,
    )

    assert report.products_covered == []
    assert report.platforms_used == []
    assert report.total_cost_usd == 0.0


def test_marketing_cycle_report_negative_counts_rejected() -> None:
    """MarketingCycleReport rejects negative counts."""
    started = datetime.now(UTC)
    completed = datetime.now(UTC)

    with pytest.raises(ValidationError) as exc_info:
        MarketingCycleReport(
            cycle_id="cycle-invalid",
            started_at=started,
            completed_at=completed,
            decisions_made=-1,  # Invalid: must be >= 0
            pieces_generated=0,
            pieces_published=0,
        )

    errors = exc_info.value.errors()
    assert any("decisions_made" in str(e) for e in errors)


def test_marketing_cycle_report_negative_cost_rejected() -> None:
    """MarketingCycleReport rejects negative costs."""
    started = datetime.now(UTC)
    completed = datetime.now(UTC)

    with pytest.raises(ValidationError) as exc_info:
        MarketingCycleReport(
            cycle_id="cycle-invalid-cost",
            started_at=started,
            completed_at=completed,
            decisions_made=1,
            pieces_generated=1,
            pieces_published=1,
            total_cost_usd=-0.50,  # Invalid: must be >= 0
        )

    errors = exc_info.value.errors()
    assert any("total_cost_usd" in str(e) for e in errors)


def test_marketing_cycle_report_to_dict() -> None:
    """MarketingCycleReport can be serialized to dict."""
    started = datetime.now(UTC)
    completed = datetime.now(UTC)

    report = MarketingCycleReport(
        cycle_id="cycle-serialize",
        started_at=started,
        completed_at=completed,
        decisions_made=2,
        pieces_generated=2,
        pieces_published=1,
        products_covered=["pilaster"],
        platforms_used=[Platform.LINKEDIN],
        total_cost_usd=0.30,
    )

    data = report.model_dump()
    assert data["cycle_id"] == "cycle-serialize"
    assert data["decisions_made"] == 2
    assert data["products_covered"] == ["pilaster"]
    assert data["platforms_used"] == [Platform.LINKEDIN]


# ---------------------------------------------------------------------------
# BrandIdentity Tests
# ---------------------------------------------------------------------------


def test_brand_identity_empty_defaults() -> None:
    """BrandIdentity has sensible defaults for all fields."""
    brand = BrandIdentity()

    assert brand.story == {}
    assert brand.positioning.one_liner == ""
    assert brand.voice.archetype == ""
    assert brand.content_pillars == []
    assert brand.anti_patterns == {}
    assert brand.platform_strategy == {}


def test_brand_identity_full() -> None:
    """BrandIdentity validates a fully populated config."""
    brand = BrandIdentity(
        story={"origin": "Colombian AI engineer"},
        positioning=BrandPositioning(
            one_liner="I build AI systems",
            category="AI consultant",
            differentiation=["Builder, not advisor"],
        ),
        voice=BrandVoice(
            archetype="Builder-philosopher",
            summary="Direct, honest",
            tone=["First person always"],
        ),
        content_pillars=[
            ContentPillar(
                id="builder_stories",
                name="Builder Stories",
                description="I built X",
            )
        ],
        anti_patterns={"language": ["leverage synergies"]},
        platform_strategy={"primary": "linkedin"},
    )

    assert brand.story["origin"] == "Colombian AI engineer"
    assert brand.positioning.one_liner == "I build AI systems"
    assert brand.voice.archetype == "Builder-philosopher"
    assert len(brand.content_pillars) == 1
    assert brand.content_pillars[0].id == "builder_stories"
    assert "leverage synergies" in brand.anti_patterns["language"]


def test_brand_identity_model_dump() -> None:
    """BrandIdentity serializes to JSON-compatible dict."""
    brand = BrandIdentity(
        positioning=BrandPositioning(one_liner="Test"),
        voice=BrandVoice(archetype="Builder"),
    )

    data = brand.model_dump(mode="json")
    assert isinstance(data, dict)
    assert data["positioning"]["one_liner"] == "Test"
    assert data["voice"]["archetype"] == "Builder"


def test_brand_positioning_defaults() -> None:
    """BrandPositioning has empty string defaults."""
    pos = BrandPositioning()
    assert pos.one_liner == ""
    assert pos.category == ""
    assert pos.differentiation == []
    assert pos.market == ""


def test_brand_voice_defaults() -> None:
    """BrandVoice has empty defaults."""
    voice = BrandVoice()
    assert voice.archetype == ""
    assert voice.tone == []
    assert voice.hooks == {}
    assert voice.closers == {}


def test_content_pillar_requires_fields() -> None:
    """ContentPillar requires id, name, and description."""
    with pytest.raises(ValidationError):
        ContentPillar()  # type: ignore[call-arg]

    pillar = ContentPillar(id="test", name="Test", description="Description")
    assert pillar.id == "test"
    assert pillar.frequency == ""  # optional
    assert pillar.products == []  # optional


def test_brand_identity_extra_fields_ignored() -> None:
    """BrandIdentity ignores unknown top-level keys from YAML."""
    brand = BrandIdentity(
        unknown_field="should be ignored",  # type: ignore[call-arg]
        positioning=BrandPositioning(one_liner="Test"),
    )
    assert brand.positioning.one_liner == "Test"
