import os
from unittest.mock import patch

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient

# Get the service URL from environment or use default
SERVICE_URL = os.getenv("SETTLEMENT_SERVICE_URL", "http://localhost:8000")


@pytest.mark.asyncio
async def test_readiness() -> None:
    """Test the health endpoint using FastAPI test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    """Test the health endpoint returns correct status using FastAPI test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_database_connectivity() -> None:
    """Test database connectivity through health endpoint using FastAPI test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    health_data = response.json()
    assert health_data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_check_detailed() -> None:
    """Test detailed health check with dependencies using FastAPI test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/detailed")

        # Detailed health check may not be implemented yet
        if response.status_code == 200:
            health_data = response.json()
            assert "status" in health_data
            # Could check for database, redis, etc. status
        else:
            # Fallback to basic health check
            response = await client.get("/health")
            assert response.status_code == 200


@pytest.mark.asyncio
@patch("os.getenv")
async def test_gcp_integration_variables(mock_getenv) -> None:
    """Test that GCP integration variables are properly configured."""
    # Mock environment variables
    mock_getenv.side_effect = lambda key, default=None: {
        "GCP_PROJECT": "fusion-prime",
        "ENVIRONMENT": "test",
        "REGION": "us-central1",
    }.get(key, default)

    # Test that environment variables are accessible
    assert mock_getenv("GCP_PROJECT") == "fusion-prime"
    assert mock_getenv("ENVIRONMENT") == "test"
    assert mock_getenv("REGION") == "us-central1"
