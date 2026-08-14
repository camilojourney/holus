"""Holus-owned public generation contract for a future authenticated BFF.

The browser never talks to Genpeli. The only future cross-service seam is a
Holus BFF that may create one mapped job, read that job's restricted status,
and proxy its preview. This package is the typed contract plus a local demo
adapter. It does not perform HTTP, load secrets, or expose operator controls.
"""

from holus.generation.demo_adapter import DemoGenerationAdapter
from holus.generation.public_contract import (
    CONTRACT_VERSION,
    FORBIDDEN_PUBLIC_FIELDS,
    CreateGenerationRequest,
    CreateGenerationResponse,
    GenerationJobStatus,
    PreviewReference,
)

__all__ = [
    "CONTRACT_VERSION",
    "FORBIDDEN_PUBLIC_FIELDS",
    "CreateGenerationRequest",
    "CreateGenerationResponse",
    "DemoGenerationAdapter",
    "GenerationJobStatus",
    "PreviewReference",
]
