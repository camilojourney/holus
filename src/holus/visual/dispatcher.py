"""Provider-routed visual asset dispatcher with JSONL audit logs.

The dispatcher keeps Holus' visual production paths behind one contract:
deterministic HTML/PDF rendering for exact layouts, and local AI image
generation for exploratory LinkedIn assets. Production AI generation should
move behind Pilaster/OpenAI providers later; the Codex CLI provider is
intentionally guarded as local/dev-only.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from holus.visual.models import RenderSpec  # noqa: TC001 - Pydantic needs this at runtime.
from holus.visual.production_plan import (
    VisualProductionPlan,
    build_visual_production_plan,
)
from holus.visual.proximity_router import VisualConceptRoute  # noqa: TC001
from holus.visual.visual_judge import (
    VisualJudgeDecision,
    VisualJudgeVerdict,
    judge_visual_output,
    mutate_visual_plan_for_retry,
)


def _run_command_with_timeout(
    command: list[str],
    *,
    timeout_seconds: int,
) -> subprocess.CompletedProcess[str]:
    """Run a command and force-kill it if timeout expires."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        return subprocess.CompletedProcess(
            command,
            124,
            stdout=stdout,
            stderr=f"{stderr}\nTimed out after {timeout_seconds} seconds.",
        )
    return subprocess.CompletedProcess(command, process.returncode, stdout=stdout, stderr=stderr)


DEFAULT_LOG_PATH = Path("data/logs/image-dispatch.jsonl")
DEFAULT_OUTPUT_DIR = Path("data/rendered-content")


class VisualProvider(StrEnum):
    """Visual asset providers currently known to Holus."""

    HTML_RENDERER = "html_renderer"
    CODEX_CLI_IMAGE = "codex_cli_image"
    AGY_CLI_IMAGE = "agy_cli_image"
    PILASTER_MCP = "pilaster_mcp"
    OPENAI_IMAGE_API = "openai_image_api"


class VisualAssetKind(StrEnum):
    """High-level output shape requested by a content workflow."""

    SINGLE_IMAGE = "single_image"
    CAROUSEL = "carousel"
    IMAGE_WITH_OVERLAY = "image_with_overlay"


class VisualDispatchStatus(StrEnum):
    """Terminal dispatcher statuses."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RefinedVisualSource(BaseModel):
    """Review-ready content that a visual provider is allowed to use.

    Raw thoughts are kept as provenance only. AI image providers should build
    prompts from ``refined_text`` and the extracted takeaway, not from the raw
    intake transcript.
    """

    piece_id: str
    platform: str
    content_type: str
    refined_text: str = Field(min_length=1)
    headline: str | None = None
    topic: str | None = None
    content_pillar: str | None = None
    intended_takeaway: str | None = None
    raw_thought_provenance: str | None = None
    thought_essence: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_queue_record(cls, record: dict[str, Any]) -> RefinedVisualSource:
        """Build a visual source from a Holus queue record."""
        thought_essence = record.get("thought_essence") if isinstance(record, dict) else None
        if not isinstance(thought_essence, dict):
            thought_essence = {}
        return cls(
            piece_id=str(record.get("piece_id", record.get("id", "")) or ""),
            platform=str(record.get("platform", "linkedin") or "linkedin"),
            content_type=str(record.get("content_type", "image_post") or "image_post"),
            refined_text=str(record.get("text", "") or ""),
            headline=str(record.get("headline") or record.get("topic") or "") or None,
            topic=str(record.get("topic") or "") or None,
            content_pillar=str(record.get("content_pillar") or "") or None,
            intended_takeaway=str(
                thought_essence.get("thesis") or record.get("topic") or record.get("text") or ""
            )
            or None,
            raw_thought_provenance=str(
                record.get("idea_source") or record.get("source_raw_input") or ""
            )
            or None,
            thought_essence=thought_essence,
            metadata={
                "group_id": record.get("group_id"),
                "model_used": record.get("model_used"),
                "source_type": record.get("source_type"),
                "source_url": record.get("source_url"),
            },
        )

    def prompt_brief(self) -> str:
        """Return the provider-facing creative brief rooted in refined copy."""
        parts = [
            "SOURCE OF TRUTH: refined Holus content, not the raw thought transcript.",
            f"Platform: {self.platform}",
            f"Content type: {self.content_type}",
        ]
        if self.headline:
            parts.append(f"Headline/thesis: {self.headline}")
        if self.topic and self.topic != self.headline:
            parts.append(f"Topic: {self.topic}")
        if self.intended_takeaway:
            parts.append(f"Intended takeaway: {self.intended_takeaway}")
        parts.append(f"Refined post/caption:\n{self.refined_text}")
        parts.append(
            "Raw thought provenance exists only for lineage. Do not copy raw wording into the image."
        )
        return "\n".join(parts)

    def log_summary(self) -> dict[str, Any]:
        """Return compact source metadata for JSONL logs."""
        return {
            "piece_id": self.piece_id,
            "platform": self.platform,
            "content_type": self.content_type,
            "topic": self.topic,
            "content_pillar": self.content_pillar,
            "has_raw_provenance": bool(self.raw_thought_provenance),
            "refined_text_chars": len(self.refined_text),
        }


class VisualDispatchRequest(BaseModel):
    """Provider-neutral visual generation request.

    For deterministic assets, pass ``render_spec``. For AI-generated images,
    pass ``prompt`` and choose ``provider=codex_cli_image`` in local/dev.
    """

    request_id: str = Field(default_factory=lambda: f"img_{uuid4().hex[:12]}")
    platform: str = Field(default="linkedin")
    asset_kind: VisualAssetKind = Field(default=VisualAssetKind.SINGLE_IMAGE)
    provider: VisualProvider | None = Field(default=None)
    prompt: str | None = Field(default=None, description="AI image prompt or creative brief")
    refined_source: RefinedVisualSource | None = Field(
        default=None,
        description="Review-ready content source used to derive AI image prompts",
    )
    visual_route: VisualConceptRoute | None = Field(
        default=None,
        description="Chosen visual proximity route for person/workflow/chart/story decisions",
    )
    visual_plan: VisualProductionPlan | None = Field(
        default=None,
        description="Detailed deterministic production plan for generation compliance",
    )
    render_spec: RenderSpec | None = Field(
        default=None,
        description="Deterministic HTML/PDF render specification",
    )
    carousel_outline: dict[str, Any] | None = Field(
        default=None,
        description="Deterministic carousel outline to render as a PDF",
    )
    output_path: Path | None = Field(default=None)
    output_dir: Path = Field(default=DEFAULT_OUTPUT_DIR)
    log_path: Path = Field(default=DEFAULT_LOG_PATH)
    width: int = Field(default=1024, ge=256, le=4096)
    height: int = Field(default=1024, ge=256, le=4096)
    timeout_seconds: int = Field(default=180, ge=10, le=900)
    enable_visual_judge: bool = Field(
        default=True,
        description="Run deterministic file/plan quality gate after provider generation",
    )
    max_attempts: int = Field(
        default=1,
        ge=1,
        le=3,
        description="Maximum provider attempts when the visual judge emits a retry verdict",
    )
    model: str | None = Field(
        default=None,
        description="Optional agent/provider model name where the provider supports it",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    def resolved_output_path(self, suffix: str = ".png") -> Path:
        """Return explicit output path or a stable default under output_dir."""
        if self.output_path is not None:
            return self.output_path
        return self.output_dir / f"{self.request_id}{suffix}"


class VisualDispatchResult(BaseModel):
    """Provider-neutral visual generation result."""

    request_id: str
    provider: VisualProvider
    status: VisualDispatchStatus
    output_path: Path | None = None
    log_path: Path
    prompt_used: str | None = None
    model_or_tool: str
    duration_ms: int = Field(ge=0)
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class VisualDispatchError(RuntimeError):
    """Raised when a visual request cannot be routed or generated."""


class VisualDispatchLogger:
    """Append-only JSONL logger for visual dispatch events."""

    def __init__(self, path: Path = DEFAULT_LOG_PATH) -> None:
        self.path = path

    def log(
        self,
        event: str,
        request: VisualDispatchRequest,
        *,
        provider: VisualProvider,
        status: str,
        result: VisualDispatchResult | None = None,
        error: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Append one structured event to the JSONL audit log."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "event": event,
            "request_id": request.request_id,
            "provider": provider.value,
            "status": status,
            "platform": request.platform,
            "asset_kind": request.asset_kind.value,
            "output_path": str(result.output_path if result else request.output_path or ""),
            "model_or_tool": result.model_or_tool if result else request.model,
            "requested_model": request.model,
            "selected_model": result.model_or_tool if result else request.model,
            "duration_ms": result.duration_ms if result else None,
            "error": error or (result.error if result else None),
            "prompt_preview": (request.prompt or "")[:240],
            "refined_source": (
                request.refined_source.log_summary() if request.refined_source else None
            ),
            "visual_route": (
                request.visual_route.model_dump(mode="json") if request.visual_route else None
            ),
            "visual_plan": request.visual_plan.log_summary() if request.visual_plan else None,
            "visual_judge": (
                result.metadata.get("visual_judge")
                if result and isinstance(result.metadata, dict)
                else None
            ),
            "metadata": request.metadata,
            "extra": extra or {},
            "created_at": datetime.now(UTC).isoformat(),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


async def _render_visual_bytes(spec: RenderSpec) -> bytes:
    """Import-late wrapper to avoid package import cycles and simplify tests."""
    from holus.visual import render_visual

    return await render_visual(spec)


class HtmlRenderProvider:
    """Deterministic HTML/PDF renderer backed by the existing visual engine."""

    provider = VisualProvider.HTML_RENDERER

    async def generate(self, request: VisualDispatchRequest) -> VisualDispatchResult:
        if request.render_spec is None and request.carousel_outline is None:
            msg = "html_renderer requires render_spec or carousel_outline"
            raise VisualDispatchError(msg)

        started = time.perf_counter()
        suffix = (
            ".pdf"
            if request.carousel_outline is not None
            else f".{request.render_spec.output_format.value}"
        )
        output_path = request.resolved_output_path(suffix)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        metadata: dict[str, Any]
        if request.carousel_outline is not None:
            from holus.visual.carousel_builder import build_carousel_pdf

            await asyncio.to_thread(build_carousel_pdf, request.carousel_outline, output_path)
            slides = request.carousel_outline.get("slides", [])
            metadata = {
                "template": "carousel/pdf",
                "format": "pdf",
                "slides": len(slides) if isinstance(slides, list) else None,
            }
        else:
            rendered = await _render_visual_bytes(request.render_spec)
            output_path.write_bytes(rendered)
            metadata = {
                "template": request.render_spec.template,
                "format": request.render_spec.output_format.value,
                "viewport": [
                    request.render_spec.viewport_width,
                    request.render_spec.viewport_height,
                ],
            }
        duration_ms = int((time.perf_counter() - started) * 1000)
        return VisualDispatchResult(
            request_id=request.request_id,
            provider=self.provider,
            status=VisualDispatchStatus.SUCCEEDED,
            output_path=output_path,
            log_path=request.log_path,
            prompt_used=None,
            model_or_tool="playwright_html_renderer",
            duration_ms=duration_ms,
            metadata=metadata,
        )


class CodexCliImageProvider:
    """Local/dev AI image provider using ``codex exec $imagegen``.

    This provider is intentionally opt-in through ``HOLUS_ENABLE_CODEX_IMAGE_PROVIDER=1``.
    It is useful for local LinkedIn image experiments, but should not become a
    production Pilaster replacement.
    """

    provider = VisualProvider.CODEX_CLI_IMAGE

    async def generate(self, request: VisualDispatchRequest) -> VisualDispatchResult:
        if os.getenv("HOLUS_ENABLE_CODEX_IMAGE_PROVIDER") != "1":
            msg = "codex_cli_image is disabled; set HOLUS_ENABLE_CODEX_IMAGE_PROVIDER=1 for local/dev use"
            raise VisualDispatchError(msg)
        prompt_used = request.prompt or (
            request.refined_source.prompt_brief() if request.refined_source else None
        )
        if not prompt_used:
            msg = "codex_cli_image requires prompt or refined_source"
            raise VisualDispatchError(msg)

        started = time.perf_counter()
        output_path = request.resolved_output_path(".png").resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        workspace = Path.cwd()
        prompt = self._build_prompt(request, output_path, prompt_used)
        command = ["codex", "-a", "never"]
        if request.model:
            command.extend(["-m", request.model])
        command.extend(
            [
                "exec",
                "-C",
                str(workspace),
                "-s",
                "workspace-write",
                prompt,
            ]
        )

        completed = await asyncio.to_thread(
            _run_command_with_timeout,
            command,
            timeout_seconds=request.timeout_seconds,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)

        stdout_tail = completed.stdout[-4000:] if completed.stdout else ""
        stderr_tail = completed.stderr[-4000:] if completed.stderr else ""
        recovered_from_nonzero_exit = completed.returncode != 0 and output_path.exists()
        if completed.returncode != 0 and not recovered_from_nonzero_exit:
            msg = f"codex exec failed with exit code {completed.returncode}"
            raise VisualDispatchError(f"{msg}: {stderr_tail or stdout_tail}")
        if not output_path.exists():
            msg = f"codex exec completed but did not create {output_path}"
            raise VisualDispatchError(msg)

        return VisualDispatchResult(
            request_id=request.request_id,
            provider=self.provider,
            status=VisualDispatchStatus.SUCCEEDED,
            output_path=output_path,
            log_path=request.log_path,
            prompt_used=prompt_used,
            model_or_tool=f"codex_cli:{request.model or 'default'}",
            duration_ms=duration_ms,
            metadata={
                "command": self._redacted_command(command),
                "stdout_tail": stdout_tail,
                "stderr_tail": stderr_tail,
                "dimensions": [request.width, request.height],
                "provider_exit_code": completed.returncode,
                "recovered_from_nonzero_exit": recovered_from_nonzero_exit,
            },
        )

    def _build_prompt(
        self,
        request: VisualDispatchRequest,
        output_path: Path,
        prompt_used: str,
    ) -> str:
        return (
            "$imagegen Generate a raster image for Holus social content.\n"
            f"Platform: {request.platform}\n"
            f"Asset kind: {request.asset_kind.value}\n"
            f"Dimensions: {request.width}x{request.height}\n"
            f"{request.visual_route.prompt_contract() if request.visual_route else ''}\n"
            f"{request.visual_plan.prompt_contract() if request.visual_plan else ''}\n"
            f"Creative brief:\n{prompt_used}\n"
            "Constraints: concrete editorial image, no generic AI wallpaper, no glowing brains, "
            "no robot mascot, no abstract network background, no readable text unless explicitly "
            "requested, no logos, no watermark, avoid pseudo-text glyphs, keep the image suitable "
            "for LinkedIn.\n"
            f"Save the final image into the workspace at {output_path.as_posix()} and report the saved path."
        )

    def _redacted_command(self, command: list[str]) -> list[str]:
        return ["<prompt>" if part.startswith("$imagegen") else part for part in command]


class AgyCliImageProvider:
    """Local/dev AI image provider using ``agy --print``.

    AGY is treated as a model-runner experiment path, not a production image
    backend. The provider succeeds only when the AGY run creates the requested
    PNG file, which keeps unclear model/tool behavior from being logged as a
    valid visual.
    """

    provider = VisualProvider.AGY_CLI_IMAGE

    async def generate(self, request: VisualDispatchRequest) -> VisualDispatchResult:
        if os.getenv("HOLUS_ENABLE_AGY_IMAGE_PROVIDER") != "1":
            msg = (
                "agy_cli_image is disabled; set HOLUS_ENABLE_AGY_IMAGE_PROVIDER=1 for local/dev use"
            )
            raise VisualDispatchError(msg)
        prompt_used = request.prompt or (
            request.refined_source.prompt_brief() if request.refined_source else None
        )
        if not prompt_used:
            msg = "agy_cli_image requires prompt or refined_source"
            raise VisualDispatchError(msg)

        started = time.perf_counter()
        output_path = request.resolved_output_path(".png").resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        prompt = self._build_prompt(request, output_path, prompt_used)
        command = ["agy", "--dangerously-skip-permissions"]
        if request.model:
            command.extend(["--model", request.model])
        command.extend(
            [
                "--print-timeout",
                f"{request.timeout_seconds}s",
                "--print",
                prompt,
            ]
        )

        completed = await asyncio.to_thread(
            _run_command_with_timeout,
            command,
            timeout_seconds=request.timeout_seconds + 5,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)

        stdout_tail = completed.stdout[-4000:] if completed.stdout else ""
        stderr_tail = completed.stderr[-4000:] if completed.stderr else ""
        if completed.returncode != 0:
            msg = f"agy --print failed with exit code {completed.returncode}"
            raise VisualDispatchError(f"{msg}: {stderr_tail or stdout_tail}")
        if not output_path.exists():
            msg = f"agy --print completed but did not create {output_path}"
            raise VisualDispatchError(msg)

        return VisualDispatchResult(
            request_id=request.request_id,
            provider=self.provider,
            status=VisualDispatchStatus.SUCCEEDED,
            output_path=output_path,
            log_path=request.log_path,
            prompt_used=prompt_used,
            model_or_tool=f"agy_cli:{request.model or 'default'}",
            duration_ms=duration_ms,
            metadata={
                "command": self._redacted_command(command),
                "stdout_tail": stdout_tail,
                "stderr_tail": stderr_tail,
                "dimensions": [request.width, request.height],
            },
        )

    def _build_prompt(
        self,
        request: VisualDispatchRequest,
        output_path: Path,
        prompt_used: str,
    ) -> str:
        return (
            "Generate one raster image for Holus social content. Use any available image "
            "generation capability in this AGY session. Do not publish or upload anything.\n"
            f"Platform: {request.platform}\n"
            f"Asset kind: {request.asset_kind.value}\n"
            f"Dimensions: {request.width}x{request.height}\n"
            f"{request.visual_route.prompt_contract() if request.visual_route else ''}\n"
            f"{request.visual_plan.prompt_contract() if request.visual_plan else ''}\n"
            f"Creative brief:\n{prompt_used}\n"
            "Constraints: concrete editorial image, no generic AI wallpaper, no glowing brains, "
            "no robot mascot, no abstract network background, no readable text unless explicitly "
            "requested, no logos, no watermark, avoid pseudo-text glyphs, keep the image suitable "
            "for LinkedIn.\n"
            f"Save the final PNG into the workspace at {output_path.as_posix()} and report the saved path."
        )

    def _redacted_command(self, command: list[str]) -> list[str]:
        return [
            "<prompt>" if part.startswith("Generate one raster image") else part for part in command
        ]


class VisualDispatcher:
    """Route visual requests to deterministic or AI-generation providers."""

    def __init__(
        self,
        *,
        logger: VisualDispatchLogger | None = None,
        providers: dict[VisualProvider, Any] | None = None,
    ) -> None:
        self._logger = logger
        self._providers = providers or {
            VisualProvider.HTML_RENDERER: HtmlRenderProvider(),
            VisualProvider.CODEX_CLI_IMAGE: CodexCliImageProvider(),
            VisualProvider.AGY_CLI_IMAGE: AgyCliImageProvider(),
        }

    async def dispatch(self, request: VisualDispatchRequest) -> VisualDispatchResult:
        started = time.perf_counter()
        request = self._with_visual_plan(request)
        provider = request.provider or self._infer_provider(request)
        logger = self._logger or VisualDispatchLogger(request.log_path)
        logger.log("visual_dispatch_started", request, provider=provider, status="started")
        if provider not in self._providers:
            msg = f"visual provider is not implemented: {provider.value}"
            result = VisualDispatchResult(
                request_id=request.request_id,
                provider=provider,
                status=VisualDispatchStatus.FAILED,
                output_path=request.output_path,
                log_path=request.log_path,
                prompt_used=request.prompt,
                model_or_tool=request.model or provider.value,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error=msg,
            )
            logger.log(
                "visual_dispatch_failed",
                request,
                provider=provider,
                status=result.status.value,
                result=result,
                error=msg,
            )
            return result

        attempt_request = request
        result: VisualDispatchResult | None = None
        for attempt in range(1, request.max_attempts + 1):
            try:
                result = await self._providers[provider].generate(attempt_request)
            except Exception as exc:
                result = VisualDispatchResult(
                    request_id=attempt_request.request_id,
                    provider=provider,
                    status=VisualDispatchStatus.FAILED,
                    output_path=attempt_request.output_path,
                    log_path=attempt_request.log_path,
                    prompt_used=attempt_request.prompt,
                    model_or_tool=attempt_request.model or provider.value,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    error=str(exc),
                    metadata={"attempt": attempt},
                )
                logger.log(
                    "visual_dispatch_failed",
                    attempt_request,
                    provider=provider,
                    status=result.status.value,
                    result=result,
                    error=str(exc),
                )
                return result

            result = self._with_visual_judge(result, attempt_request)
            judge = _judge_from_result(result)
            if judge is not None:
                logger.log(
                    "visual_judge_completed",
                    attempt_request,
                    provider=provider,
                    status=judge.verdict.value,
                    result=result,
                    extra={"attempt": attempt},
                )
                if judge.verdict == VisualJudgeVerdict.FAIL:
                    result = result.model_copy(
                        update={
                            "status": VisualDispatchStatus.FAILED,
                            "error": "; ".join(judge.reasons),
                        }
                    )
                    logger.log(
                        "visual_dispatch_failed",
                        attempt_request,
                        provider=provider,
                        status=result.status.value,
                        result=result,
                        error=result.error,
                    )
                    return result
                if (
                    judge.verdict == VisualJudgeVerdict.RETRY
                    and attempt < request.max_attempts
                    and attempt_request.visual_plan is not None
                ):
                    logger.log(
                        "visual_dispatch_retrying",
                        attempt_request,
                        provider=provider,
                        status="retrying",
                        result=result,
                        extra={"attempt": attempt, "next_attempt": attempt + 1},
                    )
                    attempt_request = self._retry_request(attempt_request, judge, attempt + 1)
                    continue
            break

        if result is None:
            msg = "visual dispatch completed without a provider result"
            raise VisualDispatchError(msg)

        logger.log(
            "visual_dispatch_completed",
            attempt_request,
            provider=provider,
            status=result.status.value,
            result=result,
        )
        self._write_sidecar(result)
        return result

    def _infer_provider(self, request: VisualDispatchRequest) -> VisualProvider:
        if request.render_spec is not None:
            return VisualProvider.HTML_RENDERER
        if request.carousel_outline is not None:
            return VisualProvider.HTML_RENDERER
        if request.prompt or request.refined_source is not None:
            return VisualProvider.CODEX_CLI_IMAGE
        msg = "visual request needs either provider, render_spec, or prompt"
        raise VisualDispatchError(msg)

    def _with_visual_plan(self, request: VisualDispatchRequest) -> VisualDispatchRequest:
        if request.visual_plan is not None:
            return request
        if request.refined_source is None or request.visual_route is None:
            return request
        return request.model_copy(
            update={
                "visual_plan": build_visual_production_plan(
                    request.refined_source,
                    request.visual_route,
                )
            }
        )

    def _write_sidecar(self, result: VisualDispatchResult) -> None:
        if result.output_path is None or result.status != VisualDispatchStatus.SUCCEEDED:
            return
        sidecar = result.output_path.with_suffix(result.output_path.suffix + ".dispatch.json")
        sidecar.write_text(
            json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def _with_visual_judge(
        self,
        result: VisualDispatchResult,
        request: VisualDispatchRequest,
    ) -> VisualDispatchResult:
        if not request.enable_visual_judge:
            return result
        decision = judge_visual_output(
            output_path=result.output_path,
            expected_width=request.width,
            expected_height=request.height,
            asset_kind=request.asset_kind.value,
            route=request.visual_route,
            plan=request.visual_plan,
            result_metadata=result.metadata,
        )
        metadata = {
            **result.metadata,
            "attempt": result.metadata.get("attempt", 1),
            "visual_judge": decision.model_dump(mode="json"),
        }
        return result.model_copy(update={"metadata": metadata})

    def _retry_request(
        self,
        request: VisualDispatchRequest,
        judge: VisualJudgeDecision,
        attempt: int,
    ) -> VisualDispatchRequest:
        update: dict[str, Any] = {
            "metadata": {
                **request.metadata,
                "retry_attempt": attempt,
                "retry_instruction": judge.retry_instruction,
                "previous_judge": judge.log_summary(),
            },
        }
        if request.visual_plan is not None:
            update["visual_plan"] = mutate_visual_plan_for_retry(
                request.visual_plan,
                judge,
                attempt=attempt,
            )
        if request.output_path is not None:
            update["output_path"] = _attempt_output_path(request.output_path, attempt)
        return request.model_copy(update=update)


def _judge_from_result(result: VisualDispatchResult) -> VisualJudgeDecision | None:
    raw = result.metadata.get("visual_judge") if isinstance(result.metadata, dict) else None
    if not isinstance(raw, dict):
        return None
    return VisualJudgeDecision.model_validate(raw)


def _attempt_output_path(output_path: Path, attempt: int) -> Path:
    return output_path.with_name(f"{output_path.stem}.retry{attempt}{output_path.suffix}")
