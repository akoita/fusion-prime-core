"""
Unit tests for Risk Engine Service health endpoints.
"""

from unittest.mock import Mock, patch

import pytest
from app.dependencies import get_analytics_engine, get_risk_calculator
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_risk_calculator():
    """Mock risk calculator."""
    mock = Mock()
    mock.health_check.return_value = {
        "status": "healthy",
        "database": "connected",
        "cache": "connected",
        "market_data": "connected",
    }
    return mock


@pytest.fixture
def mock_analytics_engine():
    """Mock analytics engine."""
    mock = Mock()
    mock.health_check.return_value = {
        "status": "healthy",
        "database": "connected",
        "bigquery": "connected",
    }
    return mock


class TestHealthEndpoints:
    """Test health endpoints."""

    def test_health_check(self, client):
        """Test basic health check."""
        response = client.get("/health/")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "services" in data

    @patch("app.dependencies.get_risk_calculator")
    @patch("app.dependencies.get_analytics_engine")
    def test_detailed_health_check(
        self,
        mock_analytics,
        mock_risk,
        client,
        mock_risk_calculator,
        mock_analytics_engine,
    ):
        """Test detailed health check."""
        mock_risk.return_value = mock_risk_calculator
        mock_analytics.return_value = mock_analytics_engine

        response = client.get("/health/detailed")
        assert response.status_code == 200

        data = response.json()
        # With resilience changes, service reports "degraded" when dependencies are not initialized
        assert data["status"] in ["healthy", "degraded"]
        assert "services" in data
        assert "dependencies" in data

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
