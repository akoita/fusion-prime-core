"""Cross-chain message routes."""

import logging
from typing import List, Optional

from app.services.message_service import MessageService
from fastapi import APIRouter, Depends, HTTPException, Query
from infrastructure.db.models import MessageStatus
from infrastructure.db.session import get_session
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


class CrossChainMessage(BaseModel):
    """Cross-chain message model."""

    message_id: str
    source_chain: str
    destination_chain: str
    source_address: str
    destination_address: str
    payload: dict
    status: str
    protocol: str  # "axelar" or "ccip"
    transaction_hash: Optional[str] = None
    block_number: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None


@router.get("/", response_model=List[CrossChainMessage])
async def list_messages(
    source_chain: Optional[str] = Query(None),
    destination_chain: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """List cross-chain messages with filters."""
    message_service = MessageService(session)
    messages, total = await message_service.list_messages(
        source_chain=source_chain,
        destination_chain=destination_chain,
        status=status,
        limit=limit,
        offset=offset,
    )

    return [
        {
            "message_id": m.message_id,
            "source_chain": m.source_chain,
            "destination_chain": m.destination_chain,
            "source_address": m.source_address,
            "destination_address": m.destination_address,
            "payload": m.payload if isinstance(m.payload, dict) else {},
            "status": m.status.value,
            "protocol": m.protocol.value,
            "transaction_hash": m.transaction_hash,
            "block_number": m.block_number,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
            "completed_at": m.completed_at.isoformat() if m.completed_at else None,
        }
        for m in messages
    ]


@router.get("/{message_id}", response_model=CrossChainMessage)
async def get_message(message_id: str, session: AsyncSession = Depends(get_session)):
    """Get cross-chain message details."""
    message_service = MessageService(session)
    message = await message_service.get_message(message_id)

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    return {
        "message_id": message.message_id,
        "source_chain": message.source_chain,
        "destination_chain": message.destination_chain,
        "source_address": message.source_address,
        "destination_address": message.destination_address,
        "payload": message.payload if isinstance(message.payload, dict) else {},
        "status": message.status.value,
        "protocol": message.protocol.value,
        "transaction_hash": message.transaction_hash,
        "block_number": message.block_number,
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "updated_at": message.updated_at.isoformat() if message.updated_at else None,
        "completed_at": message.completed_at.isoformat() if message.completed_at else None,
    }


@router.post("/{message_id}/retry")
async def retry_message(message_id: str, session: AsyncSession = Depends(get_session)):
    """Retry a failed cross-chain message."""
    from app.core.retry_coordinator import RetryCoordinator

    message_service = MessageService(session)
    message = await message_service.get_message(message_id)

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if message.status != MessageStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail=f"Message is not in failed status (current: {message.status.value})",
        )

    if message.retry_count >= message.max_retries:
        raise HTTPException(
            status_code=400, detail=f"Message has exceeded max retries ({message.max_retries})"
        )

    # Use retry coordinator
    retry_coordinator = RetryCoordinator(session)
    success = await retry_coordinator.retry_message(message)

    if success:
        return {
            "message_id": message_id,
            "status": "retry_initiated",
            "retry_count": message.retry_count,
            "max_retries": message.max_retries,
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to initiate retry")
