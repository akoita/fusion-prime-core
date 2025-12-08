"""
Pub/Sub publisher for broadcasting price updates.

Publishes to market.prices.v1 topic for consumption by risk engine and other services.
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from google.api_core import retry
from google.cloud import pubsub_v1

logger = logging.getLogger(__name__)


class PricePublisher:
    """
    Publisher for market price updates to Pub/Sub.

    Publishes price data to `market.prices.v1` topic for consumption by:
    - Risk Engine (for VaR calculations)
    - Settlement Service (for USD valuations)
    - Analytics pipelines
    """

    def __init__(self, project_id: str, topic_name: str = "market.prices.v1"):
        """
        Initialize Pub/Sub publisher.

        Args:
            project_id: GCP project ID
            topic_name: Pub/Sub topic name (default: market.prices.v1)
        """
        self.project_id = project_id
        self.topic_name = topic_name
        self.topic_path = f"projects/{project_id}/topics/{topic_name}"

        # Initialize publisher client
        self.publisher = pubsub_v1.PublisherClient()

        logger.info(f"Price publisher initialized for topic: {self.topic_path}")

    async def publish_price(
        self,
        asset_symbol: str,
        price_usd: Decimal,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Publish a single price update.

        Args:
            asset_symbol: Asset symbol (ETH, BTC, etc.)
            price_usd: Current USD price
            source: Price source (chainlink, pyth, coingecko)
            metadata: Additional metadata (feed_address, confidence, etc.)

        Returns:
            Message ID from Pub/Sub
        """
        message = {
            "asset_symbol": asset_symbol.upper(),
            "price_usd": str(price_usd),
            "source": source,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": metadata or {},
        }

        # Publish to Pub/Sub
        message_data = json.dumps(message).encode("utf-8")

        future = self.publisher.publish(
            self.topic_path,
            message_data,
            asset_symbol=asset_symbol.upper(),  # Attribute for filtering
            source=source,
        )

        # Wait for publish confirmation
        message_id = future.result(timeout=5.0)

        logger.debug(
            f"Published price for {asset_symbol}: ${price_usd} "
            f"(source: {source}, message_id: {message_id})"
        )

        return message_id

    async def publish_multiple_prices(
        self,
        prices: Dict[str, Decimal],
        source: str,
        metadata: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> list[str]:
        """
        Publish multiple price updates in batch.

        Args:
            prices: Dictionary mapping asset_symbol to price
            source: Price source
            metadata: Optional metadata per asset

        Returns:
            List of message IDs
        """
        message_ids = []

        for asset_symbol, price_usd in prices.items():
            asset_metadata = metadata.get(asset_symbol) if metadata else None

            try:
                message_id = await self.publish_price(
                    asset_symbol, price_usd, source, asset_metadata
                )
                message_ids.append(message_id)
            except Exception as e:
                logger.error(f"Failed to publish price for {asset_symbol}: {e}")

        logger.info(
            f"Published {len(message_ids)}/{len(prices)} price updates " f"(source: {source})"
        )

        return message_ids

    async def publish_historical_prices(
        self, asset_symbol: str, historical_prices: list[tuple[datetime, Decimal]], source: str
    ) -> list[str]:
        """
        Publish historical price data (for backtesting/analytics).

        Args:
            asset_symbol: Asset symbol
            historical_prices: List of (timestamp, price) tuples
            source: Price source

        Returns:
            List of message IDs
        """
        message_ids = []

        for timestamp, price in historical_prices:
            message = {
                "asset_symbol": asset_symbol.upper(),
                "price_usd": str(price),
                "source": source,
                "timestamp": timestamp.isoformat() + "Z",
                "historical": True,
            }

            message_data = json.dumps(message).encode("utf-8")

            try:
                future = self.publisher.publish(
                    self.topic_path,
                    message_data,
                    asset_symbol=asset_symbol.upper(),
                    source=source,
                    historical="true",
                )

                message_id = future.result(timeout=5.0)
                message_ids.append(message_id)

            except Exception as e:
                logger.error(
                    f"Failed to publish historical price for {asset_symbol} " f"at {timestamp}: {e}"
                )

        logger.info(
            f"Published {len(message_ids)}/{len(historical_prices)} "
            f"historical prices for {asset_symbol}"
        )

        return message_ids

    def close(self):
        """Close publisher client."""
        # Flush any pending messages
        self.publisher.stop()
        logger.info("Price publisher closed")
