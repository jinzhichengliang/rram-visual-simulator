"""S00 Bootstrap — API health endpoint test."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    """Health endpoint must return status=ok."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "phase" in data


@pytest.mark.asyncio
async def test_root_endpoint():
    """Root endpoint must return service info."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "RRAM Visual Simulator"


@pytest.mark.asyncio
async def test_no_rram_physics_in_s00():
    """S00 must not contain any RRAM state transition logic."""
    # This test verifies the bootstrap constraint: no business logic yet.
    # The API should only have health and root endpoints.
    routes = [route.path for route in app.routes]
    assert "/health" in routes
    assert "/" in routes
    # No simulation endpoints should exist yet
    assert "/api/session" not in routes
    assert "/api/session/{id}/step" not in routes
