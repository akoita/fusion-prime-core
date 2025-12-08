"""Command service for ingest and status handling."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from domain.commands import SettlementCommand
from infrastructure.db.models import SettlementCommandRecord
from infrastructure.db.repository import get_command, upsert_command
from sqlalchemy.ext.asyncio import AsyncSession


async def ingest_command(session: AsyncSession, payload: dict[str, Any]) -> SettlementCommandRecord:
    command = SettlementCommand(
        command_id=str(payload["command_id"]),
        workflow_id=str(payload.get("workflow_id", "")),
        account_ref=str(payload.get("account_ref", "")),
        asset_symbol=str(payload.get("asset_symbol", "")),
        amount=str(payload.get("amount", "0")),
        deadline=datetime.now(UTC),
        command_type="DVP",
    )

    record = SettlementCommandRecord(
        command_id=command.command_id,
        workflow_id=command.workflow_id,
        account_ref=command.account_ref,
        asset_symbol=command.asset_symbol,
        amount_numeric=Decimal(command.amount),
        status="RECEIVED",
    )
    await upsert_command(session, record)
    return record


async def fetch_command_status(
    session: AsyncSession, command_id: str
) -> SettlementCommandRecord | None:
    return await get_command(session, command_id)
