"""Repository functions for escrow records in risk_db."""

from __future__ import annotations

from typing import List, Optional

from infrastructure.db.models import EscrowRecord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def upsert_escrow(session: AsyncSession, record: EscrowRecord) -> None:
    """Insert or update an escrow record in risk_db."""
    existing = await session.get(EscrowRecord, record.address)
    if existing:
        # Update existing record
        existing.payer = record.payer
        existing.payee = record.payee
        existing.amount = record.amount
        existing.amount_numeric = record.amount_numeric
        existing.asset_symbol = record.asset_symbol
        existing.chain_id = record.chain_id
        existing.status = record.status
        existing.release_delay = record.release_delay
        existing.approvals_required = record.approvals_required
        existing.approvals_count = record.approvals_count
        existing.arbiter = record.arbiter
        existing.transaction_hash = record.transaction_hash
        existing.block_number = record.block_number
    else:
        session.add(record)
    await session.commit()


async def get_escrow(session: AsyncSession, address: str) -> Optional[EscrowRecord]:
    """Get an escrow by address."""
    result = await session.execute(select(EscrowRecord).where(EscrowRecord.address == address))
    return result.scalar_one_or_none()


async def get_escrows_by_payer(session: AsyncSession, payer: str) -> List[EscrowRecord]:
    """Get all escrows for a specific payer."""
    result = await session.execute(select(EscrowRecord).where(EscrowRecord.payer == payer))
    return list(result.scalars().all())


async def get_escrows_by_payee(session: AsyncSession, payee: str) -> List[EscrowRecord]:
    """Get all escrows for a specific payee."""
    result = await session.execute(select(EscrowRecord).where(EscrowRecord.payee == payee))
    return list(result.scalars().all())


async def update_escrow_status(
    session: AsyncSession, address: str, status: str, approvals_count: Optional[int] = None
) -> bool:
    """Update the status of an escrow."""
    escrow = await get_escrow(session, address)
    if not escrow:
        return False

    escrow.status = status
    if approvals_count is not None:
        escrow.approvals_count = approvals_count

    await session.commit()
    return True


async def increment_escrow_approvals(session: AsyncSession, address: str) -> Optional[EscrowRecord]:
    """Increment the approval count for an escrow."""
    escrow = await get_escrow(session, address)
    if not escrow:
        return None

    escrow.approvals_count = (escrow.approvals_count or 0) + 1

    # Auto-update status if approvals threshold is met
    if escrow.approvals_required and escrow.approvals_count >= escrow.approvals_required:
        escrow.status = "approved"

    await session.commit()
    return escrow
