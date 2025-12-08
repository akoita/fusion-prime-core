"""Retry coordinator for failed cross-chain messages."""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.services.bridge_executor import BridgeExecutor
from app.services.message_service import MessageService
from infrastructure.db.models import BridgeProtocol, CrossChainMessage, MessageStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class RetryCoordinator:
    """Coordinates retries for failed cross-chain messages."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.max_retries = int(os.getenv("MAX_MESSAGE_RETRIES", "3"))
        self.retry_delay_seconds = int(os.getenv("RETRY_DELAY_SECONDS", "60"))
        self.exponential_backoff = os.getenv("RETRY_EXPONENTIAL_BACKOFF", "true").lower() == "true"

    async def find_failed_messages(self, limit: int = 100) -> List[CrossChainMessage]:
        """Find messages that have failed and are eligible for retry."""
        query = (
            select(CrossChainMessage)
            .where(CrossChainMessage.status == MessageStatus.FAILED)
            .where(CrossChainMessage.retry_count < CrossChainMessage.max_retries)
            .order_by(CrossChainMessage.created_at.asc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        messages = result.scalars().all()

        # Filter by retry delay (don't retry too frequently)
        eligible = []
        for message in messages:
            if await self._is_eligible_for_retry(message):
                eligible.append(message)

        return eligible

    async def _is_eligible_for_retry(self, message: CrossChainMessage) -> bool:
        """Check if a message is eligible for retry based on timing."""
        if message.updated_at is None:
            return True

        # Calculate delay based on retry count (exponential backoff)
        delay = self.retry_delay_seconds
        if self.exponential_backoff:
            delay = delay * (2**message.retry_count)

        elapsed = datetime.utcnow() - message.updated_at.replace(tzinfo=None)
        return elapsed.total_seconds() >= delay

    async def retry_message(self, message: CrossChainMessage) -> bool:
        """
        Retry a failed cross-chain message.

        Args:
            message: The message to retry

        Returns:
            True if retry was initiated, False otherwise
        """
        if message.retry_count >= message.max_retries:
            logger.warning(
                f"Message {message.message_id} has exceeded max retries ({message.max_retries})"
            )
            return False

        if not await self._is_eligible_for_retry(message):
            logger.debug(f"Message {message.message_id} not yet eligible for retry")
            return False

        try:
            # Update message status to retrying
            message.status = MessageStatus.RETRYING
            message.retry_count += 1
            message.updated_at = datetime.utcnow()

            await self.session.commit()
            await self.session.refresh(message)

            logger.info(
                f"Retrying message {message.message_id} (attempt {message.retry_count}/{message.max_retries})"
            )

            # Actually trigger the retry by executing bridge transaction again
            try:
                # Extract payload from message
                payload_dict = (
                    message.payload
                    if isinstance(message.payload, dict)
                    else json.loads(message.payload)
                )

                # Re-encode payload for bridge execution
                from eth_abi import encode

                # Extract settlement details from payload (assuming settlement payload format)
                settlement_id = payload_dict.get("settlement_id", message.message_id)
                amount = payload_dict.get("amount", 0)
                asset = payload_dict.get("asset", "ETH")

                # Convert amount to wei
                amount_multiplier = 1e18 if asset.upper() in ["ETH", "WETH"] else 1e6
                amount_wei = int(amount * amount_multiplier)

                # Encode payload (same format as in orchestrator_service)
                payload = encode(
                    ["string", "uint256", "string", "string", "string"],
                    [
                        settlement_id,
                        amount_wei,
                        asset,
                        message.source_chain,
                        message.destination_chain,
                    ],
                )

                # Execute bridge transaction via BridgeExecutor
                executor = BridgeExecutor(source_chain=message.source_chain)
                protocol = (
                    BridgeProtocol(message.protocol)
                    if isinstance(message.protocol, str)
                    else message.protocol
                )

                new_tx_hash = await executor.execute_settlement(
                    protocol=protocol,
                    destination_chain=message.destination_chain,
                    destination_address=message.destination_address,
                    payload=payload,
                    gas_value=1000000000000000,  # 0.001 ETH in wei
                )

                # Update message with new transaction hash
                message.transaction_hash = new_tx_hash
                message.status = MessageStatus.PENDING
                message.updated_at = datetime.utcnow()

                await self.session.commit()

                logger.info(
                    f"Successfully retried message {message.message_id} with new tx: {new_tx_hash}"
                )

                return True

            except Exception as retry_error:
                logger.error(
                    f"Failed to execute retry for message {message.message_id}: {retry_error}",
                    exc_info=True,
                )
                # Mark as failed if retry execution fails
                message.status = MessageStatus.FAILED
                await self.session.commit()
                return False

        except Exception as e:
            logger.error(f"Failed to retry message {message.message_id}: {e}", exc_info=True)
            await self.session.rollback()
            return False

    async def process_retry_queue(self, batch_size: int = 10):
        """Process a batch of failed messages for retry."""
        failed_messages = await self.find_failed_messages(limit=batch_size)

        if not failed_messages:
            logger.debug("No messages eligible for retry")
            return

        logger.info(f"Processing {len(failed_messages)} messages for retry")

        # Retry messages with some concurrency
        tasks = [self.retry_message(msg) for msg in failed_messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if r is True)
        logger.info(f"Retried {success_count}/{len(failed_messages)} messages successfully")
