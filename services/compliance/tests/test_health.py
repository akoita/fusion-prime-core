"""
Unit tests for Compliance Service health endpoints.
"""

import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self, client):
        """Test basic health check."""
        response = client.get("/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "services" in data

    def test_readiness_check(self, client):
        """Test readiness check."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "timestamp" in data

    def test_liveness_check(self, client):
        """Test liveness check."""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data

    def test_detailed_health_check(self, client):
        """Test detailed health check."""
        response = client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"  # Expected since services are not initialized
        assert "timestamp" in data
        assert "version" in data
        assert "services" in data
        assert "dependencies" in data
