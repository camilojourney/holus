"""Base class for all Content Factory specialist creators.

Every specialist inherits from :class:`BaseSpecialist` and implements the
:meth:`create` abstract method. The base class enforces:

- A ``format_type`` class variable so the router can look up specialists by format.
- A ``quality_threshold`` that the eval gate uses to decide pass/fail.
- A ``_make_piece`` helper to reduce boilerplate when constructing a
  :class:`~holus.agents.content_factory.models.ContentPiece`.
"""

from __future__ import annotations

import abc
import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

from ..models import ContentIdea, ContentPiece, FormatType


class BaseSpecialist(abc.ABC):
    """Abstract base for all specialist content creators.

    Subclasses must:
    - Set ``format_type`` as a class variable.
    - Implement the ``create`` coroutine.

    The ``quality_threshold`` (0-100) controls the minimum score a piece must
    achieve from each reviewer to be considered passing. Override in subclasses
    when a format warrants a higher or lower bar.
    """

    #: The format this specialist produces.  Override in every subclass.
    format_type: ClassVar[FormatType]

    #: Minimum reviewer score (0-100) for a piece to pass the eval gate.
    quality_threshold: int = 70

    @abc.abstractmethod
    async def create(self, idea: ContentIdea, context: dict[str, Any]) -> ContentPiece:
        """Create a content piece for the given idea.

        Args:
            idea: The :class:`ContentIdea` to create content for.
            context: Arbitrary context dict that may contain brand identity,
                product data, analytics, platform knowledge, and a Claude
                client.  Specialists should use ``context.get(key)`` with
                safe defaults — they must not raise if a key is absent.

        Returns:
            A fully-populated :class:`ContentPiece` with ``raw_content``
            serialised as a JSON string.
        """

    def _make_piece(
        self,
        idea: ContentIdea,
        raw_content: str,
        model_used: str = "",
    ) -> ContentPiece:
        """Construct a :class:`ContentPiece` from raw specialist output.

        Args:
            idea: The originating content idea.
            raw_content: Serialised JSON string (the specialist's structured output).
            model_used: Claude model alias used for generation (optional).

        Returns:
            A new :class:`ContentPiece` in ``draft`` status.
        """
        return ContentPiece(
            piece_id=str(uuid.uuid4()),
            format=self.format_type,
            idea=idea,
            raw_content=raw_content,
            status="draft",
            created_at=datetime.now(UTC).isoformat(),
            model_used=model_used,
        )
