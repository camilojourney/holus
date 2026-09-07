"""Contract tests for completed, deterministic execution facts."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from holus.agents import stage_execution
from holus.agents.stage_execution import StageExecution, StageExecutionRecorder, StageWiringError


def test_records_measured_timing_result_and_immutable_round_trip(monkeypatch):
    clock = iter([1.0, 1.125])
    monkeypatch.setattr(stage_execution, "perf_counter", lambda: next(clock))
    sink = []
    recorder = StageExecutionRecorder("run", "group", sink)

    def upper(value):
        return value.upper()

    result = recorder.run("local_copy", upper, "hello", piece_id="piece")
    assert result == "HELLO"
    [record] = sink
    assert record == recorder.records[0]
    assert record.latency_ms == 125
    assert record.execution_id == "run:1"
    assert record.started_at <= record.finished_at <= datetime.now(UTC)
    assert record.status == "success"
    assert StageExecution.model_validate_json(record.model_dump_json()) == record
    with pytest.raises(ValidationError):
        record.status = "error"


@pytest.mark.parametrize(
    "executor, code",
    [
        (None, "non_callable_stage"),
        (str.upper, "unidentified_stage_executor"),
    ],
)
def test_missing_function_is_a_wiring_error_not_an_execution(executor, code):
    recorder = StageExecutionRecorder("run", "group")
    with pytest.raises(StageWiringError, match=f"{code}:missing"):
        recorder.run("missing", executor)
    assert recorder.records == []


def test_cancellation_is_recorded_and_reraised_without_message():
    recorder = StageExecutionRecorder("run", "group")

    def cancelled():
        raise KeyboardInterrupt("not trace metadata")

    with pytest.raises(KeyboardInterrupt):
        recorder.run("interrupted", cancelled)
    [record] = recorder.records
    assert record.status == "error" and record.error_code == "KeyboardInterrupt"
    assert "not trace metadata" not in record.model_dump_json()
    assert record.model is None and record.prompt_sha is None
