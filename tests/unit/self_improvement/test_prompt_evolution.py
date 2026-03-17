"""Tests for genetic prompt evolution."""

from holus.self_improvement.prompt_evolution import PromptEvolution, PromptVariant


class TestPromptVariant:
    def test_initial_state(self):
        v = PromptVariant(
            variant_id="v1", prompt_text="test", parent_ids=[],
            mutation_type="canonical", created_at="2026-01-01",
        )
        assert v.n_evaluations == 0
        assert v.avg_score == 0.0

    def test_record_score(self):
        v = PromptVariant(
            variant_id="v1", prompt_text="test", parent_ids=[],
            mutation_type="canonical", created_at="2026-01-01",
        )
        v.record_score(0.8)
        v.record_score(0.6)
        assert v.n_evaluations == 2
        assert abs(v.avg_score - 0.7) < 0.01

    def test_serialization(self):
        v = PromptVariant(
            variant_id="v1", prompt_text="prompt text", parent_ids=["v0"],
            mutation_type="mutation", created_at="2026-01-01",
        )
        v.record_score(0.9)
        d = v.to_dict()
        v2 = PromptVariant.from_dict(d, prompt_text="prompt text")
        assert v2.variant_id == "v1"
        assert v2.n_evaluations == 1
        assert v2.avg_score == 0.9


class TestPromptEvolution:
    def test_initialize_population(self, tmp_path):
        # Patch the populations dir
        import holus.self_improvement.prompt_evolution as mod
        original = mod.POPULATIONS_DIR
        mod.POPULATIONS_DIR = tmp_path
        try:
            evo = PromptEvolution("test-agent")
            evo._pop_dir = tmp_path / "test-agent"
            evo._meta_path = evo._pop_dir / "population.json"
            evo.initialize_population("You are a test agent.")
            assert evo.population_size == 1
            prompt, vid = evo.get_active_prompt()
            assert "test agent" in prompt
            assert vid == "canonical"
        finally:
            mod.POPULATIONS_DIR = original

    def test_record_evaluation(self, tmp_path):
        import holus.self_improvement.prompt_evolution as mod
        original = mod.POPULATIONS_DIR
        mod.POPULATIONS_DIR = tmp_path
        try:
            evo = PromptEvolution("test-agent")
            evo._pop_dir = tmp_path / "test-agent"
            evo._meta_path = evo._pop_dir / "population.json"
            evo.initialize_population("You are a test agent.")
            evo.record_evaluation("canonical", 0.85)
            prompt, vid = evo.get_active_prompt()
            assert vid == "canonical"
        finally:
            mod.POPULATIONS_DIR = original

    def test_empty_population(self, tmp_path):
        import holus.self_improvement.prompt_evolution as mod
        original = mod.POPULATIONS_DIR
        mod.POPULATIONS_DIR = tmp_path
        try:
            evo = PromptEvolution("empty-agent")
            evo._pop_dir = tmp_path / "empty-agent"
            evo._meta_path = evo._pop_dir / "population.json"
            prompt, vid = evo.get_active_prompt()
            assert prompt == ""
            assert vid == "none"
        finally:
            mod.POPULATIONS_DIR = original
