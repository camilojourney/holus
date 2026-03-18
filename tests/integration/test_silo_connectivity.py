"""Integration tests for silo service connectivity.

Hits health endpoints for all three silos. Skips gracefully if services
are not running locally. Run with: uv run pytest tests/integration/ -v -m integration
"""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.integration
class TestSiloConnectivity:
    """Verify that silo services are reachable via their health endpoints."""

    @pytest.mark.asyncio
    async def test_social_media_health(self):
        """Social media API (port 8000) responds to health check."""
        async with httpx.AsyncClient(
            base_url="http://localhost:8000", timeout=5.0
        ) as client:
            try:
                response = await client.get("/api/v1/health")
            except httpx.ConnectError:
                pytest.skip("Social media API not running on localhost:8000")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data or "platforms" in data

    @pytest.mark.asyncio
    async def test_genpeli_health(self):
        """Genpeli API (port 8100) responds to health check."""
        async with httpx.AsyncClient(
            base_url="http://localhost:8100", timeout=5.0
        ) as client:
            try:
                response = await client.get("/api/v1/health")
            except httpx.ConnectError:
                pytest.skip("Genpeli API not running on localhost:8100")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    @pytest.mark.asyncio
    async def test_pilaster_health(self):
        """Pilaster API (port 8200) responds to health check."""
        async with httpx.AsyncClient(
            base_url="http://localhost:8200", timeout=5.0
        ) as client:
            try:
                response = await client.get("/api/v1/health")
            except httpx.ConnectError:
                pytest.skip("Pilaster API not running on localhost:8200")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
