"""
Price Oracle API routes.
"""

import logging
from datetime import datetime
from typing import List

from app.core.price_oracle_client import PriceOracleClient, PriceOracleException
from app.models.price import (
    HistoricalPricePoint,
    HistoricalPricesResponse,
    MultiplePricesResponse,
    PriceResponse,
)
from fastapi import APIRouter, Depends, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/prices", tags=["prices"])


# Dependency to get price oracle client (will be injected by main.py)
def get_price_oracle() -> PriceOracleClient:
    """Dependency injection for price oracle client."""
    from app.main import price_oracle_client

    return price_oracle_client


@router.get("/{asset_symbol}", response_model=PriceResponse)
async def get_asset_price(
    asset_symbol: str,
    force_refresh: bool = Query(False, description="Skip cache and fetch fresh data"),
    oracle: PriceOracleClient = Depends(get_price_oracle),
):
    """
    Get current USD price for a single asset.

    Args:
        asset_symbol: Asset symbol (ETH, BTC, USDC, USDT)
        force_refresh: Skip cache and fetch fresh price

    Returns:
        Current price with metadata
    """
    try:
        asset_symbol = asset_symbol.upper()

        # Fetch price
        price = await oracle.get_price(asset_symbol, force_refresh=force_refresh)

        # Determine if from cache
        from_cache = not force_refresh and asset_symbol in oracle.cache

        # Determine source (check which provider succeeded)
        source = "chainlink"  # Default, would need to track in client

        return PriceResponse(
            asset_symbol=asset_symbol,
            price_usd=price,
            source=source,
            timestamp=datetime.utcnow(),
            from_cache=from_cache,
        )

    except PriceOracleException as e:
        logger.error(f"Failed to fetch price for {asset_symbol}: {e}")
        raise HTTPException(
            status_code=503, detail=f"Failed to fetch price for {asset_symbol}: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching price for {asset_symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/", response_model=MultiplePricesResponse)
async def get_multiple_prices(
    symbols: List[str] = Query(..., description="List of asset symbols", alias="symbols"),
    force_refresh: bool = Query(False, description="Skip cache and fetch fresh data"),
    oracle: PriceOracleClient = Depends(get_price_oracle),
):
    """
    Get current USD prices for multiple assets.

    Args:
        symbols: List of asset symbols (e.g., ["ETH", "BTC", "USDC"])
        force_refresh: Skip cache and fetch fresh prices

    Returns:
        Dictionary of prices by symbol
    """
    try:
        # Fetch prices in parallel
        prices_dict = await oracle.get_multiple_prices(symbols, force_refresh=force_refresh)

        # Build response
        prices_response = {}
        for symbol, price in prices_dict.items():
            from_cache = not force_refresh and symbol in oracle.cache

            prices_response[symbol] = PriceResponse(
                asset_symbol=symbol,
                price_usd=price,
                source="chainlink",  # Would need to track per symbol
                timestamp=datetime.utcnow(),
                from_cache=from_cache,
            )

        return MultiplePricesResponse(
            prices=prices_response, timestamp=datetime.utcnow(), count=len(prices_response)
        )

    except Exception as e:
        logger.error(f"Failed to fetch multiple prices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch prices: {str(e)}")


@router.get("/{asset_symbol}/historical", response_model=HistoricalPricesResponse)
async def get_historical_prices(
    asset_symbol: str,
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
    oracle: PriceOracleClient = Depends(get_price_oracle),
):
    """
    Get historical daily prices for an asset.

    Args:
        asset_symbol: Asset symbol (ETH, BTC, USDC, USDT)
        days: Number of days of history (1-365)

    Returns:
        Historical price data
    """
    try:
        asset_symbol = asset_symbol.upper()

        # Fetch historical prices
        historical_data = await oracle.get_historical_prices(asset_symbol, days)

        # Convert to response model
        price_points = [
            HistoricalPricePoint(timestamp=ts, price_usd=price) for ts, price in historical_data
        ]

        return HistoricalPricesResponse(
            asset_symbol=asset_symbol,
            prices=price_points,
            days=days,
            count=len(price_points),
            source="coingecko",  # Historical data from Coingecko
        )

    except PriceOracleException as e:
        logger.error(f"Failed to fetch historical prices for {asset_symbol}: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to fetch historical prices: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching historical prices for {asset_symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/cache/clear")
async def clear_cache(oracle: PriceOracleClient = Depends(get_price_oracle)):
    """
    Clear price cache (admin endpoint).

    Forces all subsequent requests to fetch fresh data.
    """
    oracle.clear_cache()

    return {
        "message": "Price cache cleared successfully",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
