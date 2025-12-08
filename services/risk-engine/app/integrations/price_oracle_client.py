"""
Price Oracle Client Integration for Risk Engine.

Fetches real-time and historical prices from the Price Oracle Service.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Tuple

import httpx

logger = logging.getLogger(__name__)


class PriceOracleClient:
    """
    Client for consuming prices from the Price Oracle Service.

    This client talks to the deployed price-oracle-service via HTTP.
    """

    def __init__(self, base_url: str, timeout: float = 10.0):
        """
        Initialize price oracle client.

        Args:
            base_url: Price Oracle Service URL
            timeout: HTTP request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        logger.info(f"Price oracle client initialized: {base_url}")

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def get_price(self, asset_symbol: str) -> Decimal:
        """
        Get current USD price for an asset.

        Args:
            asset_symbol: Asset symbol (ETH, BTC, etc.)

        Returns:
            Current USD price

        Raises:
            Exception: If price fetch fails
        """
        try:
            url = f"{self.base_url}/api/v1/prices/{asset_symbol.upper()}"
            response = await self.client.get(url)
            response.raise_for_status()

            data = response.json()
            return Decimal(data["price_usd"])

        except Exception as e:
            logger.error(f"Failed to fetch price for {asset_symbol}: {e}")
            raise

    async def get_multiple_prices(self, asset_symbols: List[str]) -> Dict[str, Decimal]:
        """
        Get current USD prices for multiple assets.

        Args:
            asset_symbols: List of asset symbols

        Returns:
            Dictionary mapping symbol to price
        """
        try:
            # Build query string
            symbols_param = "&".join(f"symbols={s.upper()}" for s in asset_symbols)
            url = f"{self.base_url}/api/v1/prices/?{symbols_param}"

            response = await self.client.get(url)
            response.raise_for_status()

            data = response.json()

            # Extract prices from response
            prices = {}
            for symbol, price_data in data["prices"].items():
                prices[symbol] = Decimal(price_data["price_usd"])

            return prices

        except Exception as e:
            logger.error(f"Failed to fetch multiple prices: {e}")
            raise

    async def get_historical_prices(
        self, asset_symbol: str, days: int = 252
    ) -> List[Tuple[datetime, Decimal]]:
        """
        Get historical daily prices for an asset.

        Args:
            asset_symbol: Asset symbol
            days: Number of days of history (default: 252 trading days = 1 year)

        Returns:
            List of (timestamp, price) tuples sorted by date ascending
        """
        try:
            url = f"{self.base_url}/api/v1/prices/{asset_symbol.upper()}/historical"
            params = {"days": min(days, 365)}  # Max 365 days

            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            # Parse response
            historical_prices = []
            for price_point in data["prices"]:
                timestamp = datetime.fromisoformat(price_point["timestamp"].replace("Z", "+00:00"))
                price = Decimal(price_point["price_usd"])
                historical_prices.append((timestamp, price))

            # Sort by date ascending
            historical_prices.sort(key=lambda x: x[0])

            logger.info(f"Fetched {len(historical_prices)} historical prices for {asset_symbol}")

            return historical_prices

        except Exception as e:
            logger.error(f"Failed to fetch historical prices for {asset_symbol}: {e}")
            raise

    async def health_check(self) -> bool:
        """
        Check if Price Oracle Service is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            url = f"{self.base_url}/health"
            response = await self.client.get(url)
            response.raise_for_status()

            data = response.json()
            return data.get("status") == "healthy"

        except Exception as e:
            logger.error(f"Price oracle health check failed: {e}")
            return False
