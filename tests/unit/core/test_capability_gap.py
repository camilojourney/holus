from holus.core.capability_gap import CapabilityGap, CapabilityRequest, CapabilityTier


def test_capability_gap_model():
    gap = CapabilityGap(
        what="Carousel content adapter",
        why="Tutorials get 4x engagement",
        tier=CapabilityTier.TIER_2_CODE,
        evidence="Top 3 competitors use carousels",
        workaround="Single image",
        priority=3,
    )
    assert gap.what == "Carousel content adapter"
    assert gap.tier == "tier_2_code"
    assert gap.priority == 3


def test_capability_request_model():
    request = CapabilityRequest(
        what="Carousel content adapter",
        why="High engagement",
        slug="carousel-adapter",
        status="pending",
    )
    assert request.status == "pending"
    assert request.tier == "tier_2_code"
    assert request.slug == "carousel-adapter"
    assert request.created_at != ""
