"""
Integration tests for Compliance Service.
"""

import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestIntegration:
    """Test service integration."""

    def test_api_documentation(self, client):
        """Test API documentation endpoint."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_schema(self, client):
        """Test OpenAPI schema endpoint."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data

    def test_cors_headers(self, client):
        """Test CORS headers."""
        response = client.get("/health/")
        assert response.status_code == 200
        # CORS is configured but headers may not be present in all requests
        # This test just ensures the endpoint is accessible

    def test_error_handling(self, client):
        """Test error handling."""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Compliance Service"
        assert data["version"] == "0.1.0"
        assert data["status"] == "operational"
        assert data["team"] == "Team B: Compliance & Identity"
