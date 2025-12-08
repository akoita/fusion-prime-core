"""
Price data models for API requests and responses.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class PriceResponse(BaseModel):
    """Single asset price response."""

    asset_symbol: str = Field(..., description="Asset symbol (ETH, BTC, etc.)")
    price_usd: Decimal = Field(..., description="Current USD price")
    source: str = Field(..., description="Price source (chainlink, pyth, coingecko)")
    timestamp: datetime = Field(..., description="Price timestamp")
    from_cache: bool = Field(False, description="Whether price was from cache")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    class Config:
        json_encoders = {Decimal: str, datetime: lambda v: v.isoformat() + "Z"}


class MultiplePricesResponse(BaseModel):
    """Multiple asset prices response."""

    prices: Dict[str, PriceResponse] = Field(..., description="Prices by asset symbol")
    timestamp: datetime = Field(..., description="Response timestamp")
    count: int = Field(..., description="Number of prices returned")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z"}


class HistoricalPricePoint(BaseModel):
    """Single historical price data point."""

    timestamp: datetime = Field(..., description="Price timestamp")
    price_usd: Decimal = Field(..., description="USD price at timestamp")

    class Config:
        json_encoders = {Decimal: str, datetime: lambda v: v.isoformat() + "Z"}


class HistoricalPricesResponse(BaseModel):
    """Historical prices response."""

    asset_symbol: str = Field(..., description="Asset symbol")
    prices: list[HistoricalPricePoint] = Field(..., description="Historical price data")
    days: int = Field(..., description="Number of days of history")
    count: int = Field(..., description="Number of data points")
    source: str = Field(..., description="Data source")

    class Config:
        json_encoders = {Decimal: str, datetime: lambda v: v.isoformat() + "Z"}


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status (healthy, degraded, unhealthy)")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field("1.0.0", description="Service version")
    components: Dict[str, str] = Field(..., description="Component health status")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z"}
