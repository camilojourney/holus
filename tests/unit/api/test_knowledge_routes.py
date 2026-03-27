"""Tests for GET /api/v1/knowledge routes."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient


def _setup(tmp_path, monkeypatch):
    """Create temp directory structure and monkeypatch knowledge paths."""
    knowledge_dir = tmp_path / "knowledge" / "current"
    knowledge_dir.mkdir(parents=True)
    memory_path = tmp_path / "MEMORY.md"
    lessons_path = tmp_path / "lessons.json"

    import holus.api.routes.knowledge as knowledge_mod

    monkeypatch.setattr(knowledge_mod, "KNOWLEDGE_DIR", knowledge_dir)
    monkeypatch.setattr(knowledge_mod, "MEMORY_PATH", memory_path)
    monkeypatch.setattr(knowledge_mod, "LESSONS_PATH", lessons_path)

    return {
        "knowledge_dir": knowledge_dir,
        "memory": memory_path,
        "lessons": lessons_path,
    }


def test_list_knowledge(tmp_path, monkeypatch):
    paths = _setup(tmp_path, monkeypatch)

    (paths["knowledge_dir"] / "audience.md").write_text("# Audience\nDevelopers and creators")
    (paths["knowledge_dir"] / "strategy.md").write_text("# Strategy\nAuthority-first")

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/knowledge")
    assert resp.status_code == 200
    data = resp.json()
    filenames = {f["filename"] for f in data["files"]}
    assert filenames == {"audience.md", "strategy.md"}
    # Content should NOT be included in list view
    for f in data["files"]:
        assert f["content"] is None
        assert f["size_bytes"] > 0


def test_list_knowledge_empty(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/knowledge")
    assert resp.status_code == 200
    assert resp.json()["files"] == []


def test_get_memory_content(tmp_path, monkeypatch):
    paths = _setup(tmp_path, monkeypatch)
    paths["memory"].write_text("# Memory\n\nHook posts outperform promo posts 4:1")

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/knowledge/memory/content")
    assert resp.status_code == 200
    data = resp.json()
    assert "Hook posts outperform" in data["content"]
    assert data["size_bytes"] > 0
    assert data["last_modified"] is not None


def test_get_memory_content_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/knowledge/memory/content")
    assert resp.status_code == 404


def test_get_lessons_with_list_format(tmp_path, monkeypatch):
    paths = _setup(tmp_path, monkeypatch)
    lessons = [
        {
            "id": "1",
            "date": "2026-03-01",
            "lesson": "Tutorials convert better",
            "source": "analytics",
            "agent_id": "strategist",
        },
        {
            "id": "2",
            "date": "2026-03-02",
            "lesson": "LinkedIn > Instagram for devs",
            "source": "analytics",
        },
        {
            "id": "3",
            "date": "2026-03-03",
            "lesson": "Hooks with questions get 2x engagement",
            "category": "copywriting",
        },
    ]
    paths["lessons"].write_text(json.dumps(lessons))

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/knowledge/lessons/recent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["lessons"]) == 3
    # Newest first
    assert data["lessons"][0]["id"] == "3"
    assert data["lessons"][2]["id"] == "1"


def test_get_lessons_with_dict_format(tmp_path, monkeypatch):
    """lessons.json can be a dict with a 'lessons' key."""
    paths = _setup(tmp_path, monkeypatch)
    paths["lessons"].write_text(
        json.dumps(
            {
                "lessons": [
                    {"id": "a", "lesson": "First lesson"},
                    {"id": "b", "lesson": "Second lesson"},
                ]
            }
        )
    )

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/knowledge/lessons/recent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


def test_get_lessons_missing_file(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/knowledge/lessons/recent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["lessons"] == []
    assert data["total"] == 0


def test_get_lessons_with_limit(tmp_path, monkeypatch):
    paths = _setup(tmp_path, monkeypatch)
    lessons = [{"id": str(i), "lesson": f"Lesson {i}"} for i in range(10)]
    paths["lessons"].write_text(json.dumps(lessons))

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/knowledge/lessons/recent?limit=3")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 10
    assert len(data["lessons"]) == 3
