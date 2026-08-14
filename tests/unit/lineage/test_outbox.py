"""Adversarial tests for the local dispatch outbox."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from holus.lineage.outbox import DispatchOutbox

if TYPE_CHECKING:
    from pathlib import Path


def test_outbox_reserves_one_idempotency_key_across_concurrent_retries(tmp_path: Path) -> None:
    outbox = DispatchOutbox(tmp_path / "outbox")

    def reserve() -> tuple[str, bool]:
        intent, created = outbox.reserve(
            operation="publish",
            piece_id="piece-1",
            revision="revision-1",
            payload={"platforms": ["linkedin"]},
        )
        return intent.request_id, created

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: reserve(), range(16)))
    assert len({request_id for request_id, _ in results}) == 1
    assert sum(created for _, created in results) == 1


def test_outbox_result_survives_and_reuses_same_request(tmp_path: Path) -> None:
    outbox = DispatchOutbox(tmp_path / "outbox")
    intent, _ = outbox.reserve(
        operation="schedule", piece_id="piece-1", revision="revision-1", payload={"x": 1}
    )
    outbox.mark_result(intent, status="accepted", external_id="schedule-1")
    retried, created = outbox.reserve(
        operation="schedule", piece_id="piece-1", revision="revision-1", payload={"x": 1}
    )
    assert created is False
    assert retried.request_id == intent.request_id
    assert retried.status == "accepted"
    assert retried.external_id == "schedule-1"


def test_schedule_time_is_part_of_outbox_identity(tmp_path: Path) -> None:
    outbox = DispatchOutbox(tmp_path / "outbox")
    first, first_created = outbox.reserve(
        operation="schedule",
        piece_id="piece-1",
        revision="revision-1",
        payload={"scheduled_at": "2026-08-13T10:00:00Z"},
    )
    second, second_created = outbox.reserve(
        operation="schedule",
        piece_id="piece-1",
        revision="revision-1",
        payload={"scheduled_at": "2026-08-14T10:00:00Z"},
    )
    assert first_created is True
    assert second_created is True
    assert second.request_id != first.request_id
