"""Tests for content API routes (src/holus/api/routes/content.py).

Covers:
- GET /api/v1/content - list content items with status counts
- GET /api/v1/content - empty when no queue files
- GET /api/v1/content/{id} - full detail for a piece
- GET /api/v1/content/{id} - 404 for missing piece
- PATCH /api/v1/content/{id} - approve a content piece
- PATCH /api/v1/content/{id} - reject a content piece
- GET /api/v1/content/{id}/image - serve rendered PNG
- GET /api/v1/content/{id}/pdf - serve rendered carousel PDF
- PATCH /api/v1/content/{id}/visual-choice - choose A/B variant
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

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
    img_path = content_queue_dir.parent / "rendered-content" / "piece-004.png"
    img_path.parent.mkdir(parents=True, exist_ok=True)
    # Minimal PNG: 8-byte signature
    img_path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
        + b"\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
        + b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
        + b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    img_b_path = content_queue_dir.parent / "rendered-content" / "piece-004-b.png"
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


@pytest.fixture
def piece_with_pdf(content_queue_dir: Path, tmp_path: Path) -> tuple[Path, Path]:
    """Write a carousel content piece that references a rendered PDF."""
    pdf_path = content_queue_dir.parent / "rendered-content" / "piece-005.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(b"%PDF-1.4\n% Holus test carousel\n")

    data = {
        "piece_id": "piece-005",
        "topic": "Workflow carousel",
        "content_type": "carousel_outline",
        "platform": "linkedin",
        "status": "pending_review",
        "text": "Slide 1: the workflow is the product.",
        "rendered_pdf_path": str(pdf_path),
        "visual_spec": {"format": "pdf", "renderer": "holus/visual-renderer"},
    }
    p = content_queue_dir / "piece-005.yaml"
    p.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    return p, pdf_path


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


class TestCreateContentFromThought:
    """POST /api/v1/content/from-thought."""

    def test_create_from_thought_renders_visual_previews(self, client, content_queue_dir):
        """Instagram image and LinkedIn carousel drafts get rendered assets."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.post(
                "/api/v1/content/from-thought",
                json={
                    "thought": "Holus should turn one honest founder thought into native social content.",
                    "platforms": [
                        "linkedin_text",
                        "instagram_image",
                        "linkedin_carousel",
                        "instagram_carousel",
                    ],
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 4

        ids_by_platform_type = {
            (item["platform"], item["content_type"]): item["id"] for item in data["items"]
        }
        assert set(ids_by_platform_type) == {
            ("linkedin", "text_post"),
            ("instagram", "image_caption"),
            ("linkedin", "carousel_outline"),
            ("instagram", "carousel_outline"),
        }

        with _patch_queue_dir(content_queue_dir):
            image_detail = client.get(
                f"/api/v1/content/{ids_by_platform_type[('instagram', 'image_caption')]}"
            ).json()
            carousel_detail = client.get(
                f"/api/v1/content/{ids_by_platform_type[('linkedin', 'carousel_outline')]}"
            ).json()
            instagram_carousel_detail = client.get(
                f"/api/v1/content/{ids_by_platform_type[('instagram', 'carousel_outline')]}"
            ).json()
            linkedin_detail = client.get(
                f"/api/v1/content/{ids_by_platform_type[('linkedin', 'text_post')]}"
            ).json()

        assert image_detail["image_url"].endswith("/image")
        assert image_detail["posting_destination"]["platform"] == "instagram"
        assert image_detail["posting_destination"]["handle"] == "@camiloexperience"
        assert image_detail["posting_destination"]["approval_required"] is True
        assert carousel_detail["visual_spec"]["format"] == "pdf"
        assert image_detail["visual_spec"]["renderer"] in {
            "holus/visual-renderer",
            "holus/local-preview",
        }
        assert image_detail["visual_spec"]["style_profile"]["profile_id"]
        assert image_detail["visual_spec"]["style_profile"]["visual_type"]
        assert image_detail["visual_spec"]["style_profile"]["theme"]
        image_prompt = image_detail["visual_spec"]["prompt_contract"]
        assert {
            "purpose",
            "subject",
            "action",
            "setting",
            "composition",
            "camera_angle",
            "style",
            "palette",
            "lighting",
            "mood",
            "typography",
            "text_placement",
            "variation_seed",
        }.issubset(image_prompt)
        assert len(image_prompt["variation_seed"]) == 12
        creative_contract = image_detail["visual_spec"]["creative_contract"]
        assert {
            "platform_format",
            "aspect_ratio",
            "safe_zone",
            "content_job",
            "hook_pattern",
            "layout_archetype",
            "typography_hierarchy",
            "density",
            "visual_metaphor",
            "reader_action",
            "rhythm",
            "freshness_axis",
        }.issubset(creative_contract)
        assert carousel_detail["visual_spec"]["style_profile"]["profile_id"]
        assert carousel_detail["visual_spec"]["prompt_contract"]["composition"]
        assert len(carousel_detail["visual_spec"]["carousel_slides"]) == 5
        assert carousel_detail["pdf_url"].endswith("/pdf")
        assert carousel_detail["visual_spec"]["platform_export"] == "linkedin_document_pdf"
        assert instagram_carousel_detail["visual_spec"]["platform_export"] == (
            "instagram_multi_image_carousel"
        )
        assert instagram_carousel_detail["pdf_url"].endswith("/pdf")
        assert linkedin_detail["thought_essence"]["thesis"]
        assert linkedin_detail["image_url"] is None
        assert image_detail["source_type"] == "text"
        assert [step["agent_id"] for step in image_detail["agent_trace"]] == [
            "idea-injector",
            "context-builder",
            "idea-planner",
            "visual-designer",
            "brand-designer",
            "platform-adapter",
            "voice-guardian",
        ]

        with _patch_queue_dir(content_queue_dir):
            image_resp = client.get(
                f"/api/v1/content/{ids_by_platform_type[('instagram', 'image_caption')]}/image"
            )

        assert image_resp.status_code == 200
        assert image_resp.headers["content-type"] == "image/png"

    def test_create_from_thought_rejects_unsupported_channel(self, client, content_queue_dir):
        """Unsupported platform channels return 400 instead of being ignored."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.post(
                "/api/v1/content/from-thought",
                json={
                    "thought": "This should not silently drop the requested platform.",
                    "platforms": ["linkedin_text", "unknown_channel"],
                },
            )

        assert resp.status_code == 400
        assert "unknown_channel" in resp.json()["detail"]

    def test_create_from_url_stores_source_metadata(self, client, content_queue_dir):
        """URL thoughts extract source text and keep URL metadata on every variant."""
        with (
            _patch_queue_dir(content_queue_dir),
            patch(
                "holus.agents.marketing.thought_pipeline.ThoughtContentPipeline._extract_from_url",
                new=AsyncMock(
                    return_value="A public thought about turning one source into native content."
                ),
            ),
        ):
            resp = client.post(
                "/api/v1/content/from-thought",
                json={
                    "thought": "",
                    "source_type": "url",
                    "source_url": "https://example.com/thought",
                    "platforms": ["linkedin_text", "instagram_image"],
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2

        records = [
            yaml.safe_load(path.read_text(encoding="utf-8"))
            for path in sorted(content_queue_dir.glob("*.yaml"))
        ]
        assert len({record["group_id"] for record in records}) == 1
        assert {record["source_type"] for record in records} == {"url"}
        assert {record["source_url"] for record in records} == {"https://example.com/thought"}
        assert all("public thought" in record["topic"] for record in records)


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
        assert data["posting_destination"]["platform"] == "linkedin"
        assert data["posting_destination"]["handle"] == "@camiloexperience"
        assert data["posting_destination"]["approval_required"] is True

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

    def test_get_content_detail_includes_pdf_url(self, client, content_queue_dir, piece_with_pdf):
        """Carousel details expose a PDF URL for the review UI."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.get("/api/v1/content/piece-005")

        assert resp.status_code == 200
        data = resp.json()
        assert data["image_url"] is None
        assert data["pdf_url"] == "/api/v1/content/piece-005/pdf"


class TestPatchContent:
    """PATCH /api/v1/content/{piece_id}."""

    def test_patch_content_approve(self, client, content_queue_dir, sample_yaml_piece):
        """Approving updates the YAML file without publishing."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.patch(
                "/api/v1/content/piece-001",
                json={"status": "approved"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"

        # Verify YAML file was updated on disk
        updated = yaml.safe_load(sample_yaml_piece.read_text(encoding="utf-8"))
        assert updated["status"] == "approved"
        assert "post_id" not in updated

    def test_patch_content_reject(self, client, content_queue_dir, sample_yaml_piece):
        """Rejecting updates the file without publishing."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.patch(
                "/api/v1/content/piece-001",
                json={"status": "rejected"},
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

        updated = yaml.safe_load(sample_yaml_piece.read_text(encoding="utf-8"))
        assert updated["status"] == "rejected"

    def test_patch_content_json_file(self, client, content_queue_dir, sample_json_piece):
        """Patching a JSON-backed piece writes JSON correctly."""
        with _patch_queue_dir(content_queue_dir):
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


class TestPublishAndScheduleContent:
    """Explicit Holus Social API publish/schedule endpoints."""

    def test_publish_dry_run_uses_platforms_payload(
        self, client, content_queue_dir, sample_yaml_piece
    ):
        """Dry-run publish returns the payload and does not update the queue file."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.post("/api/v1/content/piece-001/publish", json={"dry_run": True})

        assert resp.status_code == 200
        data = resp.json()
        assert data["dry_run"] is True
        assert data["payload"]["platforms"] == ["linkedin"]
        assert "targets" not in data["payload"]
        assert data["status"] == "dry_run"

        updated = yaml.safe_load(sample_yaml_piece.read_text(encoding="utf-8"))
        assert updated["status"] == "pending_review"
        assert "post_id" not in updated

    def test_schedule_dry_run_stores_no_local_status(
        self, client, content_queue_dir, sample_yaml_piece
    ):
        """Dry-run schedule returns the payload without changing local review state."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.post(
                "/api/v1/content/piece-001/schedule",
                json={"scheduled_at": "2026-04-01T12:00:00Z", "dry_run": True},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["dry_run"] is True
        assert data["payload"]["platforms"] == ["linkedin"]
        assert data["payload"]["scheduled_at"] == "2026-04-01T12:00:00Z"
        assert data["status"] == "dry_run"

        updated = yaml.safe_load(sample_yaml_piece.read_text(encoding="utf-8"))
        assert updated["status"] == "pending_review"
        assert updated["scheduled_at"] == "2026-03-25T14:00:00Z"

    def test_p0_publish_external_delivery_is_contained_without_success_state(
        self, client, content_queue_dir, sample_yaml_piece
    ):
        with _patch_queue_dir(content_queue_dir):
            approved = client.patch("/api/v1/content/piece-001", json={"status": "approved"})
            revision = approved.json()["revision"]
            resp = client.post(
                "/api/v1/content/piece-001/publish",
                json={"expected_revision": revision},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "contained"
        assert data["publish_id"] is None

        updated = yaml.safe_load(sample_yaml_piece.read_text(encoding="utf-8"))
        assert updated["status"] == "approved"
        assert updated["dispatch_request_id"]
        assert "post_id" not in updated
        assert "published_at" not in updated

    def test_p0_schedule_external_delivery_is_contained_without_scheduled_state(
        self, client, content_queue_dir, sample_yaml_piece
    ):
        with _patch_queue_dir(content_queue_dir):
            approved = client.patch("/api/v1/content/piece-001", json={"status": "approved"})
            revision = approved.json()["revision"]
            resp = client.post(
                "/api/v1/content/piece-001/schedule",
                json={
                    "scheduled_at": "2026-04-01T12:00:00Z",
                    "expected_revision": revision,
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "contained"
        assert data["schedule_id"] is None

        updated = yaml.safe_load(sample_yaml_piece.read_text(encoding="utf-8"))
        assert updated["status"] == "approved"
        assert updated["dispatch_request_id"]
        assert "schedule_id" not in updated
        assert updated.get("schedule_status") == "contained"


class TestDispatchGuards:
    """External dispatch must never bypass the Phase-1 human approval gate."""

    def test_pending_review_publish_and_schedule_are_rejected_without_client(
        self, client, content_queue_dir, sample_yaml_piece
    ):
        with _patch_queue_dir(content_queue_dir):
            publish = client.post(
                "/api/v1/content/piece-001/publish", json={"expected_revision": "stale"}
            )
            schedule = client.post(
                "/api/v1/content/piece-001/schedule",
                json={"scheduled_at": "2026-04-01T12:00:00Z", "expected_revision": "stale"},
            )
        assert publish.status_code == 409
        assert publish.json()["detail"] == "APPROVAL_REQUIRED"
        assert schedule.status_code == 409
        assert schedule.json()["detail"] == "APPROVAL_REQUIRED"
        raw = yaml.safe_load(sample_yaml_piece.read_text(encoding="utf-8"))
        assert raw["status"] == "pending_review"
        assert "dispatch_request_id" not in raw

    def test_approved_dispatch_requires_exact_revision(
        self, client, content_queue_dir, sample_yaml_piece
    ):
        with _patch_queue_dir(content_queue_dir):
            approved = client.patch("/api/v1/content/piece-001", json={"status": "approved"})
            assert approved.status_code == 200
            response = client.post(
                "/api/v1/content/piece-001/publish", json={"expected_revision": "wrong"}
            )
        assert response.status_code == 409
        assert response.json()["detail"] == "REVISION_CONFLICT"


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

    def test_content_image_rejects_path_outside_rendered_roots(
        self, client, content_queue_dir, sample_yaml_piece, tmp_path
    ):
        outside = tmp_path / "outside.png"
        outside.write_bytes(b"not a real image")
        raw = yaml.safe_load(sample_yaml_piece.read_text(encoding="utf-8"))
        raw["rendered_image_path"] = str(outside)
        sample_yaml_piece.write_text(yaml.safe_dump(raw), encoding="utf-8")
        with _patch_queue_dir(content_queue_dir):
            response = client.get("/api/v1/content/piece-001/image")
        assert response.status_code == 404

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


class TestContentPdf:
    """GET /api/v1/content/{piece_id}/pdf."""

    def test_content_pdf(self, client, content_queue_dir, piece_with_pdf):
        """Serves the rendered carousel PDF for a content piece."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.get("/api/v1/content/piece-005/pdf")

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert "inline" in resp.headers["content-disposition"]
        assert resp.content.startswith(b"%PDF-")

    def test_content_pdf_not_found_piece(self, client, content_queue_dir):
        """Returns 404 when piece does not exist."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.get("/api/v1/content/nonexistent/pdf")
        assert resp.status_code == 404

    def test_content_pdf_no_carousel(self, client, content_queue_dir, sample_yaml_piece):
        """Returns 404 when piece exists but has no rendered PDF."""
        with _patch_queue_dir(content_queue_dir):
            resp = client.get("/api/v1/content/piece-001/pdf")
        assert resp.status_code == 404
        assert "no carousel pdf" in resp.json()["detail"].lower()


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
