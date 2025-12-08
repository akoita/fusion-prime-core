"""
Base Pub/Sub Subscriber for Blockchain Event Indexers

Provides common Pub/Sub subscription logic that can be extended by specific indexers.
"""

import json
import logging
from abc import ABC, abstractmethod
from concurrent.futures import TimeoutError
from typing import Any, Dict

from google.cloud import pubsub_v1
from google.cloud.pubsub_v1.subscriber.message import Message

logger = logging.getLogger(__name__)


class BaseEventProcessor(ABC):
    """Abstract base class for event processors."""

    @abstractmethod
    def process_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """
        Process an event.

        Args:
            event_type: Type of event (e.g., "EscrowDeployed")
            event_data: Event data dictionary

        Returns:
            True if successfully processed, False otherwise
        """
        pass


class BaseEventSubscriber:
    """Base Pub/Sub subscriber for blockchain events."""

    def __init__(
        self,
        project_id: str,
        subscription_id: str,
        event_processor: BaseEventProcessor,
        timeout: float = None,
        service_name: str = "indexer",
    ):
        """
        Initialize base subscriber.

        Args:
            project_id: GCP project ID
            subscription_id: Pub/Sub subscription ID
            event_processor: Event processor implementation
            timeout: Optional timeout for pulling messages (None = run forever)
            service_name: Name of the service (for logging)
        """
        self.project_id = project_id
        self.subscription_id = subscription_id
        self.event_processor = event_processor
        self.timeout = timeout
        self.service_name = service_name

        self.subscriber = pubsub_v1.SubscriberClient()
        self.subscription_path = self.subscriber.subscription_path(project_id, subscription_id)

        self.messages_processed = 0
        self.messages_failed = 0

        logger.info(f"Initialized {service_name} Pub/Sub subscriber")
        logger.info(f"  Project: {project_id}")
        logger.info(f"  Subscription: {subscription_id}")

    def _callback(self, message: Message):
        """
        Process a Pub/Sub message.

        Args:
            message: Pub/Sub message
        """
        try:
            # Get event type from message attributes
            event_type = message.attributes.get("event_type")
            if not event_type:
                logger.warning("Message missing event_type attribute, skipping")
                message.ack()
                return

            # Parse event data
            try:
                event_data = json.loads(message.data.decode("utf-8"))
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse message data: {e}")
                message.ack()  # Ack to avoid reprocessing bad data
                self.messages_failed += 1
                return

            logger.info(f"📨 Received {event_type} event")
            logger.debug(f"Event data: {event_data}")

            # Process event using injected processor
            success = self.event_processor.process_event(event_type, event_data)

            if success:
                message.ack()
                self.messages_processed += 1
                logger.info(f"✅ Successfully processed {event_type}")
            else:
                message.nack()
                self.messages_failed += 1
                logger.error(f"❌ Failed to process {event_type}, message will be retried")

        except Exception as e:
            logger.error(f"Error in callback: {e}", exc_info=True)
            message.nack()  # Retry on error
            self.messages_failed += 1

    def start(self):
        """Start subscribing to messages."""
        logger.info(
            f"🚀 Starting {self.service_name} Pub/Sub subscription: {self.subscription_path}"
        )

        streaming_pull_future = self.subscriber.subscribe(
            self.subscription_path, callback=self._callback
        )

        logger.info("✅ Listening for messages...")

        try:
            # Block and wait for messages
            if self.timeout:
                streaming_pull_future.result(timeout=self.timeout)
            else:
                streaming_pull_future.result()  # Run forever
        except TimeoutError:
            logger.info(f"Timeout reached ({self.timeout}s), shutting down")
            streaming_pull_future.cancel()
            streaming_pull_future.result()  # Wait for cleanup
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down")
            streaming_pull_future.cancel()
            streaming_pull_future.result()
        except Exception as e:
            logger.error(f"Error in subscriber: {e}", exc_info=True)
            streaming_pull_future.cancel()
            raise

        logger.info(f"📊 {self.service_name} subscriber stats:")
        logger.info(f"  Messages processed: {self.messages_processed}")
        logger.info(f"  Messages failed: {self.messages_failed}")

    def get_stats(self) -> Dict[str, Any]:
        """Get subscriber statistics."""
        return {
            "service": self.service_name,
            "messages_processed": self.messages_processed,
            "messages_failed": self.messages_failed,
            "subscription_path": self.subscription_path,
        }
