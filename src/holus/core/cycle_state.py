"""State machine for a single resilient agent cycle."""

from __future__ import annotations

from enum import StrEnum


class CycleState(StrEnum):
    """High-level states for a marketing cycle."""

    STARTING = "starting"
    HEALTH_CHECK = "health_check"
    LOADING_STATE = "loading_state"
    OBSERVING = "observing"
    REASONING = "reasoning"
    CREATING = "creating"
    QUALITY_CHECK = "quality_check"
    POSTING = "posting"
    IMPROVING = "improving"
    SAVING_STATE = "saving_state"
    DONE = "done"
    FAILED = "failed"
