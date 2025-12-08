"""Pub/Sub consumer for market price updates."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import Callable
from decimal import Decimal
from typing import Optional

from google.cloud import pubsub_v1

logger = logging.getLogger(__name__)


class _MockSubscriber:
    def subscription_path(self, project_id: str, subscription_id: str) -> str:
        return f"projects/{project_id}/subscriptions/{subscription_id}"

    def subscribe(self, path: str, callback):  # pragma: no cover
        raise RuntimeError("Mock subscriber does not support streaming pulls")


class PriceEventConsumer:
    """Consumes price updates from Pub/Sub and updates price cache."""

    def __init__(
        self,
        project_id: str,
        subscription_id: str,
        price_cache_handler: Callable[[dict], None],
        subscriber: Optional[pubsub_v1.SubscriberClient] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        mode = os.getenv("FUSION_PRIME_PUBSUB_TEST_MODE", "").lower()
        if subscriber is not None:
            self._subscriber = subscriber
        elif mode == "mock":
            self._subscriber = _MockSubscriber()
        else:
            self._subscriber = pubsub_v1.SubscriberClient()

        self._subscription_path = self._subscriber.subscription_path(project_id, subscription_id)
        self._price_cache_handler = price_cache_handler
        self._loop = loop

    def _callback(self, message: pubsub_v1.subscriber.message.Message) -> None:
        """Process incoming Pub/Sub messages."""
        try:
            logger.info(
                "Received price update from Pub/Sub",
                extra={"message_id": message.message_id, "attributes": dict(message.attributes)},
            )

            # Parse JSON message
            price_data = json.loads(message.data.decode("utf-8"))

            # Extract price info
            asset_symbol = price_data.get("asset_symbol")
            price_usd = price_data.get("price_usd")

            if not asset_symbol or price_usd is None:
                logger.warning(f"Invalid price update: missing asset_symbol or price_usd")
                message.ack()
                return

            logger.info(
                f"Processing price update: {asset_symbol} = ${price_usd}",
                extra={
                    "asset_symbol": asset_symbol,
                    "price_usd": price_usd,
                    "source": price_data.get("source", "unknown"),
                },
            )

            # Call price cache handler
            self._price_cache_handler(price_data)

            message.ack()
            logger.debug(f"Price update acknowledged for {asset_symbol}")

        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse message JSON: {e}", extra={"message_id": message.message_id}
            )
            message.nack()
        except Exception as e:
            logger.error(
                f"Failed to process Pub/Sub message: {e}",
                extra={"message_id": message.message_id},
                exc_info=True,
            )
            message.nack()

    def start(self) -> pubsub_v1.subscriber.futures.StreamingPullFuture:
        """Start the subscriber."""
        if isinstance(self._subscriber, _MockSubscriber):  # pragma: no cover
            raise RuntimeError("Mock subscriber does not support start(); call _callback directly")

        logger.info(f"Starting price event consumer for subscription: {self._subscription_path}")
        return self._subscriber.subscribe(self._subscription_path, callback=self._callback)


def create_price_cache_handler(
    price_oracle_client, loop: Optional[asyncio.AbstractEventLoop] = None
):
    """
    Create handler that updates price oracle client cache.

    Args:
        price_oracle_client: PriceOracleClient instance for caching prices
        loop: Event loop to use for scheduling coroutines

    Returns:
        Callable that processes price events
    """

    def price_cache_handler(price_data: dict) -> None:
        """
        Handle price update events by updating the local cache.

        This is called after the event has been received from Pub/Sub.
        It updates the Price Oracle client's cache with the latest price.
        """
        try:
            # Extract price information
            asset_symbol = price_data.get("asset_symbol")
            price_usd = price_data.get("price_usd")

            if not asset_symbol or price_usd is None:
                logger.error("Invalid price data: missing asset_symbol or price_usd")
                return

            # Convert to Decimal for precision
            price_decimal = Decimal(str(price_usd))

            logger.info(f"Updating price cache: {asset_symbol} = ${price_decimal}")

            # Update price oracle client's cache
            # This is synchronous and thread-safe
            if hasattr(price_oracle_client, "update_cache"):
                price_oracle_client.update_cache(asset_symbol, price_decimal)
                logger.info(f"Price cache updated successfully for {asset_symbol}")
            else:
                logger.warning("Price oracle client does not have update_cache method")

        except Exception as e:
            logger.error(f"Failed to update price cache: {e}", exc_info=True)

    return price_cache_handler
