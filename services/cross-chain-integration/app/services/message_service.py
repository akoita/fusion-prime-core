"""Service for managing cross-chain messages."""

import logging
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from infrastructure.db.models import BridgeProtocol, CrossChainMessage, MessageStatus
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class MessageService:
    """Service for managing cross-chain messages."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_message(
        self,
        source_chain: str,
        destination_chain: str,
        source_address: str,
        destination_address: str,
        payload: dict,
        protocol: BridgeProtocol,
        transaction_hash: Optional[str] = None,
        block_number: Optional[int] = None,
    ) -> CrossChainMessage:
        """Create a new cross-chain message record."""
        import json

        message_id = f"msg-{uuid.uuid4().hex[:16]}"

        # Use raw SQL to properly cast enum value
        await self.session.execute(
            text(
                """
                INSERT INTO cross_chain_messages
                (message_id, source_chain, destination_chain, source_address, destination_address,
                 payload, status, protocol, transaction_hash, block_number, retry_count, max_retries)
                VALUES
                (:message_id, :source_chain, :destination_chain, :source_address, :destination_address,
                 :payload::json, :status, CAST(:protocol AS bridgeprotocol), :transaction_hash, :block_number, :retry_count, :max_retries)
            """
            ),
            {
                "message_id": message_id,
                "source_chain": source_chain,
                "destination_chain": destination_chain,
                "source_address": source_address,
                "destination_address": destination_address,
                "payload": json.dumps(payload),
                "status": MessageStatus.PENDING.value,
                "protocol": protocol.value,
                "transaction_hash": transaction_hash,
                "block_number": block_number,
                "retry_count": 0,
                "max_retries": 3,
            },
        )
        await self.session.commit()

        # Fetch the created message
        result = await self.session.execute(
            select(CrossChainMessage).where(CrossChainMessage.message_id == message_id)
        )
        message = result.scalar_one()

        logger.info(f"Created cross-chain message: {message_id}")
        return message

    async def update_message_status(
        self,
        message_id: str,
        status: Optional[MessageStatus] = None,
        transaction_hash: Optional[str] = None,
        block_number: Optional[int] = None,
    ) -> Optional[CrossChainMessage]:
        """Update message status."""
        result = await self.session.execute(
            select(CrossChainMessage).where(CrossChainMessage.message_id == message_id)
        )
        message = result.scalar_one_or_none()

        if not message:
            logger.warning(f"Message not found: {message_id}")
            return None

        if status:
            message.status = status
            if status == MessageStatus.DELIVERED:
                message.completed_at = datetime.utcnow()

        if transaction_hash:
            message.transaction_hash = transaction_hash

        if block_number:
            message.block_number = block_number

        message.updated_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(message)

        logger.info(f"Updated message: {message_id} to status {status}")
        return message

    async def get_message(self, message_id: str) -> Optional[CrossChainMessage]:
        """Get message by ID."""
        result = await self.session.execute(
            select(CrossChainMessage).where(CrossChainMessage.message_id == message_id)
        )
        return result.scalar_one_or_none()

    async def list_messages(
        self,
        source_chain: Optional[str] = None,
        destination_chain: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[CrossChainMessage], int]:
        """List messages with optional filters."""
        query = select(CrossChainMessage)
        count_query = select(func.count(CrossChainMessage.message_id))

        if source_chain:
            query = query.where(CrossChainMessage.source_chain == source_chain)
            count_query = count_query.where(CrossChainMessage.source_chain == source_chain)

        if destination_chain:
            query = query.where(CrossChainMessage.destination_chain == destination_chain)
            count_query = count_query.where(
                CrossChainMessage.destination_chain == destination_chain
            )

        if status:
            try:
                status_enum = MessageStatus(status)
                query = query.where(CrossChainMessage.status == status_enum)
                count_query = count_query.where(CrossChainMessage.status == status_enum)
            except ValueError:
                pass

        query = query.order_by(CrossChainMessage.created_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(query)
        messages = result.scalars().all()

        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        return list(messages), total
