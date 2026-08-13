"""Research candidate persistence and approval bridge."""

from __future__ import annotations

import asyncio
import fcntl
import logging
import re
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast

import httpx
import yaml

from holus.agents.marketing.thought_pipeline import DEFAULT_CHANNELS, ThoughtContentPipeline
from holus.core.config import HolusConfig
from holus.core.storage import atomic_write_text
from holus.lineage.recorder import LineageRecorder
from holus.research.models import RawResearchItem, ResearchCandidate, ResearchScore

logger = logging.getLogger(__name__)


class ContentSetProtocol(Protocol):
    group_id: str


class ThoughtPipelineProtocol(Protocol):
    async def create_content_set(
        self,
        *,
        thought: str,
        channels: list[str],
        source_type: str | None = None,
        source_url: str | None = None,
    ) -> ContentSetProtocol:
        """Create content records from a thought."""


PipelineFactory = Callable[[], ThoughtPipelineProtocol]


class CandidateStore:
    """YAML-backed candidate store."""

    def __init__(
        self,
        directory: Path | str = "data/research/candidates",
        *,
        queue_dir: Path | str = "data/content-queue",
        lineage_dir: Path | str | None = None,
        pipeline_factory: PipelineFactory | None = None,
    ) -> None:
        self.directory = Path(directory)
        self.queue_dir = Path(queue_dir)
        self._pipeline_factory = pipeline_factory
        configured = Path(lineage_dir) if lineage_dir is not None else HolusConfig.load().lineage_dir
        self.lineage_recorder = LineageRecorder(
            configured if configured.is_absolute() else Path.cwd() / configured
        )

    def create(self, item: RawResearchItem, score: ResearchScore) -> ResearchCandidate:
        path = self._path(item.item_id)
        if path.exists():
            return self.get(item.item_id)
        candidate = ResearchCandidate(
            candidate_id=item.item_id,
            item=item,
            score=score,
            created_at=datetime.now(UTC),
        )
        self.save(candidate)
        self._record_lineage(candidate)
        return candidate

    def save(self, candidate: ResearchCandidate) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path(candidate.candidate_id)
        data = candidate.model_dump(mode="json")
        atomic_write_text(path, yaml.safe_dump(data, sort_keys=False))
        return path

    def get(self, candidate_id: str) -> ResearchCandidate:
        path = self._path(candidate_id)
        if not path.exists():
            msg = f"Research candidate {candidate_id!r} not found"
            raise FileNotFoundError(msg)
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return ResearchCandidate.model_validate(data)

    def list(self, *, status: str | None = None) -> list[ResearchCandidate]:
        if not self.directory.exists():
            return []
        candidates: list[ResearchCandidate] = []
        for path in sorted(self.directory.glob("*.yaml")):
            try:
                candidate = ResearchCandidate.model_validate(
                    yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                )
            except Exception:
                continue
            if status is None or candidate.status == status:
                candidates.append(candidate)
        return candidates

    async def approve(self, candidate_id: str) -> ResearchCandidate:
        async with self._approval_lock(candidate_id):
            candidate = self.get(candidate_id)
            if candidate.status == "approved" and candidate.approved_group_id:
                return candidate
            pipeline = self._make_pipeline()
            thought = self._approval_text(candidate)
            try:
                content_set = await pipeline.create_content_set(
                    thought=thought,
                    channels=list(DEFAULT_CHANNELS),
                    source_type="url",
                    source_url=str(candidate.item.url),
                )
            except (httpx.HTTPError, ValueError) as url_exc:
                try:
                    content_set = await pipeline.create_content_set(
                        thought=thought,
                        channels=list(DEFAULT_CHANNELS),
                        source_type="text",
                        source_url=None,
                    )
                except Exception as text_exc:
                    candidate.status = "failed"
                    candidate.failure_reason = (
                        f"url approval failed: {url_exc}; text fallback failed: {text_exc}"
                    )
                    self.save(candidate)
                    raise
            candidate.status = "approved"
            candidate.approved_group_id = content_set.group_id
            candidate.failure_reason = None
            self.save(candidate)
            self._record_lineage(candidate)
            return candidate

    def reject(self, candidate_id: str) -> ResearchCandidate:
        candidate = self.get(candidate_id)
        if candidate.status == "pending":
            candidate.status = "rejected"
            self.save(candidate)
            self._record_lineage(candidate)
        return candidate

    def _record_lineage(self, candidate: ResearchCandidate) -> None:
        """Keep research persistence successful if optional provenance storage fails."""
        try:
            self.lineage_recorder.record_candidate(candidate)
        except Exception:
            logger.exception(
                "lineage_emission_failed", extra={"candidate_id": candidate.candidate_id}
            )

    def _make_pipeline(self) -> ThoughtPipelineProtocol:
        if self._pipeline_factory is not None:
            return self._pipeline_factory()
        return cast("ThoughtPipelineProtocol", ThoughtContentPipeline(queue_dir=self.queue_dir))

    def _path(self, candidate_id: str) -> Path:
        if (
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", candidate_id)
            or ".." in candidate_id
        ):
            raise ValueError("Invalid candidate ID")
        return self.directory / f"{candidate_id}.yaml"

    @asynccontextmanager
    async def _approval_lock(self, candidate_id: str) -> Any:
        self.directory.mkdir(parents=True, exist_ok=True)
        lock_path = self.directory / f"{candidate_id}.approval.lock"
        with lock_path.open("w", encoding="utf-8") as lock_file:
            await asyncio.to_thread(fcntl.flock, lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _approval_text(candidate: ResearchCandidate) -> str:
        return "\n\n".join(
            [
                candidate.score.key_idea,
                candidate.score.why_it_matters,
                f"Source: {candidate.item.title} ({candidate.item.url})",
            ]
        )


def candidate_to_api_dict(candidate: ResearchCandidate) -> dict[str, Any]:
    return candidate.model_dump(mode="json")
