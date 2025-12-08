"""Escrow query endpoints for integration testing and monitoring."""

from decimal import Decimal
from typing import Optional

from app.dependencies import get_session
from fastapi import APIRouter, Depends, HTTPException, status
from infrastructure.db.escrow_repository import (
    get_escrow,
    get_escrows_by_payee,
    get_escrows_by_payer,
)
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/escrows", tags=["escrows"])


class EscrowResponse(BaseModel):
    """Response model for escrow data."""

    address: str
    payer: str
    payee: str
    amount: str
    asset_symbol: str
    chain_id: int
    status: str
    release_delay: Optional[int] = None
    approvals_required: Optional[int] = None
    approvals_count: int = 0
    arbiter: Optional[str] = None
    transaction_hash: Optional[str] = None
    block_number: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@router.get("/{address}", response_model=EscrowResponse, status_code=status.HTTP_200_OK)
async def get_escrow_endpoint(
    address: str, session: AsyncSession = Depends(get_session)
) -> EscrowResponse:
    """
    Get escrow details by contract address.

    This endpoint is used by integration tests to verify that the Settlement
    service has processed EscrowDeployed events from the blockchain and stored
    the escrow data in the database.

    Args:
        address: The escrow contract address (checksummed or lowercase)

    Returns:
        Escrow data including status, amounts, parties, and approval counts

    Raises:
        404: If the escrow is not found in the database
    """
    # Normalize address to lowercase for comparison
    address_lower = address.lower()

    escrow = await get_escrow(session, address_lower)
    if not escrow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Escrow {address} not found in database"
        )

    return EscrowResponse(
        address=escrow.address,
        payer=escrow.payer,
        payee=escrow.payee,
        amount=escrow.amount,
        asset_symbol=escrow.asset_symbol or "ETH",
        chain_id=escrow.chain_id,
        status=escrow.status,
        release_delay=escrow.release_delay,
        approvals_required=escrow.approvals_required,
        approvals_count=escrow.approvals_count or 0,
        arbiter=escrow.arbiter,
        transaction_hash=escrow.transaction_hash,
        block_number=escrow.block_number,
        created_at=escrow.created_at.isoformat() if escrow.created_at else None,
        updated_at=escrow.updated_at.isoformat() if escrow.updated_at else None,
    )


@router.get("/", response_model=list[EscrowResponse], status_code=status.HTTP_200_OK)
async def list_escrows_endpoint(
    payer: Optional[str] = None,
    payee: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
) -> list[EscrowResponse]:
    """
    List escrows with optional filtering.

    Args:
        payer: Filter by payer address
        payee: Filter by payee address

    Returns:
        List of escrows matching the filter criteria
    """
    if payer:
        escrows = await get_escrows_by_payer(session, payer.lower())
    elif payee:
        escrows = await get_escrows_by_payee(session, payee.lower())
    else:
        # If no filters, return empty list (avoid returning all escrows)
        return []

    return [
        EscrowResponse(
            address=e.address,
            payer=e.payer,
            payee=e.payee,
            amount=e.amount,
            asset_symbol=e.asset_symbol or "ETH",
            chain_id=e.chain_id,
            status=e.status,
            release_delay=e.release_delay,
            approvals_required=e.approvals_required,
            approvals_count=e.approvals_count or 0,
            arbiter=e.arbiter,
            transaction_hash=e.transaction_hash,
            block_number=e.block_number,
            created_at=e.created_at.isoformat() if e.created_at else None,
            updated_at=e.updated_at.isoformat() if e.updated_at else None,
        )
        for e in escrows
    ]
