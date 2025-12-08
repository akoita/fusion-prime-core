"""
Pub/Sub Subscriber for Escrow Indexer.
Subscribes to blockchain events and processes them.
"""

import json
import logging
import os
from concurrent.futures import TimeoutError
from typing import Callable

from google.cloud import pubsub_v1
from google.cloud.pubsub_v1.subscriber.message import Message
from infrastructure.db import get_db_session

from .event_processor import EscrowEventProcessor

logger = logging.getLogger(__name__)


class EscrowEventSubscriber:
    """Subscribes to Pub/Sub and processes escrow events."""

    def __init__(
        self,
        project_id: str,
        subscription_id: str,
        timeout: float = None,
    ):
        """
        Initialize subscriber.

        Args:
            project_id: GCP project ID
            subscription_id: Pub/Sub subscription ID
            timeout: Optional timeout for pulling messages (None = run forever)
        """
        self.project_id = project_id
        self.subscription_id = subscription_id
        self.timeout = timeout

        self.subscriber = pubsub_v1.SubscriberClient()
        self.subscription_path = self.subscriber.subscription_path(project_id, subscription_id)

        self.messages_processed = 0
        self.messages_failed = 0

        logger.info(f"Initialized Pub/Sub subscriber")
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

            # Process event in database
            with get_db_session() as db:
                processor = EscrowEventProcessor(db)
                success = processor.process_event(event_type, event_data)

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
        logger.info(f"🚀 Starting Pub/Sub subscription: {self.subscription_path}")

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

        logger.info(f"📊 Subscriber stats:")
        logger.info(f"  Messages processed: {self.messages_processed}")
        logger.info(f"  Messages failed: {self.messages_failed}")

    def get_stats(self):
        """Get subscriber statistics."""
        return {
            "messages_processed": self.messages_processed,
            "messages_failed": self.messages_failed,
            "subscription_path": self.subscription_path,
        }
