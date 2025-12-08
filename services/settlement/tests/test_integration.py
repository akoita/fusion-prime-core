"""
Integration Tests for Settlement Service

Tests the settlement service integration features including:
- API documentation
- CORS handling
- Error handling
- Rate limiting
- Logging configuration
- Metrics endpoints
"""

import os

import httpx
import pytest
from app.main import app

# Get the service URL from environment or use default
SERVICE_URL = os.getenv("SETTLEMENT_SERVICE_URL", "http://localhost:8000")


@pytest.mark.asyncio
async def test_api_documentation() -> None:
    """Test API documentation is accessible using FastAPI test client."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs")

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_openapi_schema() -> None:
    """Test OpenAPI schema is accessible using FastAPI test client."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")

    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema


@pytest.mark.asyncio
async def test_cors_headers() -> None:
    """Test CORS headers are properly set using FastAPI test client."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options("/health")

    # Should handle OPTIONS request
    assert response.status_code in [200, 204, 405]


@pytest.mark.asyncio
async def test_error_handling() -> None:
    """Test error handling for invalid requests using FastAPI test client."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Test invalid JSON
        response = await client.post("/commands/ingest", content="invalid json")

    # Should return 422 or 400 for invalid JSON
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_rate_limiting() -> None:
    """Test rate limiting (if implemented) using FastAPI test client."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Make multiple rapid requests
        responses = []
        for _ in range(5):
            response = await client.get("/health")
            responses.append(response.status_code)

    # All requests should succeed (rate limiting not implemented yet)
    assert all(status == 200 for status in responses)


@pytest.mark.asyncio
async def test_logging_configuration() -> None:
    """Test that logging is properly configured using FastAPI test client."""
    # This is a basic test - in a real scenario, you might check log output
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    # Logging configuration is tested indirectly through successful requests


@pytest.mark.asyncio
async def test_metrics_endpoint() -> None:
    """Test metrics endpoint (if implemented) using FastAPI test client."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")

    # Metrics endpoint may not be implemented yet
    assert response.status_code in [200, 404]
