"""
Historical Simulation VaR Calculator.

Implements Value-at-Risk calculation using historical price data
instead of parametric assumptions.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import numpy as np
from app.integrations.price_oracle_client import PriceOracleClient

logger = logging.getLogger(__name__)


class HistoricalVaRCalculator:
    """
    Calculate Value-at-Risk using Historical Simulation method.

    This method:
    1. Fetches historical prices (e.g., 252 days = 1 trading year)
    2. Calculates daily returns from price changes
    3. Sorts returns to build empirical distribution
    4. Finds percentile based on confidence level (e.g., 5th percentile for 95% confidence)
    5. VaR = portfolio_value * |percentile_return|

    Benefits over Parametric VaR:
    - No assumption of normal distribution (captures fat tails)
    - Uses actual market behavior
    - Automatically adapts to current volatility
    """

    def __init__(self, price_oracle_client: PriceOracleClient):
        """
        Initialize Historical VaR calculator.

        Args:
            price_oracle_client: Client for fetching historical prices
        """
        self.price_oracle = price_oracle_client
        logger.info("Historical VaR calculator initialized")

    async def calculate_var(
        self,
        portfolio: Dict[str, float],  # {asset_symbol: amount}
        confidence_level: float = 0.95,
        lookback_days: int = 252,  # 1 trading year
        time_horizon_days: int = 1,  # 1-day VaR
    ) -> Dict[str, any]:
        """
        Calculate VaR using Historical Simulation method.

        Args:
            portfolio: Dictionary mapping asset symbol to amount held
            confidence_level: Confidence level (0.95 = 95%)
            lookback_days: Days of historical data to use
            time_horizon_days: Time horizon for VaR (1 = 1-day VaR)

        Returns:
            Dictionary with VaR metrics
        """
        try:
            logger.info(
                f"Calculating Historical VaR: {len(portfolio)} assets, "
                f"{confidence_level*100}% confidence, {lookback_days} days lookback"
            )

            # Step 1: Fetch historical prices for all assets
            historical_prices_by_asset = {}
            for asset_symbol in portfolio.keys():
                prices = await self.price_oracle.get_historical_prices(
                    asset_symbol, days=lookback_days
                )
                historical_prices_by_asset[asset_symbol] = prices

            # Step 2: Calculate daily returns for each asset
            returns_by_asset = {}
            for asset_symbol, prices in historical_prices_by_asset.items():
                returns = self._calculate_returns(prices)
                returns_by_asset[asset_symbol] = returns

            # Step 3: Calculate portfolio returns for each historical day
            portfolio_returns = self._calculate_portfolio_returns(returns_by_asset, portfolio)

            if len(portfolio_returns) == 0:
                logger.warning("No historical returns available")
                return self._empty_var_result()

            # Step 4: Sort returns to build empirical distribution
            sorted_returns = np.sort(portfolio_returns)

            # Step 5: Find VaR percentile
            # For 95% confidence, we look at the 5th percentile (worst 5% of outcomes)
            var_percentile = 1 - confidence_level
            var_index = int(var_percentile * len(sorted_returns))
            var_return = sorted_returns[var_index]

            # Calculate portfolio value
            current_prices = await self.price_oracle.get_multiple_prices(list(portfolio.keys()))

            portfolio_value = sum(
                portfolio[symbol] * float(current_prices[symbol]) for symbol in portfolio.keys()
            )

            # VaR = portfolio_value * |var_return|
            # This is the maximum expected loss at the confidence level
            var_1d = portfolio_value * abs(var_return)

            # Scale to other time horizons using square root of time rule
            var_7d = var_1d * np.sqrt(7 / time_horizon_days)
            var_30d = var_1d * np.sqrt(30 / time_horizon_days)

            # Calculate Expected Shortfall (CVaR) - average of losses beyond VaR
            tail_returns = sorted_returns[:var_index]
            if len(tail_returns) > 0:
                expected_shortfall_return = np.mean(tail_returns)
                cvar_1d = portfolio_value * abs(expected_shortfall_return)
            else:
                cvar_1d = var_1d * 1.3  # Conservative estimate

            cvar_7d = cvar_1d * np.sqrt(7 / time_horizon_days)
            cvar_30d = cvar_1d * np.sqrt(30 / time_horizon_days)

            # Calculate realized volatility from historical data
            volatility = float(np.std(portfolio_returns))

            # Max drawdown - worst historical loss
            max_drawdown = abs(float(np.min(portfolio_returns)))

            # Sharpe ratio estimate (assuming 0 risk-free rate for simplicity)
            mean_return = float(np.mean(portfolio_returns))
            sharpe_ratio = mean_return / volatility if volatility > 0 else 0

            return {
                "method": "historical_simulation",
                "portfolio_value_usd": round(portfolio_value, 2),
                "confidence_level": confidence_level,
                "lookback_days": lookback_days,
                "time_horizon_days": time_horizon_days,
                "var_1d": round(var_1d, 2),
                "var_7d": round(var_7d, 2),
                "var_30d": round(var_30d, 2),
                "cvar_1d": round(cvar_1d, 2),
                "cvar_7d": round(cvar_7d, 2),
                "cvar_30d": round(cvar_30d, 2),
                "expected_shortfall": round(cvar_1d, 2),
                "volatility": round(volatility, 4),
                "max_drawdown": round(max_drawdown, 4),
                "sharpe_ratio": round(sharpe_ratio, 2),
                "data_points": len(portfolio_returns),
                "calculated_at": datetime.utcnow().isoformat() + "Z",
            }

        except Exception as e:
            logger.error(f"Error calculating Historical VaR: {e}")
            return self._empty_var_result()

    def _calculate_returns(self, prices: List[Tuple[datetime, Decimal]]) -> np.ndarray:
        """
        Calculate daily returns from price series.

        Returns are calculated as: (P_t - P_{t-1}) / P_{t-1}

        Args:
            prices: List of (timestamp, price) tuples

        Returns:
            Numpy array of daily returns
        """
        if len(prices) < 2:
            return np.array([])

        price_values = np.array([float(p[1]) for p in prices])

        # Calculate returns: (P_t - P_{t-1}) / P_{t-1}
        returns = np.diff(price_values) / price_values[:-1]

        return returns

    def _calculate_portfolio_returns(
        self, returns_by_asset: Dict[str, np.ndarray], portfolio: Dict[str, float]
    ) -> np.ndarray:
        """
        Calculate portfolio returns from individual asset returns.

        For each historical day, computes the weighted average return
        based on portfolio weights.

        Args:
            returns_by_asset: Dictionary mapping asset to returns array
            portfolio: Dictionary mapping asset to amount held

        Returns:
            Numpy array of portfolio returns
        """
        # Find minimum length (some assets may have less history)
        min_length = min(len(returns) for returns in returns_by_asset.values())

        if min_length == 0:
            return np.array([])

        # Trim all return series to same length
        trimmed_returns = {
            asset: returns[:min_length] for asset, returns in returns_by_asset.items()
        }

        # Calculate portfolio weights
        total_value = sum(portfolio.values())
        weights = {asset: amount / total_value for asset, amount in portfolio.items()}

        # Calculate portfolio return for each day
        portfolio_returns = np.zeros(min_length)

        for day in range(min_length):
            day_return = sum(
                weights[asset] * trimmed_returns[asset][day] for asset in portfolio.keys()
            )
            portfolio_returns[day] = day_return

        return portfolio_returns

    def _empty_var_result(self) -> Dict[str, any]:
        """Return empty VaR result when calculation fails."""
        return {
            "method": "historical_simulation",
            "portfolio_value_usd": 0.0,
            "confidence_level": 0.95,
            "lookback_days": 0,
            "time_horizon_days": 1,
            "var_1d": 0.0,
            "var_7d": 0.0,
            "var_30d": 0.0,
            "cvar_1d": 0.0,
            "cvar_7d": 0.0,
            "cvar_30d": 0.0,
            "expected_shortfall": 0.0,
            "volatility": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "data_points": 0,
            "calculated_at": datetime.utcnow().isoformat() + "Z",
        }

    async def calculate_var_for_asset(
        self,
        asset_symbol: str,
        amount: float,
        confidence_level: float = 0.95,
        lookback_days: int = 252,
    ) -> Dict[str, any]:
        """
        Calculate VaR for a single asset position.

        Args:
            asset_symbol: Asset symbol
            amount: Amount held
            confidence_level: Confidence level
            lookback_days: Days of historical data

        Returns:
            Dictionary with VaR metrics
        """
        portfolio = {asset_symbol: amount}
        return await self.calculate_var(portfolio, confidence_level, lookback_days)

    async def calculate_marginal_var(
        self, portfolio: Dict[str, float], asset_symbol: str, confidence_level: float = 0.95
    ) -> float:
        """
        Calculate Marginal VaR - the change in VaR from adding one unit of an asset.

        This helps assess the risk contribution of each asset.

        Args:
            portfolio: Current portfolio
            asset_symbol: Asset to calculate marginal VaR for
            confidence_level: Confidence level

        Returns:
            Marginal VaR value
        """
        # Calculate current VaR
        current_var_result = await self.calculate_var(portfolio, confidence_level)
        current_var = current_var_result["var_1d"]

        # Add small amount of asset and recalculate
        delta = 1.0  # Add 1 unit
        modified_portfolio = portfolio.copy()
        modified_portfolio[asset_symbol] = modified_portfolio.get(asset_symbol, 0) + delta

        modified_var_result = await self.calculate_var(modified_portfolio, confidence_level)
        modified_var = modified_var_result["var_1d"]

        # Marginal VaR = change in VaR / change in position
        marginal_var = (modified_var - current_var) / delta

        return marginal_var
