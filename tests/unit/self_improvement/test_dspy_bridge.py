"""Tests for DSPy bridge — dataset building and few-shot selection."""

import json
from pathlib import Path

import pytest

from holus.self_improvement.dspy_bridge import DSPyBridge, DSPyExample


@pytest.fixture
def trajectory_file(tmp_path):
    """Create a trajectory file with mixed entries."""
    path = tmp_path / "trajectory.jsonl"
    entries = [
        {"agent_id": "idea-generator", "task_summary": "Write carousel about MCP", "judge_score": 0.92, "metadata": {"output": "Great carousel content", "content_type": "carousel", "platform": "linkedin"}},
        {"agent_id": "idea-generator", "task_summary": "Write text post about agents", "judge_score": 0.85, "metadata": {"output": "Agent post content", "content_type": "text_post", "platform": "linkedin"}},
        {"agent_id": "idea-generator", "task_summary": "Write thread about AI", "judge_score": 0.78, "metadata": {"output": "Thread content", "content_type": "thread", "platform": "twitter"}},
        {"agent_id": "idea-generator", "task_summary": "Write bad post", "judge_score": 0.3, "metadata": {"output": "Bad content", "content_type": "text_post", "platform": "linkedin"}},
        {"agent_id": "other-agent", "task_summary": "Different task", "judge_score": 0.95, "metadata": {"output": "Other output", "content_type": "code", "platform": "github"}},
        {"agent_id": "idea-generator", "task_summary": "No output entry", "judge_score": 0.9, "metadata": {}},
    ]
    with open(path, "w") as fh:
        for e in entries:
            fh.write(json.dumps(e) + "\n")
    return path


class TestBuildDataset:
    def test_filters_by_agent(self, trajectory_file, tmp_path):
        bridge = DSPyBridge(trajectory_path=trajectory_file, prompts_dir=tmp_path / "prompts")
        dataset = bridge.build_dataset("idea-generator", min_score=0.75)
        assert all(e.agent_id == "idea-generator" for e in dataset)
        assert len(dataset) == 3  # 0.92, 0.85, and 0.78 (all >= 0.75; 0.3 too low; no-output skipped)

    def test_filters_by_score(self, trajectory_file, tmp_path):
        bridge = DSPyBridge(trajectory_path=trajectory_file, prompts_dir=tmp_path / "prompts")
        dataset = bridge.build_dataset("idea-generator", min_score=0.9)
        assert len(dataset) == 1
        assert dataset[0].score == 0.92

    def test_sorted_by_score(self, trajectory_file, tmp_path):
        bridge = DSPyBridge(trajectory_path=trajectory_file, prompts_dir=tmp_path / "prompts")
        dataset = bridge.build_dataset("idea-generator", min_score=0.0)
        scores = [e.score for e in dataset]
        assert scores == sorted(scores, reverse=True)

    def test_empty_trajectory(self, tmp_path):
        bridge = DSPyBridge(trajectory_path=tmp_path / "nonexistent.jsonl", prompts_dir=tmp_path)
        assert bridge.build_dataset("any") == []


class TestSelectFewShot:
    def test_diverse_selection(self, trajectory_file, tmp_path):
        bridge = DSPyBridge(trajectory_path=trajectory_file, prompts_dir=tmp_path / "prompts")
        dataset = bridge.build_dataset("idea-generator", min_score=0.0)
        selected = bridge.select_few_shot(dataset, k=2, diverse=True)
        # Should pick from different content_types/platforms
        platforms = {e.platform for e in selected}
        assert len(selected) == 2

    def test_non_diverse_takes_top_k(self, trajectory_file, tmp_path):
        bridge = DSPyBridge(trajectory_path=trajectory_file, prompts_dir=tmp_path / "prompts")
        dataset = bridge.build_dataset("idea-generator", min_score=0.0)
        selected = bridge.select_few_shot(dataset, k=2, diverse=False)
        assert selected[0].score >= selected[1].score


class TestFormatAndSave:
    def test_format_few_shot_block(self, trajectory_file, tmp_path):
        bridge = DSPyBridge(trajectory_path=trajectory_file, prompts_dir=tmp_path / "prompts")
        dataset = bridge.build_dataset("idea-generator", min_score=0.8)
        block = bridge.format_few_shot_block(dataset)
        assert "<few_shot_examples>" in block
        assert "<example>" in block
        assert "0.92" in block

    def test_save_to_prompt(self, trajectory_file, tmp_path):
        prompts_dir = tmp_path / "prompts"
        bridge = DSPyBridge(trajectory_path=trajectory_file, prompts_dir=prompts_dir)
        dataset = bridge.build_dataset("idea-generator", min_score=0.8)
        path = bridge.save_to_prompt("idea-generator", dataset)
        assert path is not None
        assert path.exists()
        content = path.read_text()
        assert "<few_shot_examples>" in content

    def test_save_dataset_jsonl(self, trajectory_file, tmp_path):
        prompts_dir = tmp_path / "prompts"
        bridge = DSPyBridge(trajectory_path=trajectory_file, prompts_dir=prompts_dir)
        dataset = bridge.build_dataset("idea-generator", min_score=0.0)
        path = bridge.save_dataset("idea-generator", dataset)
        assert path.exists()
        lines = path.read_text().strip().split("\n")
        assert len(lines) == len(dataset)

    def test_empty_examples_returns_none(self, tmp_path):
        bridge = DSPyBridge(trajectory_path=tmp_path / "empty.jsonl", prompts_dir=tmp_path)
        assert bridge.save_to_prompt("agent", []) is None

    def test_format_empty_returns_empty(self, tmp_path):
        bridge = DSPyBridge(trajectory_path=tmp_path / "empty.jsonl", prompts_dir=tmp_path)
        assert bridge.format_few_shot_block([]) == ""


class TestActivation:
    def test_not_activated_with_few_entries(self, trajectory_file, tmp_path):
        bridge = DSPyBridge(trajectory_path=trajectory_file, prompts_dir=tmp_path)
        assert not bridge.is_activated()  # Only 6 entries, need 500

    def test_count_entries(self, trajectory_file, tmp_path):
        bridge = DSPyBridge(trajectory_path=trajectory_file, prompts_dir=tmp_path)
        assert bridge.count_entries() == 6
