"""Message monitor for tracking cross-chain messages via Axelar and CCIP."""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Optional

from app.integrations.axelar_client import AxelarClient
from app.integrations.ccip_client import CCIPClient
from google.cloud import pubsub_v1
from infrastructure.db.models import BridgeProtocol, CrossChainMessage, MessageStatus
from infrastructure.db.session import get_session_factory
from sqlalchemy import select

logger = logging.getLogger(__name__)


class MessageMonitor:
    """Monitors cross-chain messages via AxelarScan API and CCIP."""

    def __init__(self, session_factory=None):
        self.running = False
        self.poll_interval = int(os.getenv("MESSAGE_MONITOR_INTERVAL", "30"))  # seconds
        self.project_id = os.getenv("GCP_PROJECT")
        self.pubsub_topic = os.getenv("CROSS_CHAIN_MESSAGES_TOPIC", "cross-chain.messages.v1")
        # Use provided session_factory or get default one
        if session_factory:
            self.session_factory = session_factory
        else:
            from infrastructure.db.session import get_session_factory

            self.session_factory = get_session_factory()

        # Initialize API clients
        self.axelar_client = AxelarClient()
        self.ccip_client = CCIPClient()

    async def start(self):
        """Start monitoring cross-chain messages."""
        if not self.project_id:
            logger.warning("GCP_PROJECT not set, message monitor will not publish to Pub/Sub")

        self.running = True
        logger.info(f"Starting message monitor (poll interval: {self.poll_interval}s)")

        # Start background monitoring task
        asyncio.create_task(self._monitor_loop())

    async def stop(self):
        """Stop monitoring."""
        self.running = False
        await self.axelar_client.close()
        await self.ccip_client.close()
        logger.info("Message monitor stopped")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                await self._check_messages()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error in message monitor loop: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

    async def _check_messages(self):
        """Check for pending messages and update their status."""
        try:
            async with self.session_factory() as session:
                # Get all pending/sent messages
                query = select(CrossChainMessage).where(
                    (CrossChainMessage.status == MessageStatus.PENDING)
                    | (CrossChainMessage.status == MessageStatus.SENT)
                    | (CrossChainMessage.status == MessageStatus.CONFIRMED)
                )

                result = await session.execute(query)
                messages = result.scalars().all()

                for message in messages:
                    try:
                        await self._update_message_status(session, message)
                    except Exception as e:
                        logger.error(
                            f"Failed to update message {message.message_id}: {e}",
                            exc_info=True,
                        )

                await session.commit()
        except Exception as e:
            logger.error(f"Error checking messages: {e}", exc_info=True)

    async def _update_message_status(self, session, message: CrossChainMessage):
        """Update status of a single message by querying the bridge protocol."""
        if not message.transaction_hash:
            return

        status_info = None

        if message.protocol == BridgeProtocol.AXELAR:
            status_info = await self.axelar_client.get_gmp_transaction_status(
                message.transaction_hash
            )
        elif message.protocol == BridgeProtocol.CCIP:
            status_info = await self.ccip_client.get_message_status(
                message.transaction_hash,
                message.source_chain,
                message.destination_chain,
            )

        if not status_info:
            return

        # Update message status based on protocol response
        new_status = self._map_protocol_status_to_message_status(status_info.get("status"))

        if new_status and new_status != message.status:
            message.status = new_status
            message.updated_at = datetime.utcnow()

            if new_status == MessageStatus.DELIVERED:
                message.completed_at = datetime.utcnow()

                # Update linked settlement status
                from sqlalchemy import text

                await session.execute(
                    text(
                        """
                        UPDATE settlement_records
                        SET status = 'completed', completed_at = NOW()
                        WHERE message_id = :message_id AND status = 'pending'
                    """
                    ),
                    {"message_id": message.message_id},
                )
                await session.commit()
                logger.info(
                    f"Updated settlement status to 'completed' for message {message.message_id}"
                )

            # Publish event to Pub/Sub
            await self.publish_message_event(message)

            logger.info(
                f"Updated message {message.message_id} from {message.status} to {new_status}"
            )

    def _map_protocol_status_to_message_status(
        self, protocol_status: Optional[str]
    ) -> Optional[MessageStatus]:
        """Map protocol-specific status to our MessageStatus enum."""
        if not protocol_status:
            return None

        status_lower = protocol_status.lower()

        # Axelar status mapping
        if "pending" in status_lower or "processing" in status_lower:
            return MessageStatus.PENDING
        elif "sent" in status_lower or "broadcast" in status_lower:
            return MessageStatus.SENT
        elif "confirmed" in status_lower or "executed" in status_lower:
            return MessageStatus.CONFIRMED
        elif "delivered" in status_lower or "completed" in status_lower:
            return MessageStatus.DELIVERED
        elif "failed" in status_lower or "error" in status_lower:
            return MessageStatus.FAILED

        return None

    async def publish_message_event(self, message: CrossChainMessage):
        """Publish message event to Pub/Sub."""
        if not self.project_id:
            return

        try:
            publisher = pubsub_v1.PublisherClient()
            topic_path = publisher.topic_path(self.project_id, self.pubsub_topic)

            event = {
                "message_id": message.message_id,
                "source_chain": message.source_chain,
                "destination_chain": message.destination_chain,
                "status": message.status.value,
                "protocol": message.protocol.value,
                "transaction_hash": message.transaction_hash,
                "updated_at": (message.updated_at.isoformat() if message.updated_at else None),
            }

            message_bytes = json.dumps(event).encode("utf-8")
            future = publisher.publish(topic_path, message_bytes)
            message_id = future.result()

            logger.info(f"Published cross-chain message event: {message_id}")
        except Exception as e:
            logger.error(f"Failed to publish message event: {e}", exc_info=True)
