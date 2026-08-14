"""In-process demo adapter that satisfies the public generation contract.

Never calls an external endpoint, loads a secret, or contacts Genpeli.
"""

from __future__ import annotations

from uuid import uuid4

from holus.generation.public_contract import (
    CreateGenerationRequest,
    CreateGenerationResponse,
    GenerationJobStatus,
    GenerationSource,
    PreviewReference,
    PublicGenerationStatus,
)

_DEMO_SOURCE: GenerationSource = "demo"

_READY_MESSAGE = "Demonstration complete. Preview is a local placeholder, not a generated artifact."
_ERROR_MESSAGE = "Generation is unavailable in this demonstration. No live job was created."
_QUEUED_MESSAGE = "Queued in the local Holus demo adapter. No live generation request was sent."
_GENERATING_MESSAGE = "Local demonstration is advancing. Genpeli was not contacted."


def _placeholder_preview() -> PreviewReference:
    return PreviewReference(
        availability="local_placeholder",
        label="Local placeholder — not an artifact URL",
    )


def _unavailable_preview() -> PreviewReference:
    return PreviewReference(
        availability="unavailable",
        label="Preview unavailable in this demonstration",
    )


class DemoGenerationAdapter:
    """Local lifecycle only: queued → generating → ready|error."""

    def __init__(self) -> None:
        self._jobs: dict[str, GenerationJobStatus] = {}
        self._outcomes: dict[str, PublicGenerationStatus] = {}

    def create(
        self,
        _request: CreateGenerationRequest,
        *,
        outcome: PublicGenerationStatus = "ready",
    ) -> CreateGenerationResponse:
        if outcome not in {"ready", "error"}:
            raise ValueError("Demo outcome must be 'ready' or 'error'")
        token = uuid4().hex[:12]
        request_id = f"holus-demo-{token}"
        job_id = f"holus-mapped-{token}"
        status = GenerationJobStatus(
            request_id=request_id,
            job_id=job_id,
            status="queued",
            stage="queued",
            progress=0.0,
            user_message=_QUEUED_MESSAGE,
            preview=_unavailable_preview(),
            source=_DEMO_SOURCE,
        )
        self._jobs[request_id] = status
        self._outcomes[request_id] = outcome
        return CreateGenerationResponse(
            request_id=request_id,
            job_id=job_id,
            status="queued",
            source=_DEMO_SOURCE,
        )

    def get(self, request_id: str) -> GenerationJobStatus | None:
        return self._jobs.get(request_id)

    def advance(self, request_id: str) -> GenerationJobStatus:
        current = self._jobs[request_id]
        if current.status in {"ready", "error"}:
            return current
        outcome = self._outcomes[request_id]
        if current.status == "queued":
            nxt = current.model_copy(
                update={
                    "status": "generating",
                    "stage": "generating",
                    "progress": 0.45,
                    "user_message": _GENERATING_MESSAGE,
                    "preview": _unavailable_preview(),
                }
            )
        elif outcome == "error":
            nxt = current.model_copy(
                update={
                    "status": "error",
                    "stage": "error",
                    "progress": 0.45,
                    "user_message": _ERROR_MESSAGE,
                    "preview": _unavailable_preview(),
                }
            )
        else:
            nxt = current.model_copy(
                update={
                    "status": "ready",
                    "stage": "ready",
                    "progress": 1.0,
                    "user_message": _READY_MESSAGE,
                    "preview": _placeholder_preview(),
                }
            )
        self._jobs[request_id] = nxt
        return nxt

    def lifecycle(self, request_id: str) -> list[GenerationJobStatus]:
        """Return the remaining bounded stages, advancing in-memory state."""
        frames = [self._jobs[request_id]]
        while frames[-1].status not in {"ready", "error"}:
            frames.append(self.advance(request_id))
        return frames
