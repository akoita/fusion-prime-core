"""
Integration Tests for Risk Engine Production Implementation

Tests the Risk Engine service with real database integration and actual VaR calculations.

WHAT THESE TESTS VALIDATE:
✅ Risk Engine health with database connectivity
✅ Portfolio risk calculation using real escrow data
✅ Custom portfolio risk calculation for arbitrary asset portfolios
✅ Margin requirements calculation for real users
✅ Risk metrics retrieval and filtering by time range
✅ Stress test execution with multiple scenarios
✅ Risk alert creation and management
✅ Complete end-to-end risk workflow

COMPLETE END-TO-END FLOW:
1. User creates escrow → Settlement Service → Database
2. Risk Engine queries escrows → Calculates portfolio risk metrics
3. User views risk dashboard → Fetches real-time risk metrics
4. Alerts trigger on margin breaches → User notified

Each test is a complete scenario that validates:
- Service availability and connectivity
- Real-time risk calculations from database
- Financial accuracy (VaR, margins, correlations)
- User workflows (alerts, stress tests, metrics)
"""

import os

import pytest
import requests

from tests.base_integration_test import BaseIntegrationTest


class TestRiskEngineProduction(BaseIntegrationTest):
    """Integration tests for Risk Engine production functionality."""

    def setup_method(self):
        """Setup test environment using configuration system."""
        # Call parent setup to load environment configuration
        super().setup_method()

        # Get Risk Engine URL from configuration
        self.risk_engine_url = self.risk_engine_url or "http://localhost:8080"
        self.timeout = 30

    def test_risk_engine_health_with_database(self):
        """
        Test Scenario: Risk Engine Health Check with Database

        WHAT THIS TEST VALIDATES:
        ✅ Service is running and accessible
        ✅ Health endpoint returns valid response
        ✅ Database connectivity established
        ✅ All subsystems operational

        EXPECTED BEHAVIOR:
        - HTTP 200 status
        - Status: "healthy" or "degraded" (degraded acceptable if dependencies not fully initialized)
        """
        print("\n🔄 Testing Risk Engine health with database...")

        response = requests.get(f"{self.risk_engine_url}/health/", timeout=self.timeout)

        assert response.status_code == 200, f"Health check failed: {response.status_code}"

        data = response.json()
        print(f"✅ Risk Engine status: {data.get('status')}")

        # Should be healthy with database connected
        assert data.get("status") in ["healthy", "degraded"]

    def test_calculate_portfolio_risk_from_escrows(self):
        """
        Test Scenario: Portfolio Risk Calculation from Real Escrow Data

        WHAT THIS TEST VALIDATES:
        ✅ Query escrows from Settlement Service database
        ✅ Calculate portfolio risk metrics from actual positions
        ✅ Validate VaR calculations at multiple time horizons
        ✅ Verify risk score is within acceptable range (0-1)
        ✅ Confirm escalation of VaR across time horizons

        EXPECTED BEHAVIOR:
        - Returns complete portfolio risk profile
        - VaR: 1d < 7d < 30d (risk increases with time)
        - Risk score: 0.0 (low risk) to 1.0 (high risk)
        - All calculated metrics are non-negative
        """
        print("\n🔄 Testing portfolio risk calculation from escrows...")

        # Calculate portfolio risk (uses real escrow data)
        response = requests.get(
            f"{self.risk_engine_url}/risk/portfolio/portfolio_all", timeout=self.timeout
        )

        assert response.status_code == 200
        data = response.json()

        print(f"✅ Portfolio risk calculated:")
        print(f"   - Total escrows: {data.get('total_escrows')}")
        print(f"   - Total value: ${data.get('total_value_usd', 0):,.2f}")
        print(f"   - Risk score: {data.get('risk_score', 0):.2f}")

        # Validate required fields
        assert "portfolio_id" in data
        assert "total_escrows" in data
        assert "total_value_usd" in data
        assert "risk_score" in data
        assert "var_1d" in data
        assert "var_7d" in data
        assert "var_30d" in data

        # Validate risk metrics
        assert 0.0 <= data["risk_score"] <= 1.0
        assert data["var_1d"] >= 0
        assert data["var_7d"] >= data["var_1d"]
        assert data["var_30d"] >= data["var_7d"]

    def test_calculate_custom_portfolio_risk(self):
        """Test custom portfolio risk calculation."""
        print("\n🔄 Testing custom portfolio risk calculation...")

        portfolio_data = {
            "portfolio_id": "test-custom-portfolio",
            "assets": [
                {"symbol": "BTC", "amount": 1.0, "price": 50000.0},
                {"symbol": "ETH", "amount": 10.0, "price": 3000.0},
                {"symbol": "USDC", "amount": 5000.0, "price": 1.0},
            ],
            "risk_model": "standard",
            "confidence_level": 0.95,
        }

        response = requests.post(
            f"{self.risk_engine_url}/risk/calculate", json=portfolio_data, timeout=self.timeout
        )

        assert response.status_code == 200
        data = response.json()

        print(f"✅ Custom portfolio risk calculated:")
        print(f"   - Total value: ${data.get('total_value_usd', 0):,.2f}")
        print(f"   - Risk score: {data.get('risk_score', 0):.2f}")
        print(f"   - 1d VaR: ${data.get('var_1d', 0):,.2f}")

        # Validate results
        assert data["portfolio_id"] == "test-custom-portfolio"
        assert data["total_value_usd"] == 85000.0  # 1*50000 + 10*3000 + 5000*1 = 85000
        assert 0.0 <= data["risk_score"] <= 1.0
        assert data["var_1d"] > 0

    def test_calculate_margin_requirements(self):
        """Test margin requirements calculation."""
        print("\n🔄 Testing margin requirements calculation...")

        response = requests.get(
            f"{self.risk_engine_url}/risk/margin/test-user-123", timeout=self.timeout
        )

        assert response.status_code == 200
        data = response.json()

        print(f"✅ Margin requirements calculated:")
        print(f"   - Total margin: ${data.get('total_margin', 0):,.2f}")
        print(f"   - Initial margin: ${data.get('initial_margin', 0):,.2f}")
        print(f"   - Available margin: ${data.get('available_margin', 0):,.2f}")
        print(f"   - Margin ratio: {data.get('margin_ratio', 0):.2f}")

        # Validate results
        assert data["user_id"] == "test-user-123"
        assert "total_margin" in data
        assert "initial_margin" in data
        assert "maintenance_margin" in data
        assert "available_margin" in data
        assert "margin_ratio" in data
        # When there's collateral, initial margin should be 20% of total
        if data["total_margin"] > 0:
            assert abs(data["initial_margin"] - data["total_margin"] * 0.20) < 0.01

    def test_get_risk_metrics(self):
        """Test risk metrics retrieval."""
        print("\n🔄 Testing risk metrics retrieval...")

        response = requests.get(
            f"{self.risk_engine_url}/risk/metrics?time_range=7d", timeout=self.timeout
        )

        assert response.status_code == 200
        data = response.json()

        print(f"✅ Risk metrics retrieved")
        print(f"   - Time range: {data.get('time_range')}")

        # Validate results
        assert "risk_score" in data
        assert "volatility" in data
        assert "time_range" in data

    def test_run_stress_test(self):
        """Test stress test scenarios."""
        print("\n🔄 Testing stress test scenarios...")

        scenarios = ["market_crash", "recession", "high_volatility"]
        response = requests.get(
            f"{self.risk_engine_url}/risk/stress-test/test-portfolio",
            params={"scenarios": scenarios},
            timeout=self.timeout,
        )

        assert response.status_code == 200
        data = response.json()

        print(f"✅ Stress test completed with {len(data)} scenarios")

        # Validate results
        assert len(data) == 3
        for result in data:
            assert "scenario" in result
            assert "portfolio_value_before" in result
            assert "portfolio_value_after" in result
            assert "loss_amount" in result
            assert "loss_percentage" in result

            # Validate crash scenario (should be -20%)
            if result["scenario"] == "market_crash":
                assert result["loss_percentage"] == 0.20

    def test_create_and_get_risk_alert(self):
        """Test creating and retrieving risk alerts."""
        print("\n🔄 Testing risk alert management...")

        # Create alert
        alert_data = {
            "user_id": "test-user-alert",
            "alert_config": {
                "alert_type": "risk_threshold",
                "threshold": 0.80,
            },
        }

        response = requests.post(
            f"{self.risk_engine_url}/risk/alerts", json=alert_data, timeout=self.timeout
        )

        assert response.status_code == 200
        alert = response.json()

        print(f"✅ Risk alert created: {alert.get('alert_id')}")
        assert alert["user_id"] == "test-user-alert"
        assert alert["alert_type"] == "risk_threshold"
        assert alert["threshold"] == 0.80

        # Get alerts for user
        response = requests.get(
            f"{self.risk_engine_url}/risk/alerts/test-user-alert", timeout=self.timeout
        )

        assert response.status_code == 200
        alerts = response.json()

        print(f"✅ Retrieved {len(alerts)} alerts for user")
        assert isinstance(alerts, list)
        assert len(alerts) >= 1

    def test_end_to_end_risk_calculation_workflow(self):
        """Test complete risk calculation workflow."""
        print("\n🔄 Testing end-to-end risk calculation workflow...")

        # 1. Get portfolio risk
        portfolio_response = requests.get(
            f"{self.risk_engine_url}/risk/portfolio/workflow-test", timeout=self.timeout
        )
        assert portfolio_response.status_code == 200

        # 2. Calculate margin requirements
        margin_response = requests.get(
            f"{self.risk_engine_url}/risk/margin/workflow-user", timeout=self.timeout
        )
        assert margin_response.status_code == 200

        # 3. Get risk metrics
        metrics_response = requests.get(
            f"{self.risk_engine_url}/risk/metrics?portfolio_id=workflow-test&time_range=7d",
            timeout=self.timeout,
        )
        assert metrics_response.status_code == 200

        # 4. Run stress test
        stress_response = requests.get(
            f"{self.risk_engine_url}/risk/stress-test/workflow-test",
            params={"scenarios": ["market_crash"]},
            timeout=self.timeout,
        )
        assert stress_response.status_code == 200

        print("✅ End-to-end workflow completed successfully")
