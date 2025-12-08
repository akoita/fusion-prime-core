"""Pub/Sub consumer for margin alert events."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import Callable
from typing import Optional

from google.cloud import pubsub_v1

logger = logging.getLogger(__name__)


class _MockSubscriber:
    def subscription_path(self, project_id: str, subscription_id: str) -> str:
        return f"projects/{project_id}/subscriptions/{subscription_id}"

    def subscribe(self, path: str, callback):  # pragma: no cover
        raise RuntimeError("Mock subscriber does not support streaming pulls")


class AlertEventConsumer:
    """Consumes margin alert events from Pub/Sub and triggers notifications."""

    def __init__(
        self,
        project_id: str,
        subscription_id: str,
        notification_handler: Callable[[dict], None],
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
        self._notification_handler = notification_handler
        self._loop = loop

    def _callback(self, message: pubsub_v1.subscriber.message.Message) -> None:
        """Process incoming Pub/Sub messages."""
        try:
            logger.info(
                "Received margin alert from Pub/Sub",
                extra={"message_id": message.message_id, "attributes": dict(message.attributes)},
            )

            # Parse JSON message
            alert_data = json.loads(message.data.decode("utf-8"))

            # Extract event type from attributes or data
            event_type = message.attributes.get("event_type") or alert_data.get(
                "event_type", "unknown"
            )

            logger.info(
                f"Processing margin alert: {event_type}",
                extra={
                    "event_type": event_type,
                    "user_id": alert_data.get("user_id"),
                    "severity": alert_data.get("severity"),
                    "health_score": alert_data.get("health_score"),
                },
            )

            # Handle alert events
            if event_type in [
                "margin_warning",
                "margin_call",
                "liquidation_imminent",
                "health_warning",
            ]:
                # Call notification handler (synchronously)
                self._notification_handler(alert_data)
                logger.info(
                    f"Margin alert {event_type} processed for user {alert_data.get('user_id')}"
                )
            else:
                logger.warning(f"Unknown event type received: {event_type}")

            message.ack()
            logger.info("Message acknowledged successfully")

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

        logger.info(f"Starting alert event consumer for subscription: {self._subscription_path}")
        return self._subscriber.subscribe(self._subscription_path, callback=self._callback)


def create_alert_handler(notification_manager, loop: Optional[asyncio.AbstractEventLoop] = None):
    """
    Create alert event handler that uses the notification manager.

    Args:
        notification_manager: NotificationManager instance for sending notifications
        loop: Event loop to use for scheduling coroutines

    Returns:
        Callable that processes alert events
    """

    def alert_event_handler(alert_data: dict) -> None:
        """
        Handle margin alert events by sending notifications.

        This is called after the event has been received from Pub/Sub.
        It triggers notification delivery via email, SMS, or webhook.
        """
        logger.info(
            "Processing margin alert for notification delivery",
            extra={
                "event_type": alert_data.get("event_type"),
                "user_id": alert_data.get("user_id"),
                "severity": alert_data.get("severity"),
            },
        )

        # Schedule notification sending (async)
        # Use run_coroutine_threadsafe since Pub/Sub callback runs in a thread pool
        try:
            if loop is None:
                logger.error("No event loop provided to alert handler")
                return

            # Schedule the coroutine in the main event loop
            future = asyncio.run_coroutine_threadsafe(
                notification_manager.send_notification(
                    user_id=alert_data.get("user_id"),
                    alert_type=alert_data.get("event_type", "margin_alert"),
                    severity=alert_data.get("severity", "medium"),
                    message=alert_data.get("message", "Margin alert triggered"),
                    metadata=alert_data,
                ),
                loop,
            )

            logger.info(f"Notification scheduled for user {alert_data.get('user_id')}")

        except Exception as e:
            logger.error(f"Failed to schedule notification: {e}", exc_info=True)

    return alert_event_handler
