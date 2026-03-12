"""Platform framers for the Content Factory v2 (Spec 024).

Each framer adapts specialist output (raw_content JSON) into a
:class:`~holus.agents.content_factory.models.PlatformAdaptation` — a
platform-ready text string with metadata, char count, and media requirements.

Framers implement :class:`BasePlatformFramer` and are selected by the
pipeline based on the target platform returned by the router.
"""

from .base import BasePlatformFramer
from .facebook import FacebookFramer
from .instagram import InstagramFramer
from .linkedin import LinkedInFramer
from .threads import ThreadsFramer
from .twitter import TwitterFramer

__all__ = [
    "BasePlatformFramer",
    "FacebookFramer",
    "InstagramFramer",
    "LinkedInFramer",
    "ThreadsFramer",
    "TwitterFramer",
]
