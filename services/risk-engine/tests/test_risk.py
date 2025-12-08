"""
Unit tests for Risk Engine Service risk calculation endpoints.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from app.dependencies import get_risk_calculator
from app.main import app
from app.models.risk import PortfolioRisk, RiskLevel, RiskScore
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_risk_calculator():
    """Mock risk calculator."""
    mock = Mock()

    # Mock portfolio risk calculation
    mock.calculate_portfolio_risk.return_value = PortfolioRisk(
        portfolio_id="test-portfolio",
        risk_score=RiskScore(score=50.0, level=RiskLevel.MEDIUM, confidence=0.85),
        var_1d=1000.0,
        var_7d=2500.0,
        var_30d=5000.0,
        cvar_1d=1200.0,
        cvar_7d=3000.0,
        cvar_30d=6000.0,
        correlation_matrix={
            "BTC": {"BTC": 1.0, "ETH": 0.7, "USDC": 0.1},
            "ETH": {"BTC": 0.7, "ETH": 1.0, "USDC": 0.1},
            "USDC": {"BTC": 0.1, "ETH": 0.1, "USDC": 1.0},
        },
        calculated_at=datetime.now(timezone.utc),
    )

    # Mock custom risk calculation
    mock.calculate_custom_risk.return_value = PortfolioRisk(
        portfolio_id="custom-portfolio",
        risk_score=RiskScore(score=60.0, level=RiskLevel.HIGH, confidence=0.90),
        var_1d=1500.0,
        var_7d=3500.0,
        var_30d=6000.0,
        cvar_1d=1800.0,
        cvar_7d=4000.0,
        cvar_30d=7000.0,
        correlation_matrix={
            "BTC": {"BTC": 1.0, "ETH": 0.7, "USDC": 0.1},
            "ETH": {"BTC": 0.7, "ETH": 1.0, "USDC": 0.1},
            "USDC": {"BTC": 0.1, "ETH": 0.1, "USDC": 1.0},
        },
        calculated_at=datetime.now(timezone.utc),
    )

    # Mock margin requirements
    mock.calculate_margin_requirements.return_value = {
        "user_id": "test-user",
        "total_margin": 10000.0,
        "initial_margin": 5000.0,
        "maintenance_margin": 3000.0,
        "available_margin": 15000.0,
        "margin_ratio": 0.67,
        "calculated_at": datetime.now(timezone.utc),
    }

    # Mock risk metrics
    mock.get_risk_metrics.return_value = {
        "portfolio_id": "test-portfolio",
        "risk_score": 50.0,
        "volatility": 0.15,
        "sharpe_ratio": 1.2,
        "max_drawdown": 0.08,
        "calculated_at": datetime.now(timezone.utc),
    }

    return mock


class TestRiskEndpoints:
    """Test risk calculation endpoints."""

    @patch("app.dependencies.get_risk_calculator")
    def test_get_portfolio_risk(self, mock_risk, client, mock_risk_calculator):
        """Test get portfolio risk endpoint."""
        mock_risk.return_value = mock_risk_calculator

        response = client.get("/risk/portfolio/test-portfolio")
        assert response.status_code == 200

        data = response.json()
        assert data["portfolio_id"] == "test-portfolio"
        assert "risk_score" in data
        assert "var_1d" in data
        assert "var_7d" in data
        assert "var_30d" in data

    @patch("app.dependencies.get_risk_calculator")
    def test_calculate_risk(self, mock_risk, client, mock_risk_calculator):
        """Test calculate risk endpoint."""
        mock_risk.return_value = mock_risk_calculator

        request_data = {
            "portfolio_id": "custom-portfolio",
            "assets": [
                {"symbol": "BTC", "amount": 1.0, "price": 50000.0},
                {"symbol": "ETH", "amount": 10.0, "price": 3000.0},
            ],
            "risk_model": "standard",
            "confidence_level": 0.95,
        }

        response = client.post("/risk/calculate", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["portfolio_id"] == "custom-portfolio"
        assert "risk_score" in data
        assert "var_1d" in data
        assert "var_7d" in data
        assert "var_30d" in data

    @patch("app.dependencies.get_risk_calculator")
    def test_get_margin_requirements(self, mock_risk, client, mock_risk_calculator):
        """Test get margin requirements endpoint."""
        mock_risk.return_value = mock_risk_calculator

        response = client.get("/risk/margin/test-user")
        assert response.status_code == 200

        data = response.json()
        assert data["user_id"] == "test-user"
        assert "total_margin" in data
        assert "initial_margin" in data
        assert "maintenance_margin" in data

    @patch("app.dependencies.get_risk_calculator")
    def test_get_risk_metrics(self, mock_risk, client, mock_risk_calculator):
        """Test get risk metrics endpoint."""
        mock_risk.return_value = mock_risk_calculator

        response = client.get("/risk/metrics?portfolio_id=test-portfolio&time_range=7d")
        assert response.status_code == 200

        data = response.json()
        assert "portfolio_id" in data
        assert "risk_score" in data
        assert "volatility" in data

    @patch("app.dependencies.get_risk_calculator")
    def test_create_risk_alert(self, mock_risk, client, mock_risk_calculator):
        """Test create risk alert endpoint."""
        mock_risk.return_value = mock_risk_calculator
        mock_risk_calculator.create_risk_alert.return_value = {
            "alert_id": "alert-123",
            "user_id": "test-user",
            "alert_type": "risk_threshold",
            "threshold": 0.8,
            "current_value": 0.6,
            "status": "active",
            "created_at": datetime.now(timezone.utc),
        }

        request_data = {
            "user_id": "test-user",
            "alert_config": {
                "alert_type": "risk_threshold",
                "threshold": 0.8,
                "enabled": True,
            },
        }

        response = client.post("/risk/alerts", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["user_id"] == "test-user"
        assert data["alert_type"] == "risk_threshold"

    @patch("app.dependencies.get_risk_calculator")
    def test_get_user_risk_alerts(self, mock_risk, client, mock_risk_calculator):
        """Test get user risk alerts endpoint."""
        mock_risk.return_value = mock_risk_calculator
        mock_risk_calculator.get_user_risk_alerts.return_value = [
            {
                "alert_id": "alert-123",
                "user_id": "test-user",
                "alert_type": "risk_threshold",
                "threshold": 0.8,
                "current_value": 0.6,
                "status": "active",
                "created_at": datetime.now(timezone.utc),
            }
        ]

        response = client.get("/risk/alerts/test-user")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["user_id"] == "test-user"

    @patch("app.dependencies.get_risk_calculator")
    def test_run_stress_test(self, mock_risk, client, mock_risk_calculator):
        """Test run stress test endpoint."""
        mock_risk.return_value = mock_risk_calculator
        mock_risk_calculator.run_stress_test.return_value = [
            {
                "scenario": "market_crash",
                "portfolio_value_before": 100000.0,
                "portfolio_value_after": 85000.0,
                "loss_amount": 15000.0,
                "loss_percentage": 0.15,
            },
            {
                "scenario": "recession",
                "portfolio_value_before": 100000.0,
                "portfolio_value_after": 90000.0,
                "loss_amount": 10000.0,
                "loss_percentage": 0.10,
            },
        ]

        response = client.get(
            "/risk/stress-test/test-portfolio?scenarios=market_crash&scenarios=recession"
        )
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["scenario"] == "market_crash"
        assert data[1]["scenario"] == "recession"
