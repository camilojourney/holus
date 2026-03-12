import yaml

from holus.core.capability_gap import CapabilityGap, CapabilityTier
from holus.self_improvement.config_builder import ConfigBuilder


def test_config_builder_specialist(tmp_path):
    builder = ConfigBuilder(config_root=tmp_path)
    gap = CapabilityGap(
        what="Carousel specialist",
        why="High engagement",
        tier=CapabilityTier.TIER_1_CONFIG,
        evidence="Competitors use it",
    )
    assert builder.build_from_gap(gap)

    target_file = tmp_path / "specialists" / "spawned" / "carousel_specialist.yaml"
    assert target_file.exists()

    with open(target_file) as f:
        data = yaml.safe_load(f)
        assert data["name"] == "Carousel specialist"
        assert data["created_via"] == "self_improvement_tier_1"


def test_config_builder_reviewer(tmp_path):
    builder = ConfigBuilder(config_root=tmp_path)
    gap = CapabilityGap(
        what="Aesthetic reviewer", why="Quality control", tier=CapabilityTier.TIER_1_CONFIG
    )
    assert builder.build_from_gap(gap)

    target_file = tmp_path / "reviewers" / "spawned" / "aesthetic_reviewer.yaml"
    assert target_file.exists()


def test_config_builder_invalid_tier(tmp_path):
    builder = ConfigBuilder(config_root=tmp_path)
    gap = CapabilityGap(what="New Python module", why="Needs code", tier=CapabilityTier.TIER_2_CODE)
    assert not builder.build_from_gap(gap)
