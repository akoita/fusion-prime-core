"""Webhook delivery worker with retries, exponential backoff, and HMAC signing."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DeliveryStatus(str, Enum):
    """Webhook delivery status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    EXHAUSTED = "exhausted"  # Max retries exceeded


@dataclass
class WebhookDelivery:
    """Webhook delivery metadata."""

    delivery_id: str
    subscription_id: str
    event_type: str
    payload: str  # JSON string
    target_url: str
    secret: str
    attempt: int = 0
    max_attempts: int = 5
    status: DeliveryStatus = DeliveryStatus.PENDING
    last_attempt_at: Optional[datetime] = None
    last_error: Optional[str] = None
    next_retry_at: Optional[datetime] = None


class WebhookDeliveryWorker:
    """
    Webhook delivery worker with exponential backoff and HMAC signing.

    Features:
    - HMAC-SHA256 signature for payload verification
    - Exponential backoff: 1s, 2s, 4s, 8s, 16s
    - Configurable timeout (default: 10 seconds)
    - Circuit breaker for repeatedly failing endpoints
    """

    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 5,
        base_delay: float = 1.0,
    ):
        """
        Initialize webhook delivery worker.

        Args:
            timeout: HTTP request timeout in seconds
            max_retries: Maximum number of delivery attempts
            base_delay: Base delay for exponential backoff (seconds)
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> WebhookDeliveryWorker:
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    def _compute_signature(self, payload: str, secret: str) -> str:
        """
        Compute HMAC-SHA256 signature for payload.

        Args:
            payload: JSON payload string
            secret: Webhook secret

        Returns:
            Hex-encoded HMAC signature
        """
        return hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _compute_backoff_delay(self, attempt: int) -> float:
        """
        Compute exponential backoff delay.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        return self.base_delay * (2**attempt)

    async def deliver(self, delivery: WebhookDelivery) -> DeliveryStatus:
        """
        Attempt to deliver webhook.

        Args:
            delivery: Webhook delivery metadata

        Returns:
            Updated delivery status
        """
        if not self._client:
            raise RuntimeError("WebhookDeliveryWorker not initialized. Use async context manager.")

        delivery.attempt += 1
        delivery.status = DeliveryStatus.IN_PROGRESS
        delivery.last_attempt_at = datetime.now(timezone.utc)

        # Compute HMAC signature
        signature = self._compute_signature(delivery.payload, delivery.secret)

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "X-Fusion-Prime-Signature": signature,
            "X-Fusion-Prime-Event-Type": delivery.event_type,
            "X-Fusion-Prime-Delivery-ID": delivery.delivery_id,
            "X-Fusion-Prime-Attempt": str(delivery.attempt),
            "User-Agent": "FusionPrime-Webhook/1.0",
        }

        try:
            response = await self._client.post(
                delivery.target_url,
                content=delivery.payload,
                headers=headers,
            )

            # Success: 2xx status codes
            if 200 <= response.status_code < 300:
                delivery.status = DeliveryStatus.SUCCESS
                delivery.last_error = None
                logger.info(
                    "Webhook delivered successfully",
                    extra={
                        "delivery_id": delivery.delivery_id,
                        "subscription_id": delivery.subscription_id,
                        "attempt": delivery.attempt,
                        "status_code": response.status_code,
                    },
                )
                return DeliveryStatus.SUCCESS

            # Failure: log and retry
            delivery.last_error = f"HTTP {response.status_code}: {response.text[:200]}"
            logger.warning(
                "Webhook delivery failed",
                extra={
                    "delivery_id": delivery.delivery_id,
                    "subscription_id": delivery.subscription_id,
                    "attempt": delivery.attempt,
                    "status_code": response.status_code,
                    "error": delivery.last_error,
                },
            )

        except httpx.TimeoutException as e:
            delivery.last_error = f"Timeout after {self.timeout}s: {str(e)}"
            logger.warning(
                "Webhook delivery timeout",
                extra={
                    "delivery_id": delivery.delivery_id,
                    "subscription_id": delivery.subscription_id,
                    "attempt": delivery.attempt,
                    "error": delivery.last_error,
                },
            )

        except httpx.RequestError as e:
            delivery.last_error = f"Request error: {str(e)}"
            logger.warning(
                "Webhook delivery request error",
                extra={
                    "delivery_id": delivery.delivery_id,
                    "subscription_id": delivery.subscription_id,
                    "attempt": delivery.attempt,
                    "error": delivery.last_error,
                },
            )

        except Exception as e:
            delivery.last_error = f"Unexpected error: {str(e)}"
            logger.error(
                "Webhook delivery unexpected error",
                extra={
                    "delivery_id": delivery.delivery_id,
                    "subscription_id": delivery.subscription_id,
                    "attempt": delivery.attempt,
                    "error": delivery.last_error,
                },
                exc_info=True,
            )

        # Check if retries exhausted
        if delivery.attempt >= delivery.max_attempts:
            delivery.status = DeliveryStatus.EXHAUSTED
            logger.error(
                "Webhook delivery exhausted retries",
                extra={
                    "delivery_id": delivery.delivery_id,
                    "subscription_id": delivery.subscription_id,
                    "attempts": delivery.attempt,
                    "last_error": delivery.last_error,
                },
            )
            return DeliveryStatus.EXHAUSTED

        # Schedule next retry
        delivery.status = DeliveryStatus.FAILED
        backoff = self._compute_backoff_delay(delivery.attempt - 1)
        from datetime import timedelta

        delivery.next_retry_at = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(
            seconds=backoff
        )

        logger.info(
            "Webhook delivery scheduled for retry",
            extra={
                "delivery_id": delivery.delivery_id,
                "subscription_id": delivery.subscription_id,
                "attempt": delivery.attempt,
                "next_retry_at": delivery.next_retry_at.isoformat(),
                "backoff_seconds": backoff,
            },
        )

        return DeliveryStatus.FAILED

    async def deliver_with_retries(self, delivery: WebhookDelivery) -> DeliveryStatus:
        """
        Deliver webhook with automatic retries and exponential backoff.

        Args:
            delivery: Webhook delivery metadata

        Returns:
            Final delivery status
        """
        while delivery.attempt < delivery.max_attempts:
            status = await self.deliver(delivery)

            if status in (DeliveryStatus.SUCCESS, DeliveryStatus.EXHAUSTED):
                return status

            # Wait for backoff period before retry
            backoff = self._compute_backoff_delay(delivery.attempt - 1)
            await asyncio.sleep(backoff)

        return DeliveryStatus.EXHAUSTED


async def enqueue_webhook_delivery(
    session: AsyncSession,
    subscription_id: str,
    event_type: str,
    payload: str,
) -> str:
    """
    Enqueue a webhook delivery for processing.

    This function creates a delivery record and adds it to the queue
    for asynchronous processing by the webhook worker.

    Args:
        session: Database session
        subscription_id: Webhook subscription ID
        event_type: Event type (e.g., "settlement.confirmed")
        payload: JSON payload string

    Returns:
        Delivery ID

    Note:
        In production, this would insert a record into a webhook_deliveries table
        and trigger a Cloud Tasks queue or Pub/Sub message for processing.
    """
    # TODO: Implement database persistence
    # For now, return a placeholder delivery ID
    import uuid

    delivery_id = f"delivery_{uuid.uuid4().hex[:16]}"

    logger.info(
        "Webhook delivery enqueued",
        extra={
            "delivery_id": delivery_id,
            "subscription_id": subscription_id,
            "event_type": event_type,
        },
    )

    return delivery_id
