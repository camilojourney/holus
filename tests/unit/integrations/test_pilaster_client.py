"""Tests for the pilaster image generation API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from holus.integrations.pilaster import (
    Character,
    Experiment,
    ImageResult,
    PilasterClient,
    Prompt,
    StructuredRecipe,
    Template,
)


@pytest.fixture
def client():
    """Create a test client."""
    return PilasterClient(base_url="http://localhost:8200", api_key="test-key")


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient."""
    mock = AsyncMock()
    mock.get = AsyncMock()
    mock.post = AsyncMock()
    return mock


@pytest.fixture
def sample_recipe():
    """Create a sample StructuredRecipe."""
    return StructuredRecipe(
        subject="A cat wearing a space helmet",
        style="photorealistic",
        composition="centered, close-up",
        lighting="dramatic studio lighting",
        quality="ultra high",
        negative="blurry, low quality, deformed",
        dimensions="1024x1024",
    )


class TestGenerateImage:
    """Test image generation."""

    @pytest.mark.asyncio
    async def test_generate_image_success(
        self, client, mock_httpx_client, sample_recipe
    ):
        """Successful generate_image returns ImageResult."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "image_id": "img_001",
            "image_url": "https://r2.example.com/generated.png",
            "backend": "comfyui",
            "recipe": sample_recipe.model_dump(),
            "generation_time_seconds": 12.5,
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.generate_image(
                backend="comfyui", recipe=sample_recipe
            )

            assert isinstance(result, ImageResult)
            assert result.image_id == "img_001"
            assert result.image_url == "https://r2.example.com/generated.png"
            assert result.backend == "comfyui"
            assert result.generation_time_seconds == 12.5

    @pytest.mark.asyncio
    async def test_generate_image_sends_correct_payload(
        self, client, mock_httpx_client, sample_recipe
    ):
        """generate_image sends the right payload to the API."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "image_id": "img_002",
            "image_url": "https://r2.example.com/img.png",
            "backend": "replicate",
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            await client.generate_image(backend="replicate", recipe=sample_recipe)

            mock_httpx_client.post.assert_called_once()
            call_args = mock_httpx_client.post.call_args
            assert call_args[0][0] == "/api/v1/generate"
            payload = call_args[1]["json"]
            assert payload["backend"] == "replicate"
            assert payload["recipe"]["subject"] == "A cat wearing a space helmet"
            assert payload["recipe"]["style"] == "photorealistic"
            assert payload["recipe"]["negative"] == "blurry, low quality, deformed"

    @pytest.mark.asyncio
    async def test_generate_image_http_error(
        self, client, mock_httpx_client, sample_recipe
    ):
        """generate_image raises on HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )
        mock_httpx_client.post.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client), pytest.raises(httpx.HTTPStatusError):
            await client.generate_image(backend="comfyui", recipe=sample_recipe)


class TestGetCharacters:
    """Test character retrieval."""

    @pytest.mark.asyncio
    async def test_get_characters_success(self, client, mock_httpx_client):
        """get_characters returns list of Character models."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "character_id": "char_001",
                "name": "Luna",
                "description": "Anime-style space explorer",
                "lora_url": "https://r2.example.com/luna.safetensors",
                "reference_urls": ["https://r2.example.com/luna_ref.png"],
            },
            {
                "character_id": "char_002",
                "name": "Rex",
                "description": "Cyberpunk detective",
                "lora_url": None,
                "reference_urls": [],
            },
        ]
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.get_characters()

            assert len(result) == 2
            assert all(isinstance(c, Character) for c in result)
            assert result[0].name == "Luna"
            assert result[0].lora_url == "https://r2.example.com/luna.safetensors"
            assert result[1].name == "Rex"
            assert result[1].lora_url is None
            mock_httpx_client.get.assert_called_once_with("/api/v1/characters")

    @pytest.mark.asyncio
    async def test_get_characters_empty(self, client, mock_httpx_client):
        """get_characters returns empty list when no characters exist."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.get_characters()

            assert result == []


class TestGetTemplates:
    """Test template retrieval."""

    @pytest.mark.asyncio
    async def test_get_templates_no_filter(self, client, mock_httpx_client):
        """get_templates returns all templates without style filter."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "template_id": "tmpl_001",
                "name": "Product Shot",
                "style": "photorealistic",
                "description": "Clean product photography",
                "tags": ["product", "marketing"],
            },
            {
                "template_id": "tmpl_002",
                "name": "Anime Scene",
                "style": "anime",
                "description": "Anime-style illustration",
                "tags": ["anime", "illustration"],
            },
        ]
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.get_templates()

            assert len(result) == 2
            assert all(isinstance(t, Template) for t in result)
            assert result[0].name == "Product Shot"
            mock_httpx_client.get.assert_called_once_with(
                "/api/v1/templates", params={}
            )

    @pytest.mark.asyncio
    async def test_get_templates_with_style_filter(self, client, mock_httpx_client):
        """get_templates passes style filter as query param."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "template_id": "tmpl_002",
                "name": "Anime Scene",
                "style": "anime",
            },
        ]
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.get_templates(style="anime")

            assert len(result) == 1
            mock_httpx_client.get.assert_called_once_with(
                "/api/v1/templates", params={"style": "anime"}
            )


class TestQueryExperiments:
    """Test experiment querying."""

    @pytest.mark.asyncio
    async def test_query_experiments_success(self, client, mock_httpx_client):
        """query_experiments returns list of Experiment models."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "experiment_id": "exp_001",
                "query": "cat portrait",
                "recipe": {"subject": "cat", "style": "oil painting"},
                "outcome": "success",
                "quality_score": 4.2,
                "created_at": "2026-03-15T10:00:00Z",
            },
        ]
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.query_experiments(
                query="cat portrait", outcome="success"
            )

            assert len(result) == 1
            assert isinstance(result[0], Experiment)
            assert result[0].outcome == "success"
            assert result[0].quality_score == 4.2
            mock_httpx_client.get.assert_called_once_with(
                "/api/v1/experiments",
                params={"query": "cat portrait", "outcome": "success"},
            )

    @pytest.mark.asyncio
    async def test_query_experiments_no_outcome(self, client, mock_httpx_client):
        """query_experiments works without outcome filter."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            await client.query_experiments(query="landscape")

            mock_httpx_client.get.assert_called_once_with(
                "/api/v1/experiments",
                params={"query": "landscape"},
            )


class TestGetSuccessfulPrompts:
    """Test successful prompt retrieval."""

    @pytest.mark.asyncio
    async def test_get_successful_prompts(self, client, mock_httpx_client):
        """get_successful_prompts returns list of Prompt models."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "prompt_id": "prm_001",
                "style": "photorealistic",
                "recipe": {"subject": "mountain sunset", "style": "photorealistic"},
                "quality_score": 4.8,
                "image_url": "https://r2.example.com/sunset.png",
            },
        ]
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.get_successful_prompts(style="photorealistic")

            assert len(result) == 1
            assert isinstance(result[0], Prompt)
            assert result[0].quality_score == 4.8
            mock_httpx_client.get.assert_called_once_with(
                "/api/v1/prompts/successful",
                params={"style": "photorealistic"},
            )


class TestHealth:
    """Test health check."""

    @pytest.mark.asyncio
    async def test_health_check(self, client, mock_httpx_client):
        """Health endpoint returns service status."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "healthy",
            "version": "2.1.0",
            "backends": {"comfyui": True, "replicate": True},
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.health()

            assert result["status"] == "healthy"
            assert result["backends"]["comfyui"] is True
            mock_httpx_client.get.assert_called_once_with("/api/v1/health")


class TestErrorHandling:
    """Test error handling across client methods."""

    @pytest.mark.asyncio
    async def test_timeout_on_generate_image(
        self, client, mock_httpx_client, sample_recipe
    ):
        """generate_image raises on timeout."""
        mock_httpx_client.post.side_effect = httpx.ReadTimeout("Timed out")

        with patch.object(client, "client", mock_httpx_client), pytest.raises(httpx.ReadTimeout):
            await client.generate_image.__wrapped__(client, backend="comfyui", recipe=sample_recipe)

    @pytest.mark.asyncio
    async def test_connection_error_on_generate_image(
        self, client, mock_httpx_client, sample_recipe
    ):
        """generate_image raises on connection error."""
        mock_httpx_client.post.side_effect = httpx.ConnectError("Connection refused")

        with patch.object(client, "client", mock_httpx_client), pytest.raises(httpx.ConnectError):
            await client.generate_image.__wrapped__(client, backend="comfyui", recipe=sample_recipe)

    @pytest.mark.asyncio
    async def test_404_on_get_characters(self, client, mock_httpx_client):
        """get_characters raises on 404."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client), pytest.raises(httpx.HTTPStatusError):
            await client.get_characters.__wrapped__(client)

    @pytest.mark.asyncio
    async def test_5xx_on_get_templates(self, client, mock_httpx_client):
        """get_templates raises on 500 server error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Internal Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client), pytest.raises(httpx.HTTPStatusError):
            await client.get_templates.__wrapped__(client, style="anime")

    @pytest.mark.asyncio
    async def test_4xx_on_query_experiments(self, client, mock_httpx_client):
        """query_experiments raises on 422 validation error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unprocessable Entity",
            request=MagicMock(),
            response=MagicMock(status_code=422),
        )
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client), pytest.raises(httpx.HTTPStatusError):
            await client.query_experiments.__wrapped__(client, query="test")

    @pytest.mark.asyncio
    async def test_timeout_on_get_successful_prompts(self, client, mock_httpx_client):
        """get_successful_prompts raises on timeout."""
        mock_httpx_client.get.side_effect = httpx.ReadTimeout("Timed out")

        with patch.object(client, "client", mock_httpx_client), pytest.raises(httpx.ReadTimeout):
            await client.get_successful_prompts.__wrapped__(client, style="photorealistic")

    @pytest.mark.asyncio
    async def test_connection_error_on_health(self, client, mock_httpx_client):
        """health raises on connection error (server down)."""
        mock_httpx_client.get.side_effect = httpx.ConnectError("Connection refused")

        with patch.object(client, "client", mock_httpx_client), pytest.raises(httpx.ConnectError):
            await client.health()


class TestRetryBehavior:
    """Test tenacity retry on transient errors."""

    @pytest.mark.asyncio
    async def test_retries_on_http_status_error(self, client, mock_httpx_client):
        """Client retries on HTTPStatusError then succeeds."""
        error_response = MagicMock()
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=503),
        )

        success_response = MagicMock()
        success_response.json.return_value = [
            {
                "character_id": "char_001",
                "name": "Luna",
            },
        ]
        success_response.raise_for_status = MagicMock()

        mock_httpx_client.get.side_effect = [error_response, success_response]

        with patch.object(client, "client", mock_httpx_client):
            result = await client.get_characters()

            assert len(result) == 1
            assert mock_httpx_client.get.call_count == 2


class TestClientLifecycle:
    """Test client lifecycle."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Client works as async context manager."""
        async with PilasterClient(api_key="test-key") as c:
            assert c.client is not None

    @pytest.mark.asyncio
    async def test_close(self, client):
        """Client can be closed manually."""
        await client.close()


class TestModels:
    """Test Pydantic models."""

    def test_structured_recipe_defaults(self):
        """StructuredRecipe has sensible defaults."""
        recipe = StructuredRecipe(subject="A cat", style="anime")
        assert recipe.composition == ""
        assert recipe.lighting == ""
        assert recipe.quality == "high"
        assert recipe.negative == ""
        assert recipe.dimensions == "1024x1024"

    def test_structured_recipe_full(self):
        """StructuredRecipe accepts all fields."""
        recipe = StructuredRecipe(
            subject="A warrior",
            style="oil painting",
            composition="full body, standing",
            lighting="golden hour",
            quality="masterpiece",
            negative="ugly, deformed",
            dimensions="768x1024",
        )
        assert recipe.subject == "A warrior"
        assert recipe.dimensions == "768x1024"

    def test_character_defaults(self):
        """Character has sensible defaults."""
        char = Character(character_id="c1", name="Test")
        assert char.description == ""
        assert char.lora_url is None
        assert char.reference_urls == []
        assert char.metadata == {}

    def test_template_defaults(self):
        """Template has sensible defaults."""
        tmpl = Template(template_id="t1", name="Test", style="anime")
        assert tmpl.description == ""
        assert tmpl.recipe == {}
        assert tmpl.tags == []

    def test_image_result_defaults(self):
        """ImageResult has sensible defaults."""
        result = ImageResult(
            image_id="i1",
            image_url="https://example.com/img.png",
            backend="comfyui",
        )
        assert result.generation_time_seconds == 0.0
        assert result.metadata == {}

    def test_experiment_defaults(self):
        """Experiment has sensible defaults."""
        exp = Experiment(experiment_id="e1", query="test")
        assert exp.outcome == ""
        assert exp.quality_score == 0.0

    def test_prompt_defaults(self):
        """Prompt has sensible defaults."""
        prompt = Prompt(prompt_id="p1", style="anime")
        assert prompt.quality_score == 0.0
        assert prompt.image_url is None
