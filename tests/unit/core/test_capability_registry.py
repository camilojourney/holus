from holus.core.capability_registry import CapabilityRegistry


def test_capability_registry_load(tmp_path):
    config_file = tmp_path / "capabilities.yaml"
    config_file.write_text("""
platforms:
  - linkedin
  - twitter
content_types:
  - tutorial
silos:
  - pilaster
specialists:
  - text
reviewers:
  - quality_score
""")
    registry = CapabilityRegistry(config_path=config_file)
    assert registry.is_supported("platforms", "linkedin")
    assert registry.is_supported("platforms", "TWITTER")
    assert not registry.is_supported("platforms", "tiktok")
    assert registry.is_supported("content_types", "tutorial")
    assert registry.is_supported("silos", "pilaster")
    assert registry.is_supported("specialists", "text")
    assert registry.is_supported("reviewers", "quality_score")


def test_capability_registry_no_file(tmp_path):
    config_file = tmp_path / "non_existent.yaml"
    registry = CapabilityRegistry(config_path=config_file)
    assert registry.platforms == []
    assert not registry.is_supported("platforms", "linkedin")
