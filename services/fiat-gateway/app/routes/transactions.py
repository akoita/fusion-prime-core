"""Transaction history and management routes."""

import logging
from typing import Optional

from app.services.transaction_service import TransactionService
from fastapi import APIRouter, Depends, HTTPException, Query
from infrastructure.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def list_transactions(
    user_id: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """List transactions for a user."""
    transaction_service = TransactionService(session)
    transactions, total = await transaction_service.list_transactions(
        user_id=user_id, limit=limit, offset=offset
    )

    return {
        "transactions": [
            {
                "transaction_id": t.transaction_id,
                "user_id": t.user_id,
                "type": t.type.value,
                "amount": float(t.amount),
                "currency": t.currency,
                "status": t.status.value,
                "provider": t.provider.value,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in transactions
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{transaction_id}")
async def get_transaction(transaction_id: str, session: AsyncSession = Depends(get_session)):
    """Get transaction details."""
    transaction_service = TransactionService(session)
    transaction = await transaction_service.get_transaction(transaction_id)

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {
        "transaction_id": transaction.transaction_id,
        "user_id": transaction.user_id,
        "type": transaction.type.value,
        "amount": float(transaction.amount),
        "currency": transaction.currency,
        "status": transaction.status.value,
        "provider": transaction.provider.value,
        "destination_address": transaction.destination_address,
        "source_address": transaction.source_address,
        "destination_account": transaction.destination_account,
        "payment_url": transaction.payment_url,
        "provider_transaction_id": transaction.provider_transaction_id,
        "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
        "updated_at": transaction.updated_at.isoformat() if transaction.updated_at else None,
        "completed_at": transaction.completed_at.isoformat() if transaction.completed_at else None,
    }
