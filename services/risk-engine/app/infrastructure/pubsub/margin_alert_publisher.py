"""
Pub/Sub Publisher for Margin Alerts.

Publishes margin events (warnings, margin calls, liquidations) to the alerts.margin.v1 topic.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from google.api_core import retry
from google.cloud import pubsub_v1

logger = logging.getLogger(__name__)


class MarginAlertPublisher:
    """
    Publisher for margin alert events to Pub/Sub.

    Publishes to: alerts.margin.v1
    """

    def __init__(self, project_id: str, topic_name: str = "alerts.margin.v1"):
        """
        Initialize margin alert publisher.

        Args:
            project_id: GCP project ID
            topic_name: Pub/Sub topic name
        """
        self.project_id = project_id
        self.topic_name = topic_name
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(project_id, topic_name)

        logger.info(f"Margin alert publisher initialized: {self.topic_path}")

    async def publish_margin_event(self, event: Dict[str, Any]) -> str:
        """
        Publish a margin event to Pub/Sub.

        Args:
            event: Margin event dictionary containing:
                - event_type: "margin_warning" | "margin_call" | "liquidation_imminent"
                - user_id: User identifier
                - health_score: Current health score
                - status: Health status
                - severity: Event severity
                - message: Human-readable message
                - timestamp: ISO 8601 timestamp

        Returns:
            Published message ID

        Raises:
            Exception: If publish fails
        """
        try:
            # Validate required fields
            required_fields = ["event_type", "user_id", "health_score", "severity"]
            for field in required_fields:
                if field not in event:
                    raise ValueError(f"Missing required field: {field}")

            # Add metadata
            message = {
                **event,
                "published_at": datetime.utcnow().isoformat() + "Z",
                "topic": self.topic_name,
            }

            # Convert to JSON
            message_data = json.dumps(message).encode("utf-8")

            # Publish with attributes for filtering
            future = self.publisher.publish(
                self.topic_path,
                message_data,
                event_type=event["event_type"],
                user_id=event["user_id"],
                severity=event["severity"],
                health_status=event.get("status", ""),
            )

            # Wait for publish confirmation
            message_id = future.result(timeout=5.0)

            logger.info(
                f"Published margin event: {event['event_type']} for user {event['user_id']} "
                f"(message_id={message_id})"
            )

            return message_id

        except Exception as e:
            logger.error(f"Failed to publish margin event: {e}")
            raise

    async def publish_batch_margin_events(self, events: list[Dict[str, Any]]) -> list[str]:
        """
        Publish multiple margin events in batch.

        Args:
            events: List of margin event dictionaries

        Returns:
            List of published message IDs
        """
        message_ids = []

        for event in events:
            try:
                message_id = await self.publish_margin_event(event)
                message_ids.append(message_id)
            except Exception as e:
                logger.error(f"Failed to publish event in batch: {e}")
                # Continue with other events

        logger.info(f"Published {len(message_ids)}/{len(events)} margin events in batch")
        return message_ids

    def close(self):
        """Close the publisher client."""
        # PublisherClient doesn't have an explicit close method in recent versions
        # But we should ensure all pending futures are resolved
        pass
