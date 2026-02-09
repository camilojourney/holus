"""
Tests for the Content Strategy domain (SPEC-002, SPEC-003).

Covers:
- Adapter interfaces (YouTube, Twitter) — validation, adaptation
- Publisher pattern (Video, Text) — registration, publish flow
- RepurposingEngine — pipeline stages, format adaptation
- Domain orchestrator — agent discovery and wiring
- Shared re-exports
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import helpers for hyphenated directory agents/content-strategy/
# ---------------------------------------------------------------------------
_CS_DIR = Path(__file__).resolve().parent.parent / "agents" / "content-strategy"


def _bootstrap_cs_package():
    """Create a synthetic package so relative imports inside content-strategy work."""
    import types

    # Top-level synthetic package
    pkg_root = "cs_pkg"

    # adapters sub-package
    adapters_pkg_name = f"{pkg_root}.adapters"
    adapters_path = _CS_DIR / "adapters"
    adapters_init = types.ModuleType(adapters_pkg_name)
    adapters_init.__path__ = [str(adapters_path)]
    adapters_init.__package__ = adapters_pkg_name
    sys.modules[adapters_pkg_name] = adapters_init

    # publishers sub-package
    publishers_pkg_name = f"{pkg_root}.publishers"
    publishers_path = _CS_DIR / "publishers"
    publishers_init = types.ModuleType(publishers_pkg_name)
    publishers_init.__path__ = [str(publishers_path)]
    publishers_init.__package__ = publishers_pkg_name
    sys.modules[publishers_pkg_name] = publishers_init

    def _load(module_fqn: str, file_path: Path, package: str):
        spec = importlib.util.spec_from_file_location(
            module_fqn, file_path, submodule_search_locations=[]
        )
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = package
        sys.modules[module_fqn] = mod
        spec.loader.exec_module(mod)
        return mod

    # Load adapter modules (base first — others depend on it)
    base_mod = _load(
        f"{adapters_pkg_name}.base_adapter",
        adapters_path / "base_adapter.py",
        adapters_pkg_name,
    )
    twitter_mod = _load(
        f"{adapters_pkg_name}.twitter_adapter",
        adapters_path / "twitter_adapter.py",
        adapters_pkg_name,
    )
    youtube_mod = _load(
        f"{adapters_pkg_name}.youtube_adapter",
        adapters_path / "youtube_adapter.py",
        adapters_pkg_name,
    )

    # Load publisher modules (they use relative imports to adapters via "..")
    # We need to register the root package too for `..adapters` to resolve
    root_pkg = types.ModuleType(pkg_root)
    root_pkg.__path__ = [str(_CS_DIR)]
    root_pkg.__package__ = pkg_root
    root_pkg.adapters = adapters_init
    root_pkg.publishers = publishers_init
    sys.modules[pkg_root] = root_pkg

    vpub_mod = _load(
        f"{publishers_pkg_name}.video_publisher",
        publishers_path / "video_publisher.py",
        publishers_pkg_name,
    )
    tpub_mod = _load(
        f"{publishers_pkg_name}.text_publisher",
        publishers_path / "text_publisher.py",
        publishers_pkg_name,
    )

    # Load repurposing engine (top-level in content-strategy, uses relative import to adapters)
    engine_mod = _load(
        f"{pkg_root}.repurposing_engine",
        _CS_DIR / "repurposing_engine.py",
        pkg_root,
    )

    return base_mod, twitter_mod, youtube_mod, vpub_mod, tpub_mod, engine_mod


(
    _base_adapter_mod,
    _twitter_mod,
    _youtube_mod,
    _vpub_mod,
    _tpub_mod,
    _engine_mod,
) = _bootstrap_cs_package()

# Pull classes out
BaseAdapter = _base_adapter_mod.BaseAdapter
Content = _base_adapter_mod.Content
ContentType = _base_adapter_mod.ContentType
PublishResult = _base_adapter_mod.PublishResult
Analytics = _base_adapter_mod.Analytics

TwitterAdapter = _twitter_mod.TwitterAdapter
YouTubeAdapter = _youtube_mod.YouTubeAdapter

VideoPublisher = _vpub_mod.VideoPublisher
TextPublisher = _tpub_mod.TextPublisher

RepurposingEngine = _engine_mod.RepurposingEngine
ClipSuggestion = _engine_mod.ClipSuggestion
RepurposedContent = _engine_mod.RepurposedContent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _video_content(**overrides) -> Content:
    """Factory for video Content objects."""
    defaults = dict(
        type=ContentType.VIDEO,
        title="Test Video",
        body="A great description of the video",
        media_path="/tmp/video.mp4",
        tags=["ai", "python"],
    )
    defaults.update(overrides)
    return Content(**defaults)


def _text_content(**overrides) -> Content:
    """Factory for text Content objects."""
    defaults = dict(
        type=ContentType.TEXT,
        title="Test Post",
        body="Short post body",
        tags=["ai"],
    )
    defaults.update(overrides)
    return Content(**defaults)


class FakeVideoAdapter(BaseAdapter):
    """In-memory adapter for testing publishers."""

    platform = "fake_video"
    content_types = [ContentType.VIDEO]

    def __init__(self, config=None, *, should_fail: bool = False):
        super().__init__(config or {})
        self.should_fail = should_fail
        self.published: list[Content] = []

    async def authenticate(self) -> bool:
        return True

    async def publish(self, content: Content) -> PublishResult:
        if self.should_fail:
            return PublishResult(
                success=False, platform=self.platform, error="Simulated failure"
            )
        self.published.append(content)
        return PublishResult(
            success=True,
            platform=self.platform,
            content_id="fake-123",
            url="https://fake.video/fake-123",
        )

    async def get_analytics(self, content_id: str) -> Analytics:
        return Analytics(views=100)

    def adapt_content(self, content: Content) -> Content:
        return content

    def validate_content(self, content: Content) -> tuple[bool, list[str]]:
        if content.type != ContentType.VIDEO:
            return (False, ["Only VIDEO supported"])
        return (True, [])


class FakeTextAdapter(BaseAdapter):
    """In-memory adapter for testing text publishers."""

    platform = "fake_text"
    content_types = [ContentType.TEXT]

    def __init__(self, config=None, *, should_fail: bool = False):
        super().__init__(config or {})
        self.should_fail = should_fail
        self.published: list[Content] = []

    async def authenticate(self) -> bool:
        return True

    async def publish(self, content: Content) -> PublishResult:
        if self.should_fail:
            return PublishResult(
                success=False, platform=self.platform, error="Simulated failure"
            )
        self.published.append(content)
        return PublishResult(
            success=True,
            platform=self.platform,
            content_id="fake-txt-1",
            url="https://fake.text/fake-txt-1",
        )

    async def get_analytics(self, content_id: str) -> Analytics:
        return Analytics(likes=42)

    def adapt_content(self, content: Content) -> Content:
        return content

    def validate_content(self, content: Content) -> tuple[bool, list[str]]:
        if content.type != ContentType.TEXT:
            return (False, ["Only TEXT supported"])
        return (True, [])


# ===================================================================
# YouTube Adapter Tests
# ===================================================================


class TestYouTubeAdapter:
    """Tests for YouTubeAdapter (SPEC-003)."""

    def setup_method(self):
        self.adapter = YouTubeAdapter(config={})

    def test_platform_name(self):
        assert self.adapter.platform == "youtube"

    def test_content_types_video_only(self):
        assert self.adapter.content_types == [ContentType.VIDEO]

    def test_validate_valid_video(self):
        content = _video_content(title="Short title")
        valid, errors = self.adapter.validate_content(content)
        assert valid is True
        assert errors == []

    def test_validate_rejects_non_video(self):
        content = _text_content()
        valid, errors = self.adapter.validate_content(content)
        assert valid is False
        assert any("VIDEO" in e for e in errors)

    def test_validate_rejects_missing_media_path(self):
        content = _video_content(media_path=None)
        valid, errors = self.adapter.validate_content(content)
        assert valid is False
        assert any("file path" in e.lower() for e in errors)

    def test_validate_rejects_long_title(self):
        content = _video_content(title="X" * 200)
        valid, errors = self.adapter.validate_content(content)
        assert valid is False
        assert any("100" in e for e in errors)

    def test_adapt_truncates_long_title(self):
        content = _video_content(title="T" * 200)
        adapted = self.adapter.adapt_content(content)
        assert len(adapted.title) <= YouTubeAdapter.MAX_TITLE_LENGTH
        assert adapted.title.endswith("...")

    def test_adapt_truncates_long_description(self):
        content = _video_content(body="D" * 6000)
        adapted = self.adapter.adapt_content(content)
        assert len(adapted.body) <= YouTubeAdapter.MAX_DESCRIPTION_LENGTH

    def test_adapt_adds_chapters(self):
        chapters = [
            {"time": "0:00", "title": "Intro"},
            {"time": "5:00", "title": "Main"},
        ]
        content = _video_content(metadata={"chapters": chapters})
        adapted = self.adapter.adapt_content(content)
        assert "Chapters:" in adapted.body
        assert "0:00 Intro" in adapted.body

    @pytest.mark.asyncio
    async def test_publish_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            await self.adapter.publish(_video_content())

    @pytest.mark.asyncio
    async def test_authenticate_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            await self.adapter.authenticate()


# ===================================================================
# Twitter Adapter Tests
# ===================================================================


class TestTwitterAdapter:
    """Tests for TwitterAdapter (SPEC-003)."""

    def setup_method(self):
        self.adapter = TwitterAdapter(config={})

    def test_platform_name(self):
        assert self.adapter.platform == "twitter"

    def test_content_types_includes_text(self):
        assert ContentType.TEXT in self.adapter.content_types

    def test_content_types_includes_video(self):
        assert ContentType.VIDEO in self.adapter.content_types

    def test_validate_short_text_passes(self):
        content = _text_content(body="Hello world")
        valid, errors = self.adapter.validate_content(content)
        assert valid is True
        assert errors == []

    def test_validate_long_text_without_thread_fails(self):
        long_body = "x" * 300
        content = _text_content(body=long_body)
        valid, errors = self.adapter.validate_content(content)
        assert valid is False
        assert any("280" in e for e in errors)

    def test_adapt_splits_long_text_into_thread(self):
        long_body = " ".join(["word"] * 100)  # well over 280 chars
        content = _text_content(body=long_body)
        adapted = self.adapter.adapt_content(content)
        thread = adapted.metadata.get("thread", [])
        assert len(thread) > 1
        for tweet in thread:
            assert len(tweet) <= TwitterAdapter.MAX_TWEET_LENGTH

    def test_thread_has_numbering(self):
        long_body = " ".join(["word"] * 80)
        content = _text_content(body=long_body)
        adapted = self.adapter.adapt_content(content)
        thread = adapted.metadata.get("thread", [])
        if len(thread) > 1:
            assert "(1/" in thread[0]

    def test_thread_capped_at_max(self):
        # Enormous text to force many tweets
        content = _text_content(body=" ".join(["longword"] * 2000))
        adapted = self.adapter.adapt_content(content)
        thread = adapted.metadata.get("thread", [])
        assert len(thread) <= TwitterAdapter.MAX_THREAD_LENGTH

    def test_short_text_no_thread(self):
        content = _text_content(body="Short")
        adapted = self.adapter.adapt_content(content)
        assert "thread" not in (adapted.metadata or {})

    @pytest.mark.asyncio
    async def test_publish_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            await self.adapter.publish(_text_content())


# ===================================================================
# VideoPublisher Tests
# ===================================================================


class TestVideoPublisher:
    """Tests for VideoPublisher (SPEC-002/003 publisher pattern)."""

    def test_init_empty(self):
        pub = VideoPublisher()
        assert pub.platforms == []

    def test_register_video_adapter(self):
        pub = VideoPublisher()
        pub.register_adapter(FakeVideoAdapter())
        assert "fake_video" in pub.platforms

    def test_register_rejects_non_video_adapter(self):
        pub = VideoPublisher()
        pub.register_adapter(FakeTextAdapter())
        assert pub.platforms == []

    def test_validate_delegates_to_adapters(self):
        pub = VideoPublisher()
        pub.register_adapter(FakeVideoAdapter())
        results = pub.validate(_video_content())
        assert "fake_video" in results
        valid, errors = results["fake_video"]
        assert valid is True

    @pytest.mark.asyncio
    async def test_publish_success(self):
        pub = VideoPublisher()
        adapter = FakeVideoAdapter()
        pub.register_adapter(adapter)
        results = await pub.publish(_video_content())
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].platform == "fake_video"
        assert len(adapter.published) == 1

    @pytest.mark.asyncio
    async def test_publish_rejects_non_video_content(self):
        pub = VideoPublisher()
        pub.register_adapter(FakeVideoAdapter())
        results = await pub.publish(_text_content())
        assert len(results) == 1
        assert results[0].success is False
        assert "VIDEO" in results[0].error

    @pytest.mark.asyncio
    async def test_publish_no_adapters(self):
        pub = VideoPublisher()
        results = await pub.publish(_video_content())
        assert len(results) == 1
        assert results[0].success is False
        assert "No matching" in results[0].error

    @pytest.mark.asyncio
    async def test_publish_platform_filter(self):
        pub = VideoPublisher()
        pub.register_adapter(FakeVideoAdapter())
        results = await pub.publish(_video_content(), platforms=["nonexistent"])
        assert len(results) == 1
        assert results[0].success is False

    @pytest.mark.asyncio
    async def test_publish_handles_adapter_failure(self):
        pub = VideoPublisher()
        pub.register_adapter(FakeVideoAdapter(should_fail=True))
        results = await pub.publish(_video_content())
        assert len(results) == 1
        assert results[0].success is False
        assert "Simulated failure" in results[0].error

    @pytest.mark.asyncio
    async def test_publish_handles_not_implemented(self):
        """Real adapters raise NotImplementedError — publisher catches it."""
        pub = VideoPublisher()
        pub.register_adapter(YouTubeAdapter({}))
        results = await pub.publish(_video_content())
        assert len(results) == 1
        assert results[0].success is False
        assert "not yet implemented" in results[0].error


# ===================================================================
# TextPublisher Tests
# ===================================================================


class TestTextPublisher:
    """Tests for TextPublisher (SPEC-002/003 publisher pattern)."""

    def test_init_empty(self):
        pub = TextPublisher()
        assert pub.platforms == []

    def test_register_text_adapter(self):
        pub = TextPublisher()
        pub.register_adapter(FakeTextAdapter())
        assert "fake_text" in pub.platforms

    def test_register_rejects_non_text_adapter(self):
        pub = TextPublisher()
        # YouTubeAdapter only supports VIDEO
        pub.register_adapter(YouTubeAdapter({}))
        assert pub.platforms == []

    def test_validate(self):
        pub = TextPublisher()
        pub.register_adapter(FakeTextAdapter())
        results = pub.validate(_text_content())
        assert "fake_text" in results

    @pytest.mark.asyncio
    async def test_publish_success(self):
        pub = TextPublisher()
        adapter = FakeTextAdapter()
        pub.register_adapter(adapter)
        results = await pub.publish(_text_content())
        assert len(results) == 1
        assert results[0].success is True
        assert len(adapter.published) == 1

    @pytest.mark.asyncio
    async def test_publish_rejects_non_text_content(self):
        pub = TextPublisher()
        pub.register_adapter(FakeTextAdapter())
        results = await pub.publish(_video_content())
        assert len(results) == 1
        assert results[0].success is False
        assert "TEXT" in results[0].error

    @pytest.mark.asyncio
    async def test_publish_handles_not_implemented(self):
        pub = TextPublisher()
        pub.register_adapter(TwitterAdapter({}))
        results = await pub.publish(_text_content(body="Short"))
        assert len(results) == 1
        assert results[0].success is False
        assert "not yet implemented" in results[0].error


# ===================================================================
# RepurposingEngine Tests
# ===================================================================


class TestRepurposingEngine:
    """Tests for RepurposingEngine pipeline (SPEC-002)."""

    def setup_method(self):
        self.engine = RepurposingEngine()

    @pytest.mark.asyncio
    async def test_transcribe_returns_string(self):
        result = await self.engine.transcribe("/tmp/test.mp4")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_extract_clips_returns_suggestions(self):
        clips = await self.engine.extract_clips("/tmp/test.mp4")
        assert isinstance(clips, list)
        assert len(clips) >= 1
        assert isinstance(clips[0], ClipSuggestion)
        assert clips[0].start_seconds < clips[0].end_seconds

    @pytest.mark.asyncio
    async def test_extract_clips_respects_max(self):
        clips = await self.engine.extract_clips("/tmp/test.mp4", max_clips=2)
        assert len(clips) <= 2

    @pytest.mark.asyncio
    async def test_extract_clips_generates_transcript_if_missing(self):
        clips = await self.engine.extract_clips("/tmp/test.mp4", transcript=None)
        assert len(clips) >= 1

    @pytest.mark.asyncio
    async def test_cut_clip_returns_path(self):
        clip = ClipSuggestion(start_seconds=10, end_seconds=30, reason="test")
        path = await self.engine.cut_clip("/tmp/source.mp4", clip)
        assert isinstance(path, str)
        assert "10" in path and "30" in path

    @pytest.mark.asyncio
    async def test_cut_clip_uses_custom_output_path(self):
        clip = ClipSuggestion(start_seconds=0, end_seconds=60, reason="test")
        path = await self.engine.cut_clip("/tmp/source.mp4", clip, "/tmp/custom.mp4")
        assert path == "/tmp/custom.mp4"

    @pytest.mark.asyncio
    async def test_generate_hooks_default_platforms(self):
        hooks = await self.engine.generate_hooks("Some transcript text")
        assert "twitter" in hooks
        assert "youtube" in hooks
        assert "linkedin" in hooks

    @pytest.mark.asyncio
    async def test_generate_hooks_custom_platforms(self):
        hooks = await self.engine.generate_hooks("Transcript", platforms=["tiktok"])
        assert "tiktok" in hooks
        assert "twitter" not in hooks

    def test_adapt_format_video_to_text(self):
        source = _video_content()
        adapted = self.engine.adapt_format(source, ContentType.TEXT, "twitter")
        assert adapted.type == ContentType.TEXT
        assert "repurposed_from" in adapted.metadata
        assert adapted.metadata["repurposed_from"] == "video"
        assert adapted.metadata["target_platform"] == "twitter"

    def test_adapt_format_preserves_tags(self):
        source = _video_content(tags=["a", "b"])
        adapted = self.engine.adapt_format(source, ContentType.TEXT, "twitter")
        assert adapted.tags == ["a", "b"]
        # Ensure it's a copy, not a reference
        source.tags.append("c")
        assert len(adapted.tags) == 2

    def test_adapt_format_video_to_text_adds_prefix(self):
        source = _video_content(title="My Video")
        adapted = self.engine.adapt_format(source, ContentType.TEXT, "twitter")
        assert "🎬" in adapted.body
        assert "My Video" in adapted.body

    @pytest.mark.asyncio
    async def test_repurpose_full_pipeline(self):
        results = await self.engine.repurpose(
            media_path="/tmp/source.mp4",
            title="Test Video",
            platforms=["twitter", "youtube"],
        )
        assert len(results) == 2
        assert all(isinstance(r, RepurposedContent) for r in results)

        platforms = [r.platform for r in results]
        assert "twitter" in platforms
        assert "youtube" in platforms

    @pytest.mark.asyncio
    async def test_repurpose_twitter_is_text_type(self):
        results = await self.engine.repurpose("/tmp/v.mp4", "T", platforms=["twitter"])
        assert results[0].content.type == ContentType.TEXT

    @pytest.mark.asyncio
    async def test_repurpose_youtube_stays_video(self):
        results = await self.engine.repurpose("/tmp/v.mp4", "T", platforms=["youtube"])
        assert results[0].content.type == ContentType.VIDEO

    @pytest.mark.asyncio
    async def test_repurpose_attaches_clip(self):
        results = await self.engine.repurpose("/tmp/v.mp4", "T")
        for r in results:
            assert r.source_clip is not None
            assert isinstance(r.source_clip, ClipSuggestion)


# ===================================================================
# Orchestrator Domain Wiring Tests
# ===================================================================


class TestOrchestratorParseSchedule:
    """Tests for core.orchestrator.parse_schedule (SPEC-001)."""

    def test_manual_returns_none(self):
        from core.orchestrator import parse_schedule
        assert parse_schedule("manual") is None

    def test_every_minutes(self):
        from core.orchestrator import parse_schedule
        from apscheduler.triggers.interval import IntervalTrigger
        trigger = parse_schedule("every 30 minutes")
        assert isinstance(trigger, IntervalTrigger)

    def test_every_hours(self):
        from core.orchestrator import parse_schedule
        from apscheduler.triggers.interval import IntervalTrigger
        trigger = parse_schedule("every 2 hours")
        assert isinstance(trigger, IntervalTrigger)

    def test_daily_at_am(self):
        from core.orchestrator import parse_schedule
        from apscheduler.triggers.cron import CronTrigger
        trigger = parse_schedule("daily at 9am")
        assert isinstance(trigger, CronTrigger)

    def test_daily_at_pm(self):
        from core.orchestrator import parse_schedule
        from apscheduler.triggers.cron import CronTrigger
        trigger = parse_schedule("daily at 3pm")
        assert isinstance(trigger, CronTrigger)

    def test_3x_daily(self):
        from core.orchestrator import parse_schedule
        from apscheduler.triggers.interval import IntervalTrigger
        trigger = parse_schedule("3x daily")
        assert isinstance(trigger, IntervalTrigger)

    def test_unknown_falls_back_to_interval(self):
        from core.orchestrator import parse_schedule
        from apscheduler.triggers.interval import IntervalTrigger
        trigger = parse_schedule("whenever the moon is full")
        assert isinstance(trigger, IntervalTrigger)


# ===================================================================
# Shared Re-export Tests
# ===================================================================


class TestSharedReexports:
    """Verify shared/ re-exports from core/ work correctly."""

    def test_base_agent_reexport(self):
        from shared.base_agent import BaseAgent, RunRecord
        from core.base_agent import BaseAgent as CoreBaseAgent
        from core.base_agent import RunRecord as CoreRunRecord
        assert BaseAgent is CoreBaseAgent
        assert RunRecord is CoreRunRecord

    def test_llm_reexport(self):
        from shared.llm import LLMProvider, TaskComplexity, load_llm_provider
        from core.llm import LLMProvider as CoreLLM
        assert LLMProvider is CoreLLM

    def test_memory_reexport(self):
        from shared.memory import MemoryStore
        from core.memory import MemoryStore as CoreMem
        assert MemoryStore is CoreMem

    def test_notifier_reexport(self):
        from shared.notifier import Notifier, TelegramNotifier
        from core.notifier import Notifier as CoreNotifier
        assert Notifier is CoreNotifier

    def test_orchestrator_reexport(self):
        from shared.orchestrator import Orchestrator, parse_schedule
        from core.orchestrator import Orchestrator as CoreOrch
        assert Orchestrator is CoreOrch
