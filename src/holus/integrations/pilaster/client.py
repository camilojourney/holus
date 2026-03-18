"""Client for the pilaster image generation local API.

Calls the FastAPI server at http://localhost:8200 (or PILASTER_API_BASE_URL).
Handles image generation, character/template retrieval, experiment querying,
and successful prompt lookup.

Holus sends structured recipes — never flat prompt strings — to Pilaster.
Pilaster assembles the recipe into whatever format the backend needs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from types import TracebackType

import httpx
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class StructuredRecipe(BaseModel):
    """Structured prompt recipe for image generation.

    Decomposes image intent into independent dimensions.
    Pilaster assembles the recipe into whatever format the backend needs
    (ComfyUI nodes, DALL-E prompt, Imagen prompt, etc.).
    """

    subject: str
    style: str
    composition: str = ""
    lighting: str = ""
    quality: str = "high"
    negative: str = ""
    dimensions: str = "1024x1024"


class ImageResult(BaseModel):
    """Result from an image generation request."""

    image_id: str
    image_url: str
    backend: str
    recipe: dict[str, Any] = Field(default_factory=dict)
    generation_time_seconds: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class Character(BaseModel):
    """A character from Pilaster's character registry."""

    character_id: str
    name: str
    description: str = ""
    lora_url: str | None = None
    reference_urls: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Template(BaseModel):
    """A reusable generation template from Pilaster."""

    template_id: str
    name: str
    style: str
    description: str = ""
    recipe: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class Experiment(BaseModel):
    """An experiment record from Pilaster's experiment memory."""

    experiment_id: str
    query: str
    recipe: dict[str, Any] = Field(default_factory=dict)
    outcome: str = ""  # success|failure|mixed
    quality_score: float = 0.0
    created_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class Prompt(BaseModel):
    """A successful prompt from Pilaster's history."""

    prompt_id: str
    style: str
    recipe: dict[str, Any] = Field(default_factory=dict)
    quality_score: float = 0.0
    image_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PilasterClient:
    """Async client for the pilaster image generation API."""

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:8200",
        api_key: str,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-API-Key": api_key},
            timeout=60.0,  # Image generation can be slow
        )

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def generate_image(
        self,
        backend: str,
        recipe: StructuredRecipe,
    ) -> ImageResult:
        """Generate an image using a structured recipe.

        Calls POST /api/v1/generate on the pilaster server.
        The backend parameter selects the generation engine
        (comfyui, replicate, runway, etc.).

        Raises:
            httpx.HTTPError: If the API request fails.
        """
        payload: dict[str, Any] = {
            "backend": backend,
            "recipe": recipe.model_dump(),
        }
        response = await self.client.post("/api/v1/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        return ImageResult.model_validate(data)

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def get_characters(self) -> list[Character]:
        """Fetch all characters from Pilaster's character registry.

        Calls GET /api/v1/characters.
        """
        response = await self.client.get("/api/v1/characters")
        response.raise_for_status()
        data = response.json()
        return [Character.model_validate(c) for c in data]

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def get_templates(
        self,
        style: str | None = None,
    ) -> list[Template]:
        """Fetch generation templates, optionally filtered by style.

        Calls GET /api/v1/templates.
        """
        params: dict[str, Any] = {}
        if style:
            params["style"] = style
        response = await self.client.get("/api/v1/templates", params=params)
        response.raise_for_status()
        data = response.json()
        return [Template.model_validate(t) for t in data]

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def query_experiments(
        self,
        query: str,
        outcome: str | None = None,
    ) -> list[Experiment]:
        """Query Pilaster's experiment memory.

        Calls GET /api/v1/experiments.
        """
        params: dict[str, Any] = {"query": query}
        if outcome:
            params["outcome"] = outcome
        response = await self.client.get("/api/v1/experiments", params=params)
        response.raise_for_status()
        data = response.json()
        return [Experiment.model_validate(e) for e in data]

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def get_successful_prompts(
        self,
        style: str | None = None,
    ) -> list[Prompt]:
        """Fetch successful prompts from Pilaster's history.

        Calls GET /api/v1/prompts/successful.
        """
        params: dict[str, Any] = {}
        if style:
            params["style"] = style
        response = await self.client.get("/api/v1/prompts/successful", params=params)
        response.raise_for_status()
        data = response.json()
        return [Prompt.model_validate(p) for p in data]

    async def health(self) -> dict[str, Any]:
        """Check pilaster API health.

        Calls GET /api/v1/health.
        """
        response = await self.client.get("/api/v1/health")
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self) -> PilasterClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()
