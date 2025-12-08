"""
Mock Analytics Engine for development and testing.
Provides safe fallback implementations when external dependencies are not available.
"""

import logging
import random
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MockAnalyticsEngine:
    """Mock analytics engine that provides safe fallback implementations."""

    def __init__(self):
        """Initialize mock analytics engine."""
        logger.info("Initializing MockAnalyticsEngine (fallback mode)")
        self.is_initialized = False

    async def initialize(self):
        """Mock initialization."""
        logger.info("MockAnalyticsEngine initialized successfully (fallback mode)")
        self.is_initialized = True
        return True

    async def cleanup(self):
        """Mock cleanup."""
        logger.info("MockAnalyticsEngine cleaned up")
        self.is_initialized = False
        return True

    async def health_check(self) -> Dict[str, Any]:
        """Mock health check."""
        return {
            "status": "healthy",
            "database": "mock",
            "bigquery": "mock",
        }

    async def get_portfolio_history(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Mock portfolio history."""
        history = []
        base_value = 10000.0

        for i in range(days):
            date = datetime.now(UTC) - timedelta(days=days - i)
            # Generate mock data with some volatility
            value = base_value * (1 + random.uniform(-0.05, 0.05))
            history.append(
                {
                    "date": date.isoformat(),
                    "portfolio_value": round(value, 2),
                    "daily_return": round(random.uniform(-0.02, 0.02), 4),
                }
            )

        return history

    async def get_portfolio_performance(self, user_id: str, period: str = "30d") -> Dict[str, Any]:
        """Mock portfolio performance."""
        return {
            "period": period,
            "total_return": 0.12,
            "annualized_return": 0.15,
            "volatility": 0.18,
            "sharpe_ratio": 0.83,
            "max_drawdown": 0.08,
            "win_rate": 0.65,
            "calculated_at": datetime.now(UTC).isoformat(),
        }

    async def get_portfolio_volatility(self, user_id: str, period: str = "30d") -> Dict[str, Any]:
        """Mock portfolio volatility."""
        return {
            "period": period,
            "volatility": 0.18,
            "annualized_volatility": 0.22,
            "rolling_volatility": 0.16,
            "volatility_percentile": 75,
            "calculated_at": datetime.now(UTC).isoformat(),
        }

    async def get_portfolio_drawdown(self, user_id: str, period: str = "30d") -> Dict[str, Any]:
        """Mock portfolio drawdown."""
        return {
            "period": period,
            "max_drawdown": 0.08,
            "current_drawdown": 0.02,
            "drawdown_duration": 5,
            "recovery_time": 3,
            "calculated_at": datetime.now(UTC).isoformat(),
        }

    async def get_portfolio_sharpe(self, user_id: str, period: str = "30d") -> Dict[str, Any]:
        """Mock portfolio Sharpe ratio."""
        return {
            "period": period,
            "sharpe_ratio": 0.83,
            "risk_free_rate": 0.02,
            "excess_return": 0.13,
            "volatility": 0.18,
            "calculated_at": datetime.now(UTC).isoformat(),
        }

    async def get_portfolio_beta(self, user_id: str, benchmark: str = "SPY") -> Dict[str, Any]:
        """Mock portfolio beta."""
        return {
            "benchmark": benchmark,
            "beta": 0.85,
            "correlation": 0.78,
            "r_squared": 0.61,
            "alpha": 0.02,
            "calculated_at": datetime.now(UTC).isoformat(),
        }

    async def analyze_correlation(self, assets: List[str], period: str = "30d") -> Dict[str, Any]:
        """Mock correlation analysis."""
        # Generate mock correlation matrix
        correlation_matrix = {}
        for i, asset1 in enumerate(assets):
            correlation_matrix[asset1] = {}
            for j, asset2 in enumerate(assets):
                if i == j:
                    correlation_matrix[asset1][asset2] = 1.0
                else:
                    correlation_matrix[asset1][asset2] = round(random.uniform(-0.5, 0.8), 3)

        return {
            "period": period,
            "assets": assets,
            "correlation_matrix": correlation_matrix,
            "average_correlation": 0.35,
            "calculated_at": datetime.now(UTC).isoformat(),
        }

    async def run_stress_test(
        self, portfolio: Dict[str, Any], scenarios: List[str] = None
    ) -> Dict[str, Any]:
        """Mock stress test."""
        if scenarios is None:
            scenarios = ["market_crash", "interest_rate_shock", "liquidity_crisis"]

        results = {}
        for scenario in scenarios:
            results[scenario] = {
                "portfolio_value_before": 10000.0,
                "portfolio_value_after": round(10000.0 * random.uniform(0.7, 0.95), 2),
                "loss_percentage": round(random.uniform(5, 30), 2),
                "var_95": round(10000.0 * random.uniform(0.05, 0.15), 2),
                "expected_shortfall": round(10000.0 * random.uniform(0.08, 0.20), 2),
            }

        return {
            "scenarios": scenarios,
            "results": results,
            "calculated_at": datetime.now(UTC).isoformat(),
        }
