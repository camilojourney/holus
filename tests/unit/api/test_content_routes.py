"""Tests for content API routes (src/holus/api/routes/content.py).

Covers:
- GET /api/v1/content — list content items with status counts
- GET /api/v1/content — empty when no queue files
- GET /api/v1/content/{id} — full detail for a piece
- GET /api/v1/content/{id} — 404 for missing piece
- PATCH /api/v1/content/{id} — approve a content piece
- PATCH /api/v1/content/{id} — reject a content piece
- GET /api/v1/content/{id}/image — serve rendered PNG
- PATCH /api/v1/content/{id}/visual-choice — choose A/B variant
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from pathlib import Path

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
def content_queue_dir(tmp_path: Path) -> Path:
    """Create a temporary content-queue directory."""
    d = tmp_path / "data" / "content-queue"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def sample_yaml_piece(content_queue_dir: Path) -> Path:
    """Write a sample YAML content piece."""
    data = {
        "piece_id": "piece-001",
        "topic": "How to use Pilaster for AI art",
        "content_type": "tutorial",
        "platform": "linkedin",
        "content_pillar": "education",
        "status": "pending_review",
        "generated_at": "2026-03-20T10:00:00Z",
        "scheduled_at": "2026-03-25T14:00:00Z",
        "agent_id": "marketing-strategist",
        "idea_source": "analytics",
        "text": "Here is how you use Pilaster to create amazing AI art...",
        "hashtags": ["#AI", "#art", "#pilaster"],
        "char_count": 280,
        "quality": {
            "hook_score": "8/10",
            "voice_check": "pass",
            "quality_score": 85,
            "violations": [],
        },
        "agent_trace": [
            {
                "agent_id": "marketing-strategist",
                "model": "claude-opus",
                "role": "strategist",
                "at": "2026-03-20T09:55:00Z",
                "quality_score": "85",
                "verdict": "approved",
            }
        ],
        "judge_score": 8.5,
        "judge_verdict": "publish",
    }
    p = content_queue_dir / "piece-001.yaml"
    p.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    return p


@pytest.fixture
def sample_json_piece(content_queue_dir: Path) -> Path:
    """Write a sample JSON content piece."""
    data = {
        "piece_id": "piece-002",
        "topic": "Genpeli demo reel",
        "content_type": "demo",
        "platform": "tiktok",
        "status": "draft",
        "generated_at": "2026-03-21T08:00:00Z",
        "agent_id": "hook-architect",
        "text": "Watch this genpeli magic...",
        "hashtags": ["#genpeli", "#video"],
        "char_count": 120,
    }
    p = content_queue_dir / "piece-002.json"
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return p


@pytest.fixture
def sample_rejected_piece(content_queue_dir: Path) -> Path:
    """Write a rejected content piece."""
    data = {
        "piece_id": "piece-003",
        "topic": "Bad post",
        "content_type": "text_post",
        "platform": "linkedin",
        "status": "rejected",
        "text": "This was rejected.",
    }
    p = content_queue_dir / "piece-003.yaml"
    p.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    return p


@pytest.fixture
def piece_with_image(content_queue_dir: Path, tmp_path: Path) -> tuple[Path, Path]:
    """Write a content piece that references a rendered image."""
    # Create a fake PNG (minimal valid header)
    img_path = tmp_path / "rendered" / "piece-004.png"
    img_path.parent.mkdir(parents=True, exist_ok=True)
    # Minimal PNG: 8-byte signature
    img_path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
        + b"\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
        + b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
        + b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    img_b_path = tmp_path / "rendered" / "piece-004-b.png"
    img_b_path.write_bytes(img_path.read_bytes())

    data = {
        "piece_id": "piece-004",
        "topic": "Visual post",
        "content_type": "carousel",
        "platform": "linkedin",
        "status": "pending_review",
        "text": "Check out this visual.",
        "rendered_image_path": str(img_path),
        "rendered_image_b_path": str(img_b_path),
        "visual_spec": {"style": "minimalist", "colors": ["#000", "#fff"]},
        "visual_spec_b": {"style": "bold", "colors": ["#f00", "#00f"]},
    }
    p = content_queue_dir / "piece-004.yaml"
    p.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    return p, img_path


def _patch_queue_dir(content_queue_dir: Path):
    """Return a patch context manager for CONTENT_QUEUE_DIR."""
    return patch("holus.api.routes.content.CONTENT_QUEUE_DIR", content_queue_dir)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestListContent:
    """GET /api/v1/content."""

    def test_list_content(
        self, client, content_queue_dir, sample_yaml_piece, sample_json_piece, sample_rejected_piece
    ):
        """Returns content items with correct status counts."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.get("/api/v1/content")

        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "counts" in data
        assert len(data["items"]) == 3

        ids = {item["id"] for item in data["items"]}
        assert ids == {"piece-001", "piece-002", "piece-003"}

        counts = data["counts"]
        assert counts["draft"] == 1  # piece-002
        assert counts["review"] == 1  # piece-001 (pending_review)
        assert counts["rejected"] == 1  # piece-003
        assert counts["published"] == 0

    def test_list_content_empty(self, client, content_queue_dir):
        """Returns empty items and zero counts when no queue files."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.get("/api/v1/content")

        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["counts"] == {"draft": 0, "review": 0, "published": 0, "rejected": 0}

    def test_list_content_no_queue_dir(self, client, tmp_path):
        """Returns empty when content-queue directory does not exist."""
        nonexistent = tmp_path / "does-not-exist"
        with patch("holus.api.routes.content.CONTENT_QUEUE_DIR", nonexistent):
            resp = client.get("/api/v1/content")

        assert resp.status_code == 200
        assert resp.json()["items"] == []


class TestGetContentDetail:
    """GET /api/v1/content/{piece_id}."""

    def test_get_content_detail(self, client, content_queue_dir, sample_yaml_piece):
        """Returns full detail including text, trace, and quality."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.get("/api/v1/content/piece-001")

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "piece-001"
        assert data["title"] == "How to use Pilaster for AI art"
        assert data["content_type"] == "tutorial"
        assert data["platform"] == "linkedin"
        assert data["status"] == "pending_review"
        assert "Here is how you use Pilaster" in data["text"]
        assert data["hashtags"] == ["#AI", "#art", "#pilaster"]
        assert data["char_count"] == 280
        assert data["judge_score"] == 8.5
        assert data["judge_verdict"] == "publish"

        # Quality block
        assert data["quality"]["hook_score"] == "8/10"
        assert data["quality"]["quality_score"] == 85

        # Agent trace
        assert len(data["agent_trace"]) == 1
        assert data["agent_trace"][0]["agent_id"] == "marketing-strategist"

    def test_get_content_not_found(self, client, content_queue_dir):
        """Returns 404 for a non-existent piece ID."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.get("/api/v1/content/nonexistent-id")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_get_content_by_file_stem(self, client, content_queue_dir, sample_yaml_piece):
        """Can look up a piece by file stem when piece_id matches."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.get("/api/v1/content/piece-001")
        assert resp.status_code == 200


class TestPatchContent:
    """PATCH /api/v1/content/{piece_id}."""

    def test_patch_content_approve(self, client, content_queue_dir, sample_yaml_piece):
        """Approving updates the YAML file and returns the updated detail."""
        with (
            _patch_queue_dir(content_queue_dir),
            patch("holus.api.routes.content._attempt_post") as mock_post,
        ):
            resp = client.patch(
                "/api/v1/content/piece-001",
                json={"status": "approved"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"

        # Verify _attempt_post was called
        mock_post.assert_called_once()

        # Verify YAML file was updated on disk
        updated = yaml.safe_load(sample_yaml_piece.read_text(encoding="utf-8"))
        assert updated["status"] == "approved"

    def test_patch_content_reject(self, client, content_queue_dir, sample_yaml_piece):
        """Rejecting updates the file; does NOT call _attempt_post."""
        with (
            _patch_queue_dir(content_queue_dir),
            patch("holus.api.routes.content._attempt_post") as mock_post,
        ):
            resp = client.patch(
                "/api/v1/content/piece-001",
                json={"status": "rejected"},
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"
        mock_post.assert_not_called()

        updated = yaml.safe_load(sample_yaml_piece.read_text(encoding="utf-8"))
        assert updated["status"] == "rejected"

    def test_patch_content_json_file(self, client, content_queue_dir, sample_json_piece):
        """Patching a JSON-backed piece writes JSON correctly."""
        with _patch_queue_dir(content_queue_dir), patch("holus.api.routes.content._attempt_post"):
            resp = client.patch(
                "/api/v1/content/piece-002",
                json={"status": "approved"},
            )

        assert resp.status_code == 200
        updated = json.loads(sample_json_piece.read_text(encoding="utf-8"))
        assert updated["status"] == "approved"

    def test_patch_content_not_found(self, client, content_queue_dir):
        """PATCH returns 404 for a non-existent piece."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.patch(
                "/api/v1/content/nonexistent",
                json={"status": "approved"},
            )
        assert resp.status_code == 404

    def test_patch_content_reschedule(self, client, content_queue_dir, sample_yaml_piece):
        """Can update scheduled_at without changing status."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.patch(
                "/api/v1/content/piece-001",
                json={"scheduled_at": "2026-04-01T12:00:00Z"},
            )

        assert resp.status_code == 200
        updated = yaml.safe_load(sample_yaml_piece.read_text(encoding="utf-8"))
        assert updated["scheduled_at"] == "2026-04-01T12:00:00Z"


class TestContentImage:
    """GET /api/v1/content/{piece_id}/image."""

    def test_content_image(self, client, content_queue_dir, piece_with_image):
        """Serves the rendered PNG for a content piece."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.get("/api/v1/content/piece-004/image")

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert resp.content[:4] == b"\x89PNG"

    def test_content_image_variant_b(self, client, content_queue_dir, piece_with_image):
        """Serves the B-variant image."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.get("/api/v1/content/piece-004/image?variant=b")

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"

    def test_content_image_not_found_piece(self, client, content_queue_dir):
        """Returns 404 when piece does not exist."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.get("/api/v1/content/nonexistent/image")
        assert resp.status_code == 404

    def test_content_image_no_visual(self, client, content_queue_dir, sample_yaml_piece):
        """Returns 404 when piece exists but has no rendered image."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.get("/api/v1/content/piece-001/image")
        assert resp.status_code == 404
        assert "no visual" in resp.json()["detail"].lower()


class TestVisualChoice:
    """PATCH /api/v1/content/{piece_id}/visual-choice."""

    def test_visual_choice_select_a(self, client, content_queue_dir, piece_with_image):
        """Choosing variant A sets visual_chosen='a'."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.patch("/api/v1/content/piece-004/visual-choice?variant=a")

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "piece-004"

        # Verify file was updated
        yaml_path = content_queue_dir / "piece-004.yaml"
        updated = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert updated["visual_chosen"] == "a"

    def test_visual_choice_select_b(self, client, content_queue_dir, piece_with_image):
        """Choosing variant B swaps rendered_image_path to B's path."""
        yaml_path = content_queue_dir / "piece-004.yaml"
        original = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        b_path = original["rendered_image_b_path"]

        with _patch_queue_dir(content_queue_dir):
            resp = client.patch("/api/v1/content/piece-004/visual-choice?variant=b")

        assert resp.status_code == 200

        updated = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert updated["visual_chosen"] == "b"
        assert updated["rendered_image_path"] == b_path

    def test_visual_choice_not_found(self, client, content_queue_dir):
        """Returns 404 for a non-existent piece."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.patch("/api/v1/content/nonexistent/visual-choice?variant=a")
        assert resp.status_code == 404
