"""
Unit tests for Risk Engine Service analytics endpoints.
"""

from datetime import UTC, datetime, timezone
from unittest.mock import Mock, patch

import pytest
from app.dependencies import get_analytics_engine
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_analytics_engine():
    """Mock analytics engine."""
    mock = Mock()

    # Mock portfolio history
    mock.get_portfolio_history.return_value = {
        "portfolio_id": "test-portfolio",
        "time_range": "30d",
        "history": [
            {"date": "2024-01-01", "value": 100000.0, "return": 0.05},
            {"date": "2024-01-02", "value": 105000.0, "return": 0.03},
        ],
        "calculated_at": datetime.now(UTC),
    }

    # Mock stress test
    mock.run_stress_test.return_value = [
        {
            "scenario": "market_crash",
            "portfolio_value_before": 100000.0,
            "portfolio_value_after": 85000.0,
            "loss_amount": 15000.0,
            "loss_percentage": 0.15,
        }
    ]

    # Mock correlation analysis
    mock.analyze_correlation.return_value = {
        "assets": ["BTC", "ETH", "USDC"],
        "correlation_matrix": {
            "BTC": {"BTC": 1.0, "ETH": 0.7, "USDC": 0.1},
            "ETH": {"BTC": 0.7, "ETH": 1.0, "USDC": 0.1},
            "USDC": {"BTC": 0.1, "ETH": 0.1, "USDC": 1.0},
        },
        "average_correlation": 0.5,
        "max_correlation": 0.9,
        "min_correlation": 0.1,
        "calculated_at": datetime.now(UTC),
    }

    # Mock performance metrics
    mock.get_portfolio_performance.return_value = {
        "portfolio_id": "test-portfolio",
        "total_return": 0.15,
        "annualized_return": 0.12,
        "volatility": 0.18,
        "sharpe_ratio": 1.2,
        "max_drawdown": 0.08,
        "calmar_ratio": 1.5,
        "sortino_ratio": 1.8,
        "information_ratio": 0.4,
        "calculated_at": datetime.now(UTC),
    }

    return mock


class TestAnalyticsEndpoints:
    """Test analytics endpoints."""

    @patch("app.dependencies.get_analytics_engine")
    def test_get_portfolio_history(self, mock_analytics, client, mock_analytics_engine):
        """Test get portfolio history endpoint."""
        mock_analytics.return_value = mock_analytics_engine

        response = client.get("/analytics/portfolio/test-portfolio/history?time_range=30d")
        assert response.status_code == 200

        data = response.json()
        assert data["portfolio_id"] == "test-portfolio"
        assert data["time_range"] == "30d"
        assert "history" in data

    @patch("app.dependencies.get_analytics_engine")
    def test_run_stress_test(self, mock_analytics, client, mock_analytics_engine):
        """Test run stress test endpoint."""
        mock_analytics.return_value = mock_analytics_engine

        request_data = {
            "portfolio_id": "test-portfolio",
            "scenarios": ["market_crash", "recession"],
            "time_horizon": 30,
            "confidence_level": 0.95,
        }

        response = client.post("/analytics/stress-test", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2  # One result per scenario
        assert data[0]["scenario"] == "market_crash"
        assert data[1]["scenario"] == "recession"

    @patch("app.dependencies.get_analytics_engine")
    def test_analyze_correlation(self, mock_analytics, client, mock_analytics_engine):
        """Test analyze correlation endpoint."""
        mock_analytics.return_value = mock_analytics_engine

        request_data = {
            "assets": ["BTC", "ETH", "USDC"],
            "time_range": "30d",
            "method": "pearson",
        }

        response = client.post("/analytics/correlation", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["assets"] == ["BTC", "ETH", "USDC"]
        assert "correlation_matrix" in data
        assert "average_correlation" in data

    @patch("app.dependencies.get_analytics_engine")
    def test_get_portfolio_performance(self, mock_analytics, client, mock_analytics_engine):
        """Test get portfolio performance endpoint."""
        mock_analytics.return_value = mock_analytics_engine

        response = client.get("/analytics/performance/test-portfolio?benchmark=SPY&time_range=30d")
        assert response.status_code == 200

        data = response.json()
        assert data["portfolio_id"] == "test-portfolio"
        assert "total_return" in data
        assert "annualized_return" in data
        assert "volatility" in data
        assert "sharpe_ratio" in data

    @patch("app.dependencies.get_analytics_engine")
    def test_get_portfolio_volatility(self, mock_analytics, client, mock_analytics_engine):
        """Test get portfolio volatility endpoint."""
        mock_analytics.return_value = mock_analytics_engine
        mock_analytics_engine.get_portfolio_volatility.return_value = {
            "portfolio_id": "test-portfolio",
            "time_range": "30d",
            "volatility": 0.18,
            "rolling_volatility": [0.15, 0.16, 0.17, 0.18, 0.19],
            "volatility_percentiles": {
                "25th": 0.12,
                "50th": 0.15,
                "75th": 0.18,
                "90th": 0.22,
            },
            "calculated_at": datetime.now(timezone.utc),
        }

        response = client.get("/analytics/volatility/test-portfolio?time_range=30d")
        assert response.status_code == 200

        data = response.json()
        assert data["portfolio_id"] == "test-portfolio"
        assert "volatility" in data
        assert "rolling_volatility" in data

    @patch("app.dependencies.get_analytics_engine")
    def test_get_portfolio_drawdown(self, mock_analytics, client, mock_analytics_engine):
        """Test get portfolio drawdown endpoint."""
        mock_analytics.return_value = mock_analytics_engine
        mock_analytics_engine.get_portfolio_drawdown.return_value = {
            "portfolio_id": "test-portfolio",
            "time_range": "30d",
            "max_drawdown": 0.08,
            "drawdown_duration": 5,
            "recovery_time": 3,
            "calculated_at": datetime.now(timezone.utc),
        }

        response = client.get("/analytics/drawdown/test-portfolio?time_range=30d")
        assert response.status_code == 200

        data = response.json()
        assert data["portfolio_id"] == "test-portfolio"
        assert "max_drawdown" in data
        assert "drawdown_duration" in data

    @patch("app.dependencies.get_analytics_engine")
    def test_get_portfolio_sharpe(self, mock_analytics, client, mock_analytics_engine):
        """Test get portfolio Sharpe ratio endpoint."""
        mock_analytics.return_value = mock_analytics_engine
        mock_analytics_engine.get_portfolio_sharpe.return_value = {
            "portfolio_id": "test-portfolio",
            "time_range": "30d",
            "risk_free_rate": 0.02,
            "sharpe_ratio": 1.2,
            "calculated_at": datetime.now(timezone.utc),
        }

        response = client.get("/analytics/sharpe/test-portfolio?risk_free_rate=0.02&time_range=30d")
        assert response.status_code == 200

        data = response.json()
        assert data["portfolio_id"] == "test-portfolio"
        assert data["sharpe_ratio"] == 1.2

    @patch("app.dependencies.get_analytics_engine")
    def test_get_portfolio_beta(self, mock_analytics, client, mock_analytics_engine):
        """Test get portfolio beta endpoint."""
        mock_analytics.return_value = mock_analytics_engine
        mock_analytics_engine.get_portfolio_beta.return_value = {
            "portfolio_id": "test-portfolio",
            "benchmark": "SPY",
            "time_range": "30d",
            "beta": 0.9,
            "calculated_at": datetime.now(timezone.utc),
        }

        response = client.get("/analytics/beta/test-portfolio?benchmark=SPY&time_range=30d")
        assert response.status_code == 200

        data = response.json()
        assert data["portfolio_id"] == "test-portfolio"
        assert data["beta"] == 0.9
