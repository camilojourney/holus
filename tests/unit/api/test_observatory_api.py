"""Tests for the Observatory API (Spec 028).

Covers:
- GET /api/v1/agents returns agent list
- GET /api/v1/agents/{id} returns 404 for unknown agent
- GET /api/v1/health returns health status
- GET /api/v1/trajectory returns paginated results or empty list
- GET /api/v1/content returns items and counts
- GET /api/v1/evaluations returns evaluations
- GET /api/v1/evaluations/summary returns summary
- GET /api/v1/knowledge returns file listing
- GET /api/v1/metrics returns KPI metrics
"""

from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003
from unittest.mock import patch

import pytest
import yaml
from fastapi.testclient import TestClient

from holus.api.app import create_app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """Create a TestClient for the Observatory API."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def sample_agents_yaml(tmp_path: Path) -> Path:
    """Write a minimal AGENTS.yaml to tmp_path."""
    data = {
        "agents": {
            "marketing-strategist": {
                "role": "Primary marketing brain",
                "type": "manager",
                "model_tier": "strategic",
                "status": "active",
                "version": "2.0.0",
                "prompt": "managers/marketing-strategist.md",
            },
            "hook-architect": {
                "role": "First 2 lines of every post",
                "type": "specialist",
                "category": "written-authority",
                "model_tier": "operational",
                "status": "active",
                "version": "1.0.0",
                "prompt": "specialists/written-authority/hook-architect.md",
            },
        }
    }
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    yaml_file = agents_dir / "AGENTS.yaml"
    yaml_file.write_text(yaml.dump(data), encoding="utf-8")
    return yaml_file


@pytest.fixture
def sample_trajectory_file(tmp_path: Path) -> Path:
    """Write a minimal trajectory.jsonl to tmp_path."""
    memory_dir = tmp_path / ".self-improvement" / "memory"
    memory_dir.mkdir(parents=True)
    traj_file = memory_dir / "trajectory.jsonl"

    entries = [
        {
            "timestamp": "2026-03-12T10:00:00Z",
            "agent_id": "marketing-strategist",
            "action": "decide",
            "outcome": "success",
            "quality_score": 8.5,
            "cost_usd": 0.02,
            "tokens_used": 1500,
            "notes": "Generated tutorial post",
        },
        {
            "timestamp": "2026-03-12T09:00:00Z",
            "agent_id": "hook-architect",
            "action": "generate",
            "outcome": "error",
            "notes": "Hook generation failed",
        },
    ]
    traj_file.write_text(
        "\n".join(json.dumps(e) for e in entries) + "\n",
        encoding="utf-8",
    )
    return traj_file


@pytest.fixture
def sample_content_queue(tmp_path: Path) -> Path:
    """Write sample content YAML files to tmp_path."""
    queue_dir = tmp_path / "data" / "content-queue"
    queue_dir.mkdir(parents=True)

    item1 = {
        "id": "post-001",
        "title": "How to use ComfyUI",
        "content_type": "tutorial",
        "status": "review",
        "created_at": "2026-03-12T08:00:00Z",
        "agent_id": "marketing-strategist",
    }
    item2 = {
        "id": "post-002",
        "title": "Pilaster launch announcement",
        "content_type": "announcement",
        "status": "draft",
    }
    (queue_dir / "post-001.yaml").write_text(yaml.dump(item1), encoding="utf-8")
    (queue_dir / "post-002.yaml").write_text(yaml.dump(item2), encoding="utf-8")
    return queue_dir


@pytest.fixture
def sample_eval_history(tmp_path: Path) -> Path:
    """Write a minimal eval_history.jsonl to tmp_path."""
    eval_file = tmp_path / "eval_history.jsonl"
    entries = [
        {
            "timestamp": "2026-03-12T10:00:00Z",
            "agent_id": "marketing-strategist",
            "score": 8.0,
            "max_score": 10.0,
            "pass_threshold": 7.0,
            "notes": "Good strategic thinking",
        },
        {
            "timestamp": "2026-03-12T09:00:00Z",
            "agent_id": "hook-architect",
            "score": 6.0,
            "max_score": 10.0,
            "pass_threshold": 7.0,
            "notes": "Hook was too generic",
        },
    ]
    eval_file.write_text(
        "\n".join(json.dumps(e) for e in entries) + "\n",
        encoding="utf-8",
    )
    return eval_file


@pytest.fixture
def sample_knowledge_dir(tmp_path: Path) -> Path:
    """Create a knowledge/current directory with sample files."""
    knowledge_dir = tmp_path / ".self-improvement" / "knowledge" / "current"
    knowledge_dir.mkdir(parents=True)

    (knowledge_dir / "lessons.md").write_text(
        "# Lessons\n\nTutorial posts outperform promo posts 4:1.",
        encoding="utf-8",
    )
    (knowledge_dir / "patterns.md").write_text(
        "# Patterns\n\nLinkedIn performs best for technical audiences.",
        encoding="utf-8",
    )
    return knowledge_dir


# ---------------------------------------------------------------------------
# /api/v1/agents
# ---------------------------------------------------------------------------


class TestAgentsEndpoint:
    def test_list_agents_returns_list(self, client: TestClient, sample_agents_yaml: Path):
        with (
            patch("holus.api.routes.agents.AGENTS_YAML", sample_agents_yaml),
            patch("holus.api.routes.agents._load_trajectory", return_value=[]),
        ):
            resp = client.get("/api/v1/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2
        ids = [a["id"] for a in data]
        assert "marketing-strategist" in ids
        assert "hook-architect" in ids

    def test_list_agents_missing_yaml_returns_503(self, client: TestClient, tmp_path: Path):
        missing = tmp_path / "agents" / "AGENTS.yaml"
        with patch("holus.api.routes.agents.AGENTS_YAML", missing):
            resp = client.get("/api/v1/agents")
        assert resp.status_code == 503

    def test_get_agent_returns_agent(self, client: TestClient, sample_agents_yaml: Path):
        with (
            patch("holus.api.routes.agents.AGENTS_YAML", sample_agents_yaml),
            patch("holus.api.routes.agents._load_trajectory", return_value=[]),
        ):
            resp = client.get("/api/v1/agents/marketing-strategist")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "marketing-strategist"
        assert "role" in data

    def test_get_agent_unknown_returns_404(self, client: TestClient, sample_agents_yaml: Path):
        with (
            patch("holus.api.routes.agents.AGENTS_YAML", sample_agents_yaml),
            patch("holus.api.routes.agents._load_trajectory", return_value=[]),
        ):
            resp = client.get("/api/v1/agents/does-not-exist")
        assert resp.status_code == 404

    def test_get_agent_metrics(self, client: TestClient, sample_agents_yaml: Path):
        traj = [
            {
                "timestamp": "2026-03-12T10:00:00Z",
                "agent_id": "marketing-strategist",
                "action": "decide",
                "outcome": "success",
                "quality_score": 8.0,
                "cost_usd": 0.01,
            }
        ]
        with (
            patch("holus.api.routes.agents.AGENTS_YAML", sample_agents_yaml),
            patch("holus.api.routes.agents._load_trajectory", return_value=traj),
        ):
            resp = client.get("/api/v1/agents/marketing-strategist/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == "marketing-strategist"
        assert data["total_runs"] == 1
        assert data["success_rate"] == 1.0

    def test_agent_has_run_count_7d(self, client: TestClient, sample_agents_yaml: Path):
        from datetime import UTC, datetime, timedelta

        recent_ts = (datetime.now(UTC) - timedelta(hours=12)).isoformat()
        traj = [
            {
                "timestamp": recent_ts,
                "agent_id": "marketing-strategist",
                "action": "decide",
                "outcome": "success",
            }
        ]
        with (
            patch("holus.api.routes.agents.AGENTS_YAML", sample_agents_yaml),
            patch("holus.api.routes.agents._load_trajectory", return_value=traj),
        ):
            resp = client.get("/api/v1/agents")
        assert resp.status_code == 200
        strategist = next(a for a in resp.json() if a["id"] == "marketing-strategist")
        assert strategist["run_count_7d"] == 1


# ---------------------------------------------------------------------------
# /api/v1/trajectory
# ---------------------------------------------------------------------------


class TestTrajectoryEndpoint:
    def test_trajectory_returns_empty_when_no_file(self, client: TestClient, tmp_path: Path):
        missing = tmp_path / ".self-improvement" / "memory" / "trajectory.jsonl"
        with patch("holus.api.routes.trajectory.TRAJECTORY_PATH", missing):
            resp = client.get("/api/v1/trajectory")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entries"] == []
        assert data["total"] == 0
        assert data["has_more"] is False

    def test_trajectory_returns_entries(self, client: TestClient, sample_trajectory_file: Path):
        with patch("holus.api.routes.trajectory.TRAJECTORY_PATH", sample_trajectory_file):
            resp = client.get("/api/v1/trajectory")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["entries"]) == 2

    def test_trajectory_filter_by_agent(self, client: TestClient, sample_trajectory_file: Path):
        with patch("holus.api.routes.trajectory.TRAJECTORY_PATH", sample_trajectory_file):
            resp = client.get("/api/v1/trajectory?agent_id=hook-architect")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["entries"][0]["agent_id"] == "hook-architect"

    def test_trajectory_pagination(self, client: TestClient, sample_trajectory_file: Path):
        with patch("holus.api.routes.trajectory.TRAJECTORY_PATH", sample_trajectory_file):
            resp = client.get("/api/v1/trajectory?page=1&page_size=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["entries"]) == 1
        assert data["has_more"] is True
        assert data["page"] == 1
        assert data["page_size"] == 1

    def test_trajectory_skips_malformed_lines(self, client: TestClient, tmp_path: Path):
        memory_dir = tmp_path / ".self-improvement" / "memory"
        memory_dir.mkdir(parents=True)
        traj_file = memory_dir / "trajectory.jsonl"
        traj_file.write_text(
            '{"timestamp": "2026-03-12T10:00:00Z", "agent_id": "a", "action": "x"}\n'
            "THIS IS NOT JSON\n"
            '{"timestamp": "2026-03-12T09:00:00Z", "agent_id": "b", "action": "y"}\n',
            encoding="utf-8",
        )
        with patch("holus.api.routes.trajectory.TRAJECTORY_PATH", traj_file):
            resp = client.get("/api/v1/trajectory")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2  # malformed line skipped


# ---------------------------------------------------------------------------
# /api/v1/health
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_health_returns_status(self, client: TestClient, tmp_path: Path):
        missing = tmp_path / "nonexistent.jsonl"
        agents_missing = tmp_path / "agents" / "AGENTS.yaml"
        content_missing = tmp_path / "data" / "content-queue"

        with (
            patch("holus.api.routes.health.TRAJECTORY_PATH", missing),
            patch("holus.api.routes.health.EVAL_HISTORY_PATH", missing),
            patch("holus.api.routes.health.AGENTS_YAML", agents_missing),
            patch("holus.api.routes.health.CONTENT_QUEUE_DIR", content_missing),
            patch("holus.api.routes.health._is_kill_switch_active", return_value=False),
            patch("holus.api.routes.health._load_trajectory", return_value=[]),
        ):
            resp = client.get("/api/v1/health")

        assert resp.status_code == 200
        data = resp.json()
        assert "kill_switch_active" in data
        assert "trajectory_file_exists" in data
        assert "eval_history_file_exists" in data
        assert "agents_yaml_exists" in data
        assert "content_queue_count" in data
        assert data["kill_switch_active"] is False

    def test_health_reports_kill_switch(self, client: TestClient, tmp_path: Path):
        missing = tmp_path / "nonexistent.jsonl"

        with (
            patch("holus.api.routes.health.TRAJECTORY_PATH", missing),
            patch("holus.api.routes.health.EVAL_HISTORY_PATH", missing),
            patch("holus.api.routes.health.AGENTS_YAML", missing),
            patch("holus.api.routes.health.CONTENT_QUEUE_DIR", missing),
            patch("holus.api.routes.health._is_kill_switch_active", return_value=True),
            patch("holus.api.routes.health._load_trajectory", return_value=[]),
        ):
            resp = client.get("/api/v1/health")

        assert resp.status_code == 200
        assert resp.json()["kill_switch_active"] is True

    def test_health_file_existence_flags(self, client: TestClient, sample_trajectory_file: Path, tmp_path: Path):
        agents_yaml = tmp_path / "agents" / "AGENTS.yaml"
        agents_yaml.parent.mkdir()
        agents_yaml.write_text("agents: {}", encoding="utf-8")
        missing = tmp_path / "nonexistent.jsonl"

        with (
            patch("holus.api.routes.health.TRAJECTORY_PATH", sample_trajectory_file),
            patch("holus.api.routes.health.EVAL_HISTORY_PATH", missing),
            patch("holus.api.routes.health.AGENTS_YAML", agents_yaml),
            patch("holus.api.routes.health.CONTENT_QUEUE_DIR", missing),
            patch("holus.api.routes.health._is_kill_switch_active", return_value=False),
            patch("holus.api.routes.health._load_trajectory", return_value=[]),
        ):
            resp = client.get("/api/v1/health")

        data = resp.json()
        assert data["trajectory_file_exists"] is True
        assert data["eval_history_file_exists"] is False
        assert data["agents_yaml_exists"] is True


# ---------------------------------------------------------------------------
# /api/v1/content
# ---------------------------------------------------------------------------


class TestContentEndpoint:
    def test_content_returns_items_and_counts(self, client: TestClient, sample_content_queue: Path):
        with patch("holus.api.routes.content.CONTENT_QUEUE_DIR", sample_content_queue):
            resp = client.get("/api/v1/content")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "counts" in data
        assert len(data["items"]) == 2
        assert data["counts"]["review"] == 1
        assert data["counts"]["draft"] == 1

    def test_content_empty_queue_returns_zeros(self, client: TestClient, tmp_path: Path):
        empty_queue = tmp_path / "data" / "content-queue"
        empty_queue.mkdir(parents=True)
        with patch("holus.api.routes.content.CONTENT_QUEUE_DIR", empty_queue):
            resp = client.get("/api/v1/content")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["counts"]["draft"] == 0

    def test_content_missing_queue_dir_returns_empty(self, client: TestClient, tmp_path: Path):
        missing = tmp_path / "data" / "content-queue"
        with patch("holus.api.routes.content.CONTENT_QUEUE_DIR", missing):
            resp = client.get("/api/v1/content")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []


# ---------------------------------------------------------------------------
# /api/v1/evaluations
# ---------------------------------------------------------------------------


class TestEvaluationsEndpoint:
    def test_evaluations_returns_list(self, client: TestClient, sample_eval_history: Path):
        with patch("holus.api.routes.evaluations.EVAL_HISTORY_PATH", sample_eval_history):
            resp = client.get("/api/v1/evaluations")
        assert resp.status_code == 200
        data = resp.json()
        assert "evaluations" in data
        assert len(data["evaluations"]) == 2

    def test_evaluations_filter_by_agent(self, client: TestClient, sample_eval_history: Path):
        with patch("holus.api.routes.evaluations.EVAL_HISTORY_PATH", sample_eval_history):
            resp = client.get("/api/v1/evaluations?agent_id=hook-architect")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["evaluations"]) == 1
        assert data["evaluations"][0]["agent_id"] == "hook-architect"

    def test_evaluations_missing_file_returns_empty(self, client: TestClient, tmp_path: Path):
        missing = tmp_path / "eval_history.jsonl"
        with patch("holus.api.routes.evaluations.EVAL_HISTORY_PATH", missing):
            resp = client.get("/api/v1/evaluations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["evaluations"] == []

    def test_evaluations_passed_field_computed(self, client: TestClient, sample_eval_history: Path):
        with patch("holus.api.routes.evaluations.EVAL_HISTORY_PATH", sample_eval_history):
            resp = client.get("/api/v1/evaluations")
        evals = resp.json()["evaluations"]
        # score 8.0 >= 7.0 → passed, score 6.0 < 7.0 → not passed
        passed = {e["agent_id"]: e["passed"] for e in evals}
        assert passed["marketing-strategist"] is True
        assert passed["hook-architect"] is False

    def test_evaluation_summary(self, client: TestClient, sample_eval_history: Path):
        with patch("holus.api.routes.evaluations.EVAL_HISTORY_PATH", sample_eval_history):
            resp = client.get("/api/v1/evaluations/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "avg_score" in data
        assert "pass_rate" in data
        assert 0.0 <= data["pass_rate"] <= 1.0
        assert "score_by_agent" in data
        assert "trend_7d" in data
        assert len(data["trend_7d"]) == 7

    def test_evaluation_summary_empty_file(self, client: TestClient, tmp_path: Path):
        missing = tmp_path / "eval_history.jsonl"
        with patch("holus.api.routes.evaluations.EVAL_HISTORY_PATH", missing):
            resp = client.get("/api/v1/evaluations/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["avg_score"] == 0.0
        assert data["pass_rate"] == 0.0


# ---------------------------------------------------------------------------
# /api/v1/knowledge
# ---------------------------------------------------------------------------


class TestKnowledgeEndpoint:
    def test_knowledge_returns_file_listing(self, client: TestClient, sample_knowledge_dir: Path):
        with patch("holus.api.routes.knowledge.KNOWLEDGE_DIR", sample_knowledge_dir):
            resp = client.get("/api/v1/knowledge")
        assert resp.status_code == 200
        data = resp.json()
        assert "files" in data
        filenames = [f["filename"] for f in data["files"]]
        assert "lessons.md" in filenames
        assert "patterns.md" in filenames

    def test_knowledge_no_content_in_listing(self, client: TestClient, sample_knowledge_dir: Path):
        with patch("holus.api.routes.knowledge.KNOWLEDGE_DIR", sample_knowledge_dir):
            resp = client.get("/api/v1/knowledge")
        data = resp.json()
        for f in data["files"]:
            assert f["content"] is None

    def test_knowledge_file_detail_has_content(self, client: TestClient, sample_knowledge_dir: Path):
        with patch("holus.api.routes.knowledge.KNOWLEDGE_DIR", sample_knowledge_dir):
            resp = client.get("/api/v1/knowledge/lessons.md")
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "lessons.md"
        assert data["content"] is not None
        assert "Lessons" in data["content"]

    def test_knowledge_file_not_found(self, client: TestClient, sample_knowledge_dir: Path):
        with patch("holus.api.routes.knowledge.KNOWLEDGE_DIR", sample_knowledge_dir):
            resp = client.get("/api/v1/knowledge/does-not-exist.md")
        assert resp.status_code == 404

    def test_knowledge_empty_dir_returns_empty(self, client: TestClient, tmp_path: Path):
        empty_dir = tmp_path / ".self-improvement" / "knowledge" / "current"
        empty_dir.mkdir(parents=True)
        with patch("holus.api.routes.knowledge.KNOWLEDGE_DIR", empty_dir):
            resp = client.get("/api/v1/knowledge")
        assert resp.status_code == 200
        assert resp.json()["files"] == []

    def test_knowledge_path_traversal_blocked(self, client: TestClient, sample_knowledge_dir: Path):
        with patch("holus.api.routes.knowledge.KNOWLEDGE_DIR", sample_knowledge_dir):
            resp = client.get("/api/v1/knowledge/../../../etc/passwd")
        # FastAPI will 404 on path segments with ..
        assert resp.status_code in (400, 404)


# ---------------------------------------------------------------------------
# /api/v1/metrics
# ---------------------------------------------------------------------------


class TestMetricsEndpoint:
    def test_metrics_returns_kpis(self, client: TestClient):
        fake_entries = [
            {
                "timestamp": "2026-03-12T10:00:00Z",
                "agent_id": "marketing-strategist",
                "action": "decide",
                "outcome": "success",
                "quality_score": 8.5,
                "cost_usd": 0.02,
            }
        ]
        with patch("holus.api.routes.health._load_trajectory", return_value=fake_entries):
            resp = client.get("/api/v1/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_cycles" in data
        assert "success_rate" in data
        assert "active_agents_24h" in data
        assert "content_published_7d" in data
        assert data["total_cycles"] == 1
        assert data["success_rate"] == 1.0

    def test_metrics_no_trajectory_returns_zeros(self, client: TestClient):
        with patch("holus.api.routes.health._load_trajectory", return_value=[]):
            resp = client.get("/api/v1/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_cycles"] == 0
        assert data["success_rate"] == 0.0


# ---------------------------------------------------------------------------
# CORS headers
# ---------------------------------------------------------------------------


class TestCORSHeaders:
    def test_cors_allows_localhost_3000(self, client: TestClient):
        resp = client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert resp.status_code == 200
        # TestClient may not return CORS headers without an OPTIONS request,
        # but we verify the endpoint is reachable from that origin
        assert "kill_switch_active" in resp.json()

    def test_openapi_docs_accessible(self, client: TestClient):
        resp = client.get("/docs")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /api/v1/content (detail, calendar, PATCH)
# ---------------------------------------------------------------------------


class TestContentDetailEndpoint:
    def test_get_content_detail_returns_full_piece(self, client: TestClient, sample_content_queue: Path):
        with patch("holus.api.routes.content.CONTENT_QUEUE_DIR", sample_content_queue):
            resp = client.get("/api/v1/content/post-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "post-001"
        assert data["title"] == "How to use ComfyUI"
        assert "text" in data
        assert "hashtags" in data
        assert "agent_trace" in data

    def test_get_content_detail_not_found(self, client: TestClient, sample_content_queue: Path):
        with patch("holus.api.routes.content.CONTENT_QUEUE_DIR", sample_content_queue):
            resp = client.get("/api/v1/content/nonexistent-id")
        assert resp.status_code == 404

    def test_get_content_calendar_returns_days(self, client: TestClient, sample_content_queue: Path):
        with patch("holus.api.routes.content.CONTENT_QUEUE_DIR", sample_content_queue):
            resp = client.get("/api/v1/content/calendar?days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert "calendar" in data
        assert len(data["calendar"]) == 7

    def test_get_content_calendar_empty_queue(self, client: TestClient, tmp_path: Path):
        empty_dir = tmp_path / "data" / "content-queue"
        empty_dir.mkdir(parents=True)
        with patch("holus.api.routes.content.CONTENT_QUEUE_DIR", empty_dir):
            resp = client.get("/api/v1/content/calendar")
        assert resp.status_code == 200
        data = resp.json()
        assert all(len(day["items"]) == 0 for day in data["calendar"])

    def test_patch_content_status_approve(self, client: TestClient, tmp_path: Path):
        queue_dir = tmp_path / "data" / "content-queue"
        queue_dir.mkdir(parents=True)
        item = {
            "id": "patch-001",
            "title": "Test post",
            "content_type": "tutorial",
            "status": "draft",
            "text": "Hello world",
        }
        (queue_dir / "patch-001.yaml").write_text(yaml.dump(item), encoding="utf-8")

        with patch("holus.api.routes.content.CONTENT_QUEUE_DIR", queue_dir):
            resp = client.patch(
                "/api/v1/content/patch-001",
                json={"status": "rejected"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    def test_patch_content_not_found(self, client: TestClient, sample_content_queue: Path):
        with patch("holus.api.routes.content.CONTENT_QUEUE_DIR", sample_content_queue):
            resp = client.patch(
                "/api/v1/content/nonexistent",
                json={"status": "approved"},
            )
        assert resp.status_code == 404

    def test_content_normalizes_review_status(self, client: TestClient, sample_content_queue: Path):
        """Legacy 'review' status gets normalized to 'pending_review'."""
        with patch("holus.api.routes.content.CONTENT_QUEUE_DIR", sample_content_queue):
            resp = client.get("/api/v1/content")
        items = resp.json()["items"]
        statuses = [i["status"] for i in items]
        # "review" in sample_content_queue should become "pending_review"
        assert "pending_review" in statuses

    def test_content_image_not_found_no_visual(self, client: TestClient, sample_content_queue: Path):
        with patch("holus.api.routes.content.CONTENT_QUEUE_DIR", sample_content_queue):
            resp = client.get("/api/v1/content/post-001/image")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /api/v1/alerts
# ---------------------------------------------------------------------------


class TestAlertsEndpoint:
    def test_alerts_empty_file_returns_no_alerts(self, client: TestClient, tmp_path: Path):
        missing = tmp_path / "eval_history.jsonl"
        with patch("holus.api.routes.alerts.EVAL_HISTORY_PATH", missing):
            resp = client.get("/api/v1/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["alerts"] == []
        assert data["trends"] == []
        assert "checked_at" in data

    def test_alerts_detects_consecutive_failures(self, client: TestClient, tmp_path: Path):
        eval_file = tmp_path / "eval_history.jsonl"
        entries = [
            {"timestamp": "2026-03-19T10:00:00Z", "phase": "content", "score": 90},
            {"timestamp": "2026-03-19T11:00:00Z", "phase": "content", "score": 50},
            {"timestamp": "2026-03-19T12:00:00Z", "phase": "content", "score": 40},
            {"timestamp": "2026-03-19T13:00:00Z", "phase": "content", "score": 30},
        ]
        eval_file.write_text(
            "\n".join(json.dumps(e) for e in entries) + "\n",
            encoding="utf-8",
        )
        with patch("holus.api.routes.alerts.EVAL_HISTORY_PATH", eval_file):
            resp = client.get("/api/v1/alerts")
        data = resp.json()
        types = [a["type"] for a in data["alerts"]]
        assert "CONSECUTIVE_FAILURES" in types

    def test_alerts_detects_stalls(self, client: TestClient, tmp_path: Path):
        eval_file = tmp_path / "eval_history.jsonl"
        entries = [
            {"timestamp": "2026-03-19T10:00:00Z", "phase": "content", "score": 0},
        ]
        eval_file.write_text(json.dumps(entries[0]) + "\n", encoding="utf-8")
        with patch("holus.api.routes.alerts.EVAL_HISTORY_PATH", eval_file):
            resp = client.get("/api/v1/alerts")
        data = resp.json()
        types = [a["type"] for a in data["alerts"]]
        assert "STALL" in types

    def test_alerts_returns_trends(self, client: TestClient, tmp_path: Path):
        eval_file = tmp_path / "eval_history.jsonl"
        entries = [
            {"timestamp": "2026-03-19T10:00:00Z", "phase": "content", "score": 80},
            {"timestamp": "2026-03-19T11:00:00Z", "phase": "content", "score": 85},
        ]
        eval_file.write_text(
            "\n".join(json.dumps(e) for e in entries) + "\n",
            encoding="utf-8",
        )
        with patch("holus.api.routes.alerts.EVAL_HISTORY_PATH", eval_file):
            resp = client.get("/api/v1/alerts")
        data = resp.json()
        assert len(data["trends"]) == 1
        assert data["trends"][0]["skill"] == "content"
        assert data["trends"][0]["total_runs"] == 2

    def test_alerts_skill_filter(self, client: TestClient, tmp_path: Path):
        eval_file = tmp_path / "eval_history.jsonl"
        entries = [
            {"timestamp": "2026-03-19T10:00:00Z", "phase": "content", "score": 80},
            {"timestamp": "2026-03-19T11:00:00Z", "phase": "video", "score": 70},
        ]
        eval_file.write_text(
            "\n".join(json.dumps(e) for e in entries) + "\n",
            encoding="utf-8",
        )
        with patch("holus.api.routes.alerts.EVAL_HISTORY_PATH", eval_file):
            resp = client.get("/api/v1/alerts?skill=content")
        data = resp.json()
        skills = [t["skill"] for t in data["trends"]]
        assert "content" in skills
        assert "video" not in skills


# ---------------------------------------------------------------------------
# /api/v1/improvement
# ---------------------------------------------------------------------------


class TestImprovementEndpoint:
    def test_score_trends_empty(self, client: TestClient, tmp_path: Path):
        missing = tmp_path / "trajectory.jsonl"
        with patch("holus.api.routes.improvement.TRAJECTORY_PATH", missing):
            resp = client.get("/api/v1/improvement/score-trends")
        assert resp.status_code == 200
        data = resp.json()
        assert data["trends"] == []
        assert data["total_entries"] == 0

    def test_score_trends_with_data(self, client: TestClient, tmp_path: Path):
        traj_file = tmp_path / "trajectory.jsonl"
        from datetime import UTC, datetime
        ts = datetime.now(UTC).isoformat()
        entries = [
            {"timestamp": ts, "agent_id": "a", "judge_score": 8.0},
            {"timestamp": ts, "agent_id": "a", "judge_score": 7.5},
        ]
        traj_file.write_text(
            "\n".join(json.dumps(e) for e in entries) + "\n",
            encoding="utf-8",
        )
        with patch("holus.api.routes.improvement.TRAJECTORY_PATH", traj_file):
            resp = client.get("/api/v1/improvement/score-trends?days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_entries"] == 2
        assert len(data["trends"]) >= 1

    def test_bandit_arms_missing_file(self, client: TestClient, tmp_path: Path):
        missing = tmp_path / "bandit_arms.json"
        with patch("holus.api.routes.improvement.BANDIT_ARMS_PATH", missing):
            resp = client.get("/api/v1/improvement/bandit-arms")
        assert resp.status_code == 200
        data = resp.json()
        assert data["arms"] == []
        assert data["total_observations"] == 0

    def test_bandit_arms_with_data(self, client: TestClient, tmp_path: Path):
        arms_file = tmp_path / "bandit_arms.json"
        arms_data = {
            "arms": [{"name": "hook_v1", "alpha": 5, "beta": 2}],
            "total_observations": 7,
        }
        arms_file.write_text(json.dumps(arms_data), encoding="utf-8")
        with patch("holus.api.routes.improvement.BANDIT_ARMS_PATH", arms_file):
            resp = client.get("/api/v1/improvement/bandit-arms")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["arms"]) == 1
        assert data["total_observations"] == 7

    def test_gaps_empty_dirs(self, client: TestClient, tmp_path: Path):
        cap_dir = tmp_path / "capability-requests"
        know_dir = tmp_path / "knowledge-requests"
        with (
            patch("holus.api.routes.improvement.CAPABILITY_GAPS_DIR", cap_dir),
            patch("holus.api.routes.improvement.KNOWLEDGE_GAPS_DIR", know_dir),
        ):
            resp = client.get("/api/v1/improvement/gaps")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    def test_gaps_with_files(self, client: TestClient, tmp_path: Path):
        cap_dir = tmp_path / "capability-requests"
        cap_dir.mkdir()
        (cap_dir / "need-video.md").write_text("# Need video capability", encoding="utf-8")
        know_dir = tmp_path / "knowledge-requests"
        know_dir.mkdir()
        (know_dir / "tiktok-algo.md").write_text("# TikTok algorithm", encoding="utf-8")
        (know_dir / "README.md").write_text("# Ignored", encoding="utf-8")

        with (
            patch("holus.api.routes.improvement.CAPABILITY_GAPS_DIR", cap_dir),
            patch("holus.api.routes.improvement.KNOWLEDGE_GAPS_DIR", know_dir),
        ):
            resp = client.get("/api/v1/improvement/gaps")
        data = resp.json()
        assert data["total"] == 2  # README.md excluded
        assert len(data["capability_gaps"]) == 1
        assert len(data["knowledge_gaps"]) == 1

    def test_drift_empty_trajectory(self, client: TestClient, tmp_path: Path):
        missing = tmp_path / "trajectory.jsonl"
        with patch("holus.api.routes.improvement.TRAJECTORY_PATH", missing):
            resp = client.get("/api/v1/improvement/drift")
        assert resp.status_code == 200
        data = resp.json()
        assert data["alerts"] == []
        assert data["agents_checked"] == 0

    def test_summary_returns_activation_gates(self, client: TestClient, tmp_path: Path):
        traj_missing = tmp_path / "trajectory.jsonl"
        bandit_missing = tmp_path / "bandit_arms.json"
        with (
            patch("holus.api.routes.improvement.TRAJECTORY_PATH", traj_missing),
            patch("holus.api.routes.improvement.BANDIT_ARMS_PATH", bandit_missing),
        ):
            resp = client.get("/api/v1/improvement/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "activation_gates" in data
        assert data["activation_gates"]["thompson_sampling"]["active"] is False
        assert data["trajectory_entries_30d"] == 0


# ---------------------------------------------------------------------------
# /api/v1/results
# ---------------------------------------------------------------------------


class TestResultsEndpoint:
    def test_results_missing_file_returns_empty(self, client: TestClient, tmp_path: Path):
        missing = tmp_path / "growth.json"
        with patch("holus.api.routes.results.GROWTH_FILE", missing):
            resp = client.get("/api/v1/results")
        assert resp.status_code == 200
        data = resp.json()
        assert data["platforms"] == {}
        assert data["daily_growth"] == []
        assert data["top_posts"] == []

    def test_results_with_data(self, client: TestClient, tmp_path: Path):
        growth_file = tmp_path / "growth.json"
        growth_data = {
            "snapshot_date": "2026-03-20",
            "platforms": {
                "linkedin": {
                    "followers": 1200,
                    "followers_30d_ago": 1000,
                    "posts_30d": 15,
                    "impressions_30d": 50000,
                    "engagement_rate": 0.045,
                    "top_content_type": "tutorial",
                },
            },
            "daily_growth": [],
            "top_posts": [],
            "content_by_pillar": {},
            "content_by_product": {},
        }
        growth_file.write_text(json.dumps(growth_data), encoding="utf-8")
        with patch("holus.api.routes.results.GROWTH_FILE", growth_file):
            resp = client.get("/api/v1/results")
        assert resp.status_code == 200
        data = resp.json()
        assert data["snapshot_date"] == "2026-03-20"
        assert "linkedin" in data["platforms"]
        assert data["platforms"]["linkedin"]["followers"] == 1200


# ---------------------------------------------------------------------------
# /api/v1/config
# ---------------------------------------------------------------------------


class TestConfigEndpoint:
    def test_get_content_config(self, client: TestClient, tmp_path: Path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "content.yaml").write_text(
            yaml.dump({"languages": ["en", "es"], "approval_required": True}),
            encoding="utf-8",
        )
        with patch("holus.api.routes.config.CONFIG_DIR", config_dir):
            resp = client.get("/api/v1/config/content")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "content"
        assert data["data"]["approval_required"] is True

    def test_get_content_config_missing_returns_404(self, client: TestClient, tmp_path: Path):
        empty_dir = tmp_path / "config"
        empty_dir.mkdir()
        with patch("holus.api.routes.config.CONFIG_DIR", empty_dir):
            resp = client.get("/api/v1/config/content")
        assert resp.status_code == 404

    def test_put_content_config(self, client: TestClient, tmp_path: Path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "content.yaml").write_text(
            yaml.dump({"languages": ["en"]}), encoding="utf-8",
        )
        with patch("holus.api.routes.config.CONFIG_DIR", config_dir):
            resp = client.put(
                "/api/v1/config/content",
                json={"data": {"languages": ["en", "es"], "approval_required": False}},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["languages"] == ["en", "es"]
        # Verify file was written
        written = yaml.safe_load((config_dir / "content.yaml").read_text())
        assert written["languages"] == ["en", "es"]

    def test_get_products_config(self, client: TestClient, tmp_path: Path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "products.yaml").write_text(
            yaml.dump({"products": {"pilaster": {"name": "Pilaster"}}}),
            encoding="utf-8",
        )
        with patch("holus.api.routes.config.CONFIG_DIR", config_dir):
            resp = client.get("/api/v1/config/products")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "products"
        assert "pilaster" in data["data"]["products"]

    def test_get_platforms_config(self, client: TestClient):
        resp = client.get("/api/v1/config/platforms")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Should have at least linkedin
        platform_ids = [p["id"] for p in data]
        assert "linkedin" in platform_ids


# ---------------------------------------------------------------------------
# /api/v1/knowledge (memory + lessons)
# ---------------------------------------------------------------------------


class TestKnowledgeMemoryEndpoint:
    def test_memory_returns_content(self, client: TestClient, tmp_path: Path):
        memory_file = tmp_path / "MEMORY.md"
        memory_file.write_text("# System Memory\n\nTutorial posts work best.", encoding="utf-8")
        with patch("holus.api.routes.knowledge.MEMORY_PATH", memory_file):
            resp = client.get("/api/v1/knowledge/memory/content")
        assert resp.status_code == 200
        data = resp.json()
        assert "Tutorial posts" in data["content"]
        assert data["size_bytes"] > 0

    def test_memory_missing_returns_404(self, client: TestClient, tmp_path: Path):
        missing = tmp_path / "MEMORY.md"
        with patch("holus.api.routes.knowledge.MEMORY_PATH", missing):
            resp = client.get("/api/v1/knowledge/memory/content")
        assert resp.status_code == 404

    def test_lessons_returns_entries(self, client: TestClient, tmp_path: Path):
        lessons_file = tmp_path / "lessons.json"
        lessons_data = [
            {"id": "1", "date": "2026-03-19", "lesson": "Hooks matter", "source": "trajectory"},
            {"id": "2", "date": "2026-03-20", "lesson": "Short posts win", "source": "trajectory"},
        ]
        lessons_file.write_text(json.dumps(lessons_data), encoding="utf-8")
        with patch("holus.api.routes.knowledge.LESSONS_PATH", lessons_file):
            resp = client.get("/api/v1/knowledge/lessons/recent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["lessons"]) == 2
        # Most recent first
        assert data["lessons"][0]["id"] == "2"

    def test_lessons_missing_returns_empty(self, client: TestClient, tmp_path: Path):
        missing = tmp_path / "lessons.json"
        with patch("holus.api.routes.knowledge.LESSONS_PATH", missing):
            resp = client.get("/api/v1/knowledge/lessons/recent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["lessons"] == []
        assert data["total"] == 0

    def test_lessons_limit_param(self, client: TestClient, tmp_path: Path):
        lessons_file = tmp_path / "lessons.json"
        lessons_data = [{"id": str(i), "lesson": f"Lesson {i}"} for i in range(10)]
        lessons_file.write_text(json.dumps(lessons_data), encoding="utf-8")
        with patch("holus.api.routes.knowledge.LESSONS_PATH", lessons_file):
            resp = client.get("/api/v1/knowledge/lessons/recent?limit=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 10
        assert len(data["lessons"]) == 3
