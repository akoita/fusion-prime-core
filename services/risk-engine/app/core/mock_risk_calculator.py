"""
Mock Risk Calculator for development and testing.
Provides safe fallback implementations when external dependencies are not available.
"""

import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MockRiskCalculator:
    """Mock risk calculator that provides safe fallback implementations."""

    def __init__(self):
        """Initialize mock risk calculator."""
        logger.info("Initializing MockRiskCalculator (fallback mode)")
        self.is_initialized = False

    async def initialize(self):
        """Mock initialization."""
        logger.info("MockRiskCalculator initialized successfully (fallback mode)")
        self.is_initialized = True
        return True

    async def cleanup(self):
        """Mock cleanup."""
        logger.info("MockRiskCalculator cleaned up")
        self.is_initialized = False
        return True

    async def health_check(self) -> Dict[str, Any]:
        """Mock health check."""
        return {
            "status": "healthy",
            "database": "mock",
            "cache": "mock",
            "market_data": "mock",
        }

    async def calculate_portfolio_risk(self, portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """Mock portfolio risk calculation."""
        return {
            "total_risk": 0.15,
            "var_95": 0.05,
            "expected_shortfall": 0.08,
            "sharpe_ratio": 1.2,
            "beta": 0.85,
            "volatility": 0.12,
            "calculated_at": datetime.now(UTC).isoformat(),
        }

    async def calculate_margin_requirements(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """Mock margin requirements calculation."""
        return {
            "initial_margin": 1000.0,
            "maintenance_margin": 800.0,
            "margin_ratio": 0.1,
            "calculated_at": datetime.now(UTC).isoformat(),
        }

    async def get_risk_metrics(self, user_id: str) -> Dict[str, Any]:
        """Mock risk metrics."""
        return {
            "user_id": user_id,
            "portfolio_value": 10000.0,
            "total_risk": 0.15,
            "var_95": 500.0,
            "sharpe_ratio": 1.2,
            "beta": 0.85,
            "last_updated": datetime.now(UTC).isoformat(),
        }

    async def create_risk_alert(self, user_id: str, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock risk alert creation."""
        return {
            "alert_id": "mock_alert_123",
            "user_id": user_id,
            "type": alert_data.get("type", "risk_threshold"),
            "threshold": alert_data.get("threshold", 0.2),
            "status": "active",
            "created_at": datetime.now(UTC).isoformat(),
        }

    async def get_user_risk_alerts(self, user_id: str) -> List[Dict[str, Any]]:
        """Mock user risk alerts."""
        return [
            {
                "alert_id": "mock_alert_123",
                "user_id": user_id,
                "type": "risk_threshold",
                "threshold": 0.2,
                "status": "active",
                "created_at": datetime.now(UTC).isoformat(),
            }
        ]

    async def run_stress_test(self, portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """Mock stress test."""
        return {
            "scenario": "market_crash",
            "portfolio_value_before": 10000.0,
            "portfolio_value_after": 8500.0,
            "loss_percentage": 15.0,
            "var_95": 500.0,
            "expected_shortfall": 800.0,
            "calculated_at": datetime.now(UTC).isoformat(),
        }
