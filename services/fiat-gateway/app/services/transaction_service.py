"""Transaction service for managing fiat transactions."""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from infrastructure.db.models import (
    FiatTransaction,
    PaymentProvider,
    TransactionStatus,
    TransactionType,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TransactionService:
    """Service for managing fiat transactions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_transaction(
        self,
        user_id: str,
        transaction_type: TransactionType,
        amount: float,
        currency: str,
        provider: PaymentProvider,
        destination_address: Optional[str] = None,
        source_address: Optional[str] = None,
        destination_account: Optional[str] = None,
        payment_url: Optional[str] = None,
    ) -> FiatTransaction:
        """Create a new fiat transaction record."""
        transaction_id = f"{transaction_type.value}-{uuid.uuid4().hex[:16]}"

        transaction = FiatTransaction(
            transaction_id=transaction_id,
            user_id=user_id,
            type=transaction_type,
            amount=amount,
            currency=currency,
            provider=provider,
            status=TransactionStatus.PENDING,
            destination_address=destination_address,
            source_address=source_address,
            destination_account=destination_account,
            payment_url=payment_url,
        )

        self.session.add(transaction)
        await self.session.commit()
        await self.session.refresh(transaction)

        logger.info(f"Created transaction: {transaction_id} for user {user_id}")
        return transaction

    async def update_transaction(
        self,
        transaction_id: str,
        status: Optional[TransactionStatus] = None,
        provider_transaction_id: Optional[str] = None,
        provider_response: Optional[str] = None,
    ) -> Optional[FiatTransaction]:
        """Update transaction status and provider information."""
        result = await self.session.execute(
            select(FiatTransaction).where(FiatTransaction.transaction_id == transaction_id)
        )
        transaction = result.scalar_one_or_none()

        if not transaction:
            logger.warning(f"Transaction not found: {transaction_id}")
            return None

        if status:
            transaction.status = status
            if status == TransactionStatus.COMPLETED:
                transaction.completed_at = datetime.utcnow()

        if provider_transaction_id:
            transaction.provider_transaction_id = provider_transaction_id

        if provider_response:
            transaction.provider_response = provider_response

        transaction.updated_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(transaction)

        logger.info(f"Updated transaction: {transaction_id} to status {status}")
        return transaction

    async def get_transaction(self, transaction_id: str) -> Optional[FiatTransaction]:
        """Get transaction by ID."""
        result = await self.session.execute(
            select(FiatTransaction).where(FiatTransaction.transaction_id == transaction_id)
        )
        return result.scalar_one_or_none()

    async def list_transactions(
        self, user_id: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> tuple[List[FiatTransaction], int]:
        """List transactions with optional user filter."""
        query = select(FiatTransaction)

        if user_id:
            query = query.where(FiatTransaction.user_id == user_id)

        query = query.order_by(FiatTransaction.created_at.desc()).limit(limit).offset(offset)

        # Count total
        count_query = select(FiatTransaction)
        if user_id:
            count_query = count_query.where(FiatTransaction.user_id == user_id)

        result = await self.session.execute(query)
        transactions = result.scalars().all()

        count_result = await self.session.execute(select(count_query.alias().count()))
        total = count_result.scalar() or 0

        return list(transactions), total
