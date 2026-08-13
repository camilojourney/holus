"""Local durable outbox for idempotent Holus Social API dispatches."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from holus.lineage.models import stable_hash

DispatchOperation = Literal["publish", "schedule"]


@dataclass(frozen=True)
class DispatchIntent:
    """A durable pre-side-effect request keyed by content revision and operation."""

    request_id: str
    operation: DispatchOperation
    piece_id: str
    revision: str
    payload: dict[str, Any]
    status: str
    created_at: str
    external_id: str | None = None
    external_status: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> DispatchIntent:
        return cls(
            request_id=str(raw["request_id"]),
            operation=raw["operation"],
            piece_id=str(raw["piece_id"]),
            revision=str(raw["revision"]),
            payload=dict(raw["payload"]),
            status=str(raw["status"]),
            created_at=str(raw["created_at"]),
            external_id=raw.get("external_id"),
            external_status=raw.get("external_status"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "operation": self.operation,
            "piece_id": self.piece_id,
            "revision": self.revision,
            "payload": self.payload,
            "status": self.status,
            "created_at": self.created_at,
            "external_id": self.external_id,
            "external_status": self.external_status,
        }


class DispatchOutbox:
    """Small filesystem outbox; reservation is atomic before an external call."""

    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)
        self.lock_path = self.directory / ".outbox.lock"

    def reserve(
        self,
        *,
        operation: DispatchOperation,
        piece_id: str,
        revision: str,
        payload: dict[str, Any],
    ) -> tuple[DispatchIntent, bool]:
        """Return the one intent for a content revision, creating it atomically if needed."""
        key = stable_hash(
            {
                "operation": operation,
                "piece_id": piece_id,
                "revision": revision,
                "scheduled_at": payload.get("scheduled_at") if operation == "schedule" else None,
            }
        )
        path = self.directory / f"{key}.json"
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                if path.exists():
                    return DispatchIntent.from_dict(
                        json.loads(path.read_text(encoding="utf-8"))
                    ), False
                intent = DispatchIntent(
                    request_id=f"dispatch-{key[:32]}",
                    operation=operation,
                    piece_id=piece_id,
                    revision=revision,
                    payload=payload,
                    status="intent_recorded",
                    created_at=datetime.now(UTC).isoformat(),
                )
                _atomic_json_replace(path, intent.to_dict())
                return intent, True
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def find(
        self,
        *,
        operation: DispatchOperation,
        piece_id: str,
        revision: str,
        payload: dict[str, Any],
    ) -> DispatchIntent | None:
        key = stable_hash(
            {
                "operation": operation,
                "piece_id": piece_id,
                "revision": revision,
                "scheduled_at": payload.get("scheduled_at") if operation == "schedule" else None,
            }
        )
        path = self.directory / f"{key}.json"
        if not path.exists():
            return None
        return DispatchIntent.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def mark_result(
        self,
        intent: DispatchIntent,
        *,
        status: str,
        external_id: str | None,
        external_status: str | None = None,
    ) -> DispatchIntent:
        """Atomically persist the observed result; callers retry the same request ID."""
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                path = self.directory / f"{intent.request_id.removeprefix('dispatch-')}.json"
                # The filename is key hash; fall back to a bounded scan only for a future ID format change.
                if not path.exists():
                    for candidate in self.directory.glob("*.json"):
                        raw = json.loads(candidate.read_text(encoding="utf-8"))
                        if raw.get("request_id") == intent.request_id:
                            path = candidate
                            break
                updated = DispatchIntent(
                    **(
                        intent.to_dict()
                        | {
                            "status": status,
                            "external_id": external_id,
                            "external_status": external_status,
                        }
                    )
                )
                _atomic_json_replace(path, updated.to_dict())
                return updated
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _atomic_json_replace(path: Path, value: dict[str, Any]) -> None:
    """Durably replace a state projection in its own directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary.exists():
            temporary.unlink()
