from typing import Any

from app.dependencies import get_session
from app.services.commands import ingest_command
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/commands", tags=["commands"])


class IngestCommandRequest(BaseModel):
    """Request model for command ingestion with validation."""

    command_id: str = Field(..., min_length=1, description="Unique command identifier")
    workflow_id: str = Field(default="", description="Workflow identifier")
    account_ref: str = Field(default="", description="Account reference")
    asset_symbol: str = Field(default="", description="Asset symbol")
    amount: str = Field(..., description="Amount as string")
    payer: str = Field(default="", description="Payer address")
    payee: str = Field(default="", description="Payee address")
    chain_id: int = Field(default=0, description="Blockchain chain ID")

    @field_validator("command_id")
    @classmethod
    def validate_command_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("command_id must not be empty")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: str) -> str:
        try:
            float_val = float(v)
            if float_val < 0:
                raise ValueError("amount must be non-negative")
        except (ValueError, TypeError):
            raise ValueError("amount must be a valid number")
        return v


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_command_endpoint(
    payload: IngestCommandRequest, session: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    record = await ingest_command(session, payload.model_dump())
    return {"status": "accepted", "command_id": record.command_id}
