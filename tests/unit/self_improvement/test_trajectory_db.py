"""Tests for SQLite trajectory database."""

import json

import pytest

from holus.self_improvement.trajectory_db import TrajectoryDB


@pytest.fixture
def db(tmp_path):
    d = TrajectoryDB(db_path=tmp_path / "test.db")
    yield d
    d.close()


class TestTrajectoryDB:
    def test_insert_and_query(self, db):
        db.insert({
            "timestamp": "2026-03-17T00:00:00Z",
            "agent_id": "idea-runner",
            "task_type": "carousel",
            "status": "success",
            "judge_score": 0.85,
            "metadata": {"platform": "linkedin", "content_type": "carousel"},
        })
        results = db.query(agent_id="idea-runner")
        assert len(results) == 1
        assert results[0]["judge_score"] == 0.85

    def test_query_by_platform(self, db):
        db.insert({"agent_id": "a", "metadata": {"platform": "linkedin"}, "timestamp": "2026-03-17T00:00:00Z"})
        db.insert({"agent_id": "a", "metadata": {"platform": "twitter"}, "timestamp": "2026-03-17T00:00:00Z"})
        results = db.query(platform="linkedin")
        assert len(results) == 1

    def test_query_min_score(self, db):
        db.insert({"agent_id": "a", "judge_score": 0.9, "metadata": {}, "timestamp": "2026-03-17T00:00:00Z"})
        db.insert({"agent_id": "a", "judge_score": 0.3, "metadata": {}, "timestamp": "2026-03-17T00:00:00Z"})
        results = db.query(min_score=0.8)
        assert len(results) == 1

    def test_migrate_from_jsonl(self, db, tmp_path):
        jsonl = tmp_path / "trajectory.jsonl"
        entries = [
            {"timestamp": "2026-03-17T00:00:00Z", "agent_id": "test", "judge_score": 0.8, "metadata": {"platform": "linkedin"}},
            {"timestamp": "2026-03-17T01:00:00Z", "agent_id": "test", "judge_score": 0.6, "metadata": {"platform": "twitter"}},
        ]
        with open(jsonl, "w") as fh:
            for e in entries:
                fh.write(json.dumps(e) + "\n")

        count = db.migrate_from_jsonl(jsonl)
        assert count == 2
        assert db.count() == 2

    def test_aggregate_by_platform(self, db):
        for score in [0.8, 0.9, 0.7]:
            db.insert({"agent_id": "a", "judge_score": score, "metadata": {"platform": "linkedin"}, "timestamp": "2026-03-17T00:00:00Z"})
        db.insert({"agent_id": "a", "judge_score": 0.5, "metadata": {"platform": "twitter"}, "timestamp": "2026-03-17T00:00:00Z"})

        agg = db.aggregate_by_platform(days=30)
        assert len(agg) == 2
        linkedin = next(a for a in agg if a["platform"] == "linkedin")
        assert abs(linkedin["avg_judge"] - 0.8) < 0.01

    def test_count(self, db):
        assert db.count() == 0
        db.insert({"agent_id": "a", "metadata": {}, "timestamp": "2026-03-17T00:00:00Z"})
        assert db.count() == 1
