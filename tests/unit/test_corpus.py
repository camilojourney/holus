"""Tests for CorpusDB — SQLite FTS index for LinkedIn post corpus."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from holus.data.corpus import CorpusDB

if TYPE_CHECKING:
    from pathlib import Path


def _make_posts_raw(posts: list[dict], creator_dir: Path) -> None:
    """Write a posts-raw.json file into a creator directory."""
    creator_dir.mkdir(parents=True, exist_ok=True)
    (creator_dir / "posts-raw.json").write_text(
        json.dumps(posts, ensure_ascii=False), encoding="utf-8"
    )


def _sample_post(
    urn: str = "urn:li:post:1",
    text: str = "How to build ComfyUI workflows",
    reactions: int = 50,
    comments: int = 10,
    reposts: int = 5,
    post_type: str = "image+text",
    category: str = "Technical Tutorial",
    images: list[str] | None = None,
    hashtags: list[str] | None = None,
) -> dict:
    return {
        "urn": urn,
        "text": text,
        "reactions": reactions,
        "comments": comments,
        "reposts": reposts,
        "postType": post_type,
        "category": category,
        "images": images or [],
        "hashtags": hashtags or ["#AI", "#ComfyUI"],
        "dateAbsolute": "2026-03-15",
    }


class TestIngestAndSearch:
    """Ingest sample posts and search by keyword."""

    def test_ingest_and_search(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        creator_dir = tmp_path / "ref" / "alice"
        _make_posts_raw(
            [
                _sample_post(urn="p1", text="ComfyUI workflow tutorial for beginners"),
                _sample_post(urn="p2", text="Advanced Stable Diffusion techniques"),
                _sample_post(urn="p3", text="ComfyUI nodes explained step by step"),
            ],
            creator_dir,
        )

        with CorpusDB(db_path) as db:
            count = db.ingest_creator(creator_dir)
            assert count == 3

            results = db.search("ComfyUI")
            assert len(results) == 2
            texts = {r["text"] for r in results}
            assert "ComfyUI workflow tutorial for beginners" in texts
            assert "ComfyUI nodes explained step by step" in texts


class TestTopByEngagement:
    """Verify engagement ranking and filtering."""

    def test_top_by_engagement(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        creator_dir = tmp_path / "ref" / "bob"
        # engagement_total = reactions*1 + comments*3 + reposts*5
        _make_posts_raw(
            [
                _sample_post(urn="low", text="Low engagement", reactions=1, comments=0, reposts=0),
                _sample_post(urn="mid", text="Mid engagement", reactions=10, comments=5, reposts=2),
                _sample_post(
                    urn="high", text="High engagement", reactions=100, comments=50, reposts=20
                ),
            ],
            creator_dir,
        )

        with CorpusDB(db_path) as db:
            db.ingest_creator(creator_dir)
            results = db.top_by_engagement(limit=3)

            assert len(results) == 3
            # Should be sorted descending by engagement_total
            assert results[0]["text"] == "High engagement"
            assert results[1]["text"] == "Mid engagement"
            assert results[2]["text"] == "Low engagement"

            # Verify engagement_total calculation: 100*1 + 50*3 + 20*5 = 350
            assert results[0]["engagement_total"] == 100 + 150 + 100  # 350

    def test_top_by_engagement_with_filter(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        creator_dir = tmp_path / "ref" / "carol"
        _make_posts_raw(
            [
                _sample_post(urn="v1", text="Video post", post_type="video", reactions=100),
                _sample_post(urn="t1", text="Text post", post_type="text", reactions=200),
            ],
            creator_dir,
        )

        with CorpusDB(db_path) as db:
            db.ingest_creator(creator_dir)
            video_only = db.top_by_engagement(visual_type="video")
            assert len(video_only) == 1
            assert video_only[0]["text"] == "Video post"


class TestSearchEmptyDB:
    """Search on empty corpus returns empty list."""

    def test_search_empty_db(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        with CorpusDB(db_path) as db:
            results = db.search("anything")
            assert results == []

    def test_top_by_engagement_empty_db(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        with CorpusDB(db_path) as db:
            results = db.top_by_engagement()
            assert results == []


class TestIngestDuplicate:
    """Ingesting the same post twice doesn't create duplicates."""

    def test_ingest_duplicate(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        creator_dir = tmp_path / "ref" / "dave"
        posts = [_sample_post(urn="dup1", text="Original text", reactions=10)]
        _make_posts_raw(posts, creator_dir)

        with CorpusDB(db_path) as db:
            db.ingest_creator(creator_dir)

            # Update the post text and re-ingest
            posts[0]["text"] = "Updated text"
            posts[0]["reactions"] = 99
            _make_posts_raw(posts, creator_dir)
            db.ingest_creator(creator_dir)

            # Should still be 1 post, with updated data (INSERT OR REPLACE)
            results = db.top_by_engagement(limit=100)
            assert len(results) == 1
            assert results[0]["text"] == "Updated text"
            assert results[0]["reactions"] == 99


class TestSearchRelevance:
    """Verify FTS returns most relevant results first."""

    def test_search_relevance(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        creator_dir = tmp_path / "ref" / "eve"
        _make_posts_raw(
            [
                _sample_post(
                    urn="r1",
                    text="Python Python Python machine learning with Python",
                ),
                _sample_post(
                    urn="r2",
                    text="JavaScript framework comparison",
                ),
                _sample_post(
                    urn="r3",
                    text="Learning Python basics",
                ),
            ],
            creator_dir,
        )

        with CorpusDB(db_path) as db:
            db.ingest_creator(creator_dir)
            results = db.search("Python")
            # Should find exactly the 2 posts containing "Python"
            assert len(results) == 2
            # The post with more occurrences of "Python" should rank first
            assert "Python Python Python" in results[0]["text"]


class TestCorpusPersistence:
    """Create corpus, close, reopen — data still there."""

    def test_corpus_persistence(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        creator_dir = tmp_path / "ref" / "frank"
        _make_posts_raw(
            [
                _sample_post(urn="p1", text="Persistent post one"),
                _sample_post(urn="p2", text="Persistent post two"),
            ],
            creator_dir,
        )

        # First session: ingest
        with CorpusDB(db_path) as db:
            db.ingest_creator(creator_dir)

        # Second session: reopen and verify
        with CorpusDB(db_path) as db:
            results = db.top_by_engagement(limit=100)
            assert len(results) == 2

            search_results = db.search("Persistent")
            assert len(search_results) == 2


class TestIngestAll:
    """Test bulk ingestion from a reference library directory."""

    def test_ingest_all(self, tmp_path: Path) -> None:
        ref_lib = tmp_path / "ref-lib"
        _make_posts_raw(
            [_sample_post(urn="a1", text="Alice post")],
            ref_lib / "alice",
        )
        _make_posts_raw(
            [_sample_post(urn="b1", text="Bob post")],
            ref_lib / "bob",
        )
        # _index directory should be skipped (starts with _)
        (ref_lib / "_index").mkdir(parents=True)

        db_path = tmp_path / "test.db"
        with CorpusDB(db_path) as db:
            total = db.ingest_all(reference_lib=ref_lib)
            assert total == 2

            results = db.top_by_engagement(limit=100)
            assert len(results) == 2
            creators = {r["creator"] for r in results}
            assert creators == {"alice", "bob"}


class TestStats:
    """Verify corpus statistics computation."""

    def test_stats(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        creator_dir = tmp_path / "ref" / "stats-creator"
        _make_posts_raw(
            [
                _sample_post(urn="s1", reactions=10, comments=0, reposts=0, category="Tutorial"),
                _sample_post(urn="s2", reactions=20, comments=5, reposts=2, category="Tutorial"),
                _sample_post(urn="s3", reactions=5, comments=1, reposts=0, category="Case Study"),
            ],
            creator_dir,
        )

        with CorpusDB(db_path) as db:
            db.ingest_creator(creator_dir)
            s = db.stats()

            assert s["total_posts"] == 3
            assert s["total_creators"] == 1
            assert s["max_engagement"] > s["min_engagement"]
            assert len(s["by_content_type"]) == 2
            assert len(s["by_creator"]) == 1


class TestEdgeCases:
    """Edge cases: missing urn, stringified numbers, missing fields."""

    def test_missing_urn_gets_synthetic_id(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        creator_dir = tmp_path / "ref" / "nourn"
        _make_posts_raw(
            [{"text": "No URN post", "index": 42}],
            creator_dir,
        )

        with CorpusDB(db_path) as db:
            count = db.ingest_creator(creator_dir)
            assert count == 1
            results = db.top_by_engagement(limit=10)
            assert results[0]["id"] == "nourn::synthetic:42"

    def test_stringified_numbers(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        creator_dir = tmp_path / "ref" / "strnum"
        _make_posts_raw(
            [{"urn": "x1", "text": "String nums", "reactions": "1,234", "comments": "56"}],
            creator_dir,
        )

        with CorpusDB(db_path) as db:
            db.ingest_creator(creator_dir)
            results = db.top_by_engagement(limit=10)
            assert results[0]["reactions"] == 1234
            assert results[0]["comments"] == 56

    def test_json_fields_deserialized(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        creator_dir = tmp_path / "ref" / "jsonf"
        _make_posts_raw(
            [
                _sample_post(
                    urn="j1",
                    images=["https://example.com/img.png"],
                    hashtags=["#test", "#ai"],
                ),
            ],
            creator_dir,
        )

        with CorpusDB(db_path) as db:
            db.ingest_creator(creator_dir)
            results = db.top_by_engagement(limit=10)
            assert results[0]["image_urls"] == ["https://example.com/img.png"]
            assert results[0]["hashtags"] == ["#test", "#ai"]
