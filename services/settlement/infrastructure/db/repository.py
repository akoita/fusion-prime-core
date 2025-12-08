"""Repository functions for settlement commands."""

from __future__ import annotations

from infrastructure.db.models import SettlementCommandRecord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def upsert_command(session: AsyncSession, record: SettlementCommandRecord) -> None:
    existing = await session.get(SettlementCommandRecord, record.command_id)
    if existing:
        existing.status = record.status
        existing.payer = record.payer
        existing.payee = record.payee
        existing.amount_numeric = record.amount_numeric
        existing.asset_symbol = record.asset_symbol
    else:
        session.add(record)
    await session.commit()


async def get_command(session: AsyncSession, command_id: str) -> SettlementCommandRecord | None:
    result = await session.execute(
        select(SettlementCommandRecord).where(SettlementCommandRecord.command_id == command_id)
    )
    return result.scalar_one_or_none()
