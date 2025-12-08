"""
Price Oracle Client for fetching real-time and historical crypto prices.

Supports multiple price feed providers with automatic fallback:
1. Chainlink Data Feeds (primary for testnet/mainnet)
2. Pyth Network (fallback)
3. Coingecko (fallback for historical data)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import httpx
from circuitbreaker import circuit

logger = logging.getLogger(__name__)


class PriceOracleException(Exception):
    """Exception raised when price fetching fails."""

    pass


class PriceOracleClient:
    """
    Client for fetching crypto prices from multiple sources.

    Features:
    - Multi-provider fallback (Chainlink → Pyth → Coingecko)
    - In-memory caching with TTL
    - Circuit breaker pattern for resilience
    - Historical price data support
    """

    # Chainlink Sepolia testnet price feed addresses
    CHAINLINK_FEEDS_SEPOLIA = {
        "ETH": "0x694AA1769357215DE4FAC081bf1f309aDC325306",  # ETH/USD
        "BTC": "0x1b44F3514812d835EB1BDB0acB33d3fA3351Ee43",  # BTC/USD
        "USDC": "0xA2F78ab2355fe2f984D808B5CeE7FD0A93D5270E",  # USDC/USD
        "USDT": "0x3E7d1eAB13ad0104d2750B8863b489D65364e32D",  # USDT/USD
    }

    # Pyth price feed IDs
    PYTH_FEED_IDS = {
        "ETH": "0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace",
        "BTC": "0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43",
        "USDC": "0xeaa020c61cc479712813461ce153894a96a6c00b21ed0cfc2798d1f9a9e9c94a",
        "USDT": "0x2b89b9dc8fdf9f34709a5b106b472f0f39bb6ca9ce04b0fd7f2e971688e2e53b",
    }

    def __init__(
        self,
        eth_rpc_url: str,
        coingecko_api_key: Optional[str] = None,
        cache_ttl: int = 60,  # seconds
        timeout: float = 5.0,
    ):
        """
        Initialize price oracle client.

        Args:
            eth_rpc_url: Ethereum RPC URL for Chainlink feeds
            coingecko_api_key: Optional Coingecko API key for rate limit increase
            cache_ttl: Cache time-to-live in seconds
            timeout: HTTP request timeout in seconds
        """
        self.eth_rpc_url = eth_rpc_url
        self.coingecko_api_key = coingecko_api_key
        self.cache_ttl = cache_ttl
        self.timeout = timeout

        # In-memory cache: {symbol: (price, timestamp)}
        self.cache: Dict[str, Tuple[Decimal, datetime]] = {}

        # HTTP client
        self.client = httpx.AsyncClient(timeout=timeout)

        logger.info(f"Price oracle initialized with cache_ttl={cache_ttl}s, timeout={timeout}s")

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def get_price(self, asset_symbol: str, force_refresh: bool = False) -> Decimal:
        """
        Get current USD price for an asset.

        Tries providers in order:
        1. Cache (if not expired and not forced refresh)
        2. Chainlink (primary)
        3. Pyth (fallback)
        4. Coingecko (final fallback)

        Args:
            asset_symbol: Asset symbol (ETH, BTC, USDC, etc.)
            force_refresh: Skip cache and fetch fresh data

        Returns:
            Current USD price as Decimal

        Raises:
            PriceOracleException: If all providers fail
        """
        asset_symbol = asset_symbol.upper()

        # Check cache
        if not force_refresh:
            cached_price = self._get_from_cache(asset_symbol)
            if cached_price is not None:
                logger.debug(f"Price for {asset_symbol} from cache: ${cached_price}")
                return cached_price

        # Try Chainlink first
        try:
            price = await self._fetch_chainlink_price(asset_symbol)
            self._update_cache(asset_symbol, price)
            logger.info(f"Price for {asset_symbol} from Chainlink: ${price}")
            return price
        except Exception as e:
            logger.warning(f"Chainlink fetch failed for {asset_symbol}: {e}")

        # Fallback to Pyth
        try:
            price = await self._fetch_pyth_price(asset_symbol)
            self._update_cache(asset_symbol, price)
            logger.info(f"Price for {asset_symbol} from Pyth: ${price}")
            return price
        except Exception as e:
            logger.warning(f"Pyth fetch failed for {asset_symbol}: {e}")

        # Final fallback to Coingecko
        try:
            price = await self._fetch_coingecko_price(asset_symbol)
            self._update_cache(asset_symbol, price)
            logger.info(f"Price for {asset_symbol} from Coingecko: ${price}")
            return price
        except Exception as e:
            logger.error(f"Coingecko fetch failed for {asset_symbol}: {e}")

        # All providers failed
        raise PriceOracleException(f"Failed to fetch price for {asset_symbol} from all providers")

    async def get_multiple_prices(
        self, asset_symbols: List[str], force_refresh: bool = False
    ) -> Dict[str, Decimal]:
        """
        Get current USD prices for multiple assets in parallel.

        Args:
            asset_symbols: List of asset symbols
            force_refresh: Skip cache and fetch fresh data

        Returns:
            Dictionary mapping symbol to price
        """
        tasks = [self.get_price(symbol, force_refresh) for symbol in asset_symbols]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        prices = {}
        for symbol, result in zip(asset_symbols, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch price for {symbol}: {result}")
            else:
                prices[symbol.upper()] = result

        return prices

    async def get_historical_prices(
        self, asset_symbol: str, days: int = 30
    ) -> List[Tuple[datetime, Decimal]]:
        """
        Fetch historical daily prices for an asset.

        Args:
            asset_symbol: Asset symbol
            days: Number of days of history (max 365)

        Returns:
            List of (timestamp, price) tuples, sorted by date ascending
        """
        asset_symbol = asset_symbol.upper()

        # Use Coingecko for historical data
        try:
            return await self._fetch_coingecko_historical(asset_symbol, days)
        except Exception as e:
            logger.error(f"Failed to fetch historical prices for {asset_symbol}: {e}")
            raise PriceOracleException(f"Failed to fetch historical prices for {asset_symbol}")

    @circuit(failure_threshold=5, recovery_timeout=60)
    async def _fetch_chainlink_price(self, asset_symbol: str) -> Decimal:
        """
        Fetch price from Chainlink data feed.

        Uses eth_call to read latestRoundData from Chainlink aggregator.
        """
        feed_address = self.CHAINLINK_FEEDS_SEPOLIA.get(asset_symbol)
        if not feed_address:
            raise ValueError(f"No Chainlink feed for {asset_symbol}")

        # latestRoundData() function signature
        # Returns: (roundId, answer, startedAt, updatedAt, answeredInRound)
        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_call",
            "params": [
                {
                    "to": feed_address,
                    "data": "0x feaf968c",  # latestRoundData()
                },
                "latest",
            ],
        }

        response = await self.client.post(self.eth_rpc_url, json=data)
        response.raise_for_status()

        result = response.json()
        if "error" in result:
            raise PriceOracleException(f"RPC error: {result['error']}")

        # Parse response (returns 5 values)
        response_data = result["result"]

        # Extract answer (2nd value) - it's in the middle of the hex string
        # Chainlink returns 8 decimals for most feeds
        answer_hex = response_data[2 + 64 : 2 + 128]  # Skip first value, take second
        answer = int(answer_hex, 16)

        # Chainlink typically uses 8 decimals
        price = Decimal(answer) / Decimal(10**8)

        return price

    @circuit(failure_threshold=5, recovery_timeout=60)
    async def _fetch_pyth_price(self, asset_symbol: str) -> Decimal:
        """
        Fetch price from Pyth Network.

        Uses Pyth HTTP API for testnet/mainnet prices.
        """
        feed_id = self.PYTH_FEED_IDS.get(asset_symbol)
        if not feed_id:
            raise ValueError(f"No Pyth feed for {asset_symbol}")

        # Pyth Hermes API (works for testnet and mainnet)
        url = f"https://hermes.pyth.network/api/latest_price_feeds?ids[]={feed_id}"

        response = await self.client.get(url)
        response.raise_for_status()

        data = response.json()

        if not data or len(data) == 0:
            raise PriceOracleException(f"No Pyth data for {asset_symbol}")

        price_data = data[0]["price"]
        price_value = int(price_data["price"])
        exponent = int(price_data["expo"])

        # Calculate price: price * 10^exponent
        price = Decimal(price_value) * (Decimal(10) ** exponent)

        return price

    @circuit(failure_threshold=5, recovery_timeout=60)
    async def _fetch_coingecko_price(self, asset_symbol: str) -> Decimal:
        """
        Fetch current price from Coingecko.

        Fallback for when Chainlink and Pyth are unavailable.
        """
        # Map symbols to Coingecko IDs
        coingecko_ids = {
            "ETH": "ethereum",
            "BTC": "bitcoin",
            "USDC": "usd-coin",
            "USDT": "tether",
        }

        coin_id = coingecko_ids.get(asset_symbol)
        if not coin_id:
            raise ValueError(f"No Coingecko mapping for {asset_symbol}")

        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": coin_id,
            "vs_currencies": "usd",
        }

        headers = {}
        if self.coingecko_api_key:
            headers["x-cg-pro-api-key"] = self.coingecko_api_key

        response = await self.client.get(url, params=params, headers=headers)
        response.raise_for_status()

        data = response.json()

        if coin_id not in data or "usd" not in data[coin_id]:
            raise PriceOracleException(f"No Coingecko data for {asset_symbol}")

        price = Decimal(str(data[coin_id]["usd"]))
        return price

    async def _fetch_coingecko_historical(
        self, asset_symbol: str, days: int
    ) -> List[Tuple[datetime, Decimal]]:
        """
        Fetch historical prices from Coingecko.

        Returns daily prices for the specified number of days.
        """
        coingecko_ids = {
            "ETH": "ethereum",
            "BTC": "bitcoin",
            "USDC": "usd-coin",
            "USDT": "tether",
        }

        coin_id = coingecko_ids.get(asset_symbol)
        if not coin_id:
            raise ValueError(f"No Coingecko mapping for {asset_symbol}")

        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": min(days, 365),  # Max 365 days
            "interval": "daily",
        }

        headers = {}
        if self.coingecko_api_key:
            headers["x-cg-pro-api-key"] = self.coingecko_api_key

        response = await self.client.get(url, params=params, headers=headers)
        response.raise_for_status()

        data = response.json()

        if "prices" not in data:
            raise PriceOracleException(f"No historical data for {asset_symbol}")

        # Parse prices: [[timestamp_ms, price], ...]
        historical_prices = []
        for timestamp_ms, price in data["prices"]:
            dt = datetime.fromtimestamp(timestamp_ms / 1000)
            historical_prices.append((dt, Decimal(str(price))))

        return historical_prices

    def _get_from_cache(self, asset_symbol: str) -> Optional[Decimal]:
        """Get price from cache if not expired."""
        if asset_symbol not in self.cache:
            return None

        price, cached_at = self.cache[asset_symbol]
        age = (datetime.utcnow() - cached_at).total_seconds()

        if age >= self.cache_ttl:
            # Expired
            del self.cache[asset_symbol]
            return None

        return price

    def _update_cache(self, asset_symbol: str, price: Decimal):
        """Update cache with new price."""
        self.cache[asset_symbol] = (price, datetime.utcnow())

    def clear_cache(self):
        """Clear all cached prices."""
        self.cache.clear()
        logger.info("Price cache cleared")
