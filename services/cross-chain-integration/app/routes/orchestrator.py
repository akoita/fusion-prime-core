"""Settlement orchestrator routes for cross-chain operations."""

import logging
from typing import List, Optional

from app.services.orchestrator_service import OrchestratorService
from fastapi import APIRouter, Depends, HTTPException
from infrastructure.db.session import get_session
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


class CollateralSnapshot(BaseModel):
    """Collateral snapshot across chains."""

    user_id: str
    total_collateral_usd: float
    chains: dict  # {chain: {asset: amount, ...}}


class CrossChainSettlementRequest(BaseModel):
    """Request for cross-chain settlement."""

    source_chain: str
    destination_chain: str
    amount: float
    asset: str
    source_address: str
    destination_address: str
    preferred_protocol: Optional[str] = None  # "axelar" or "ccip"


@router.post("/settlement", response_model=dict)
async def initiate_settlement(
    request: CrossChainSettlementRequest, session: AsyncSession = Depends(get_session)
):
    """Initiate cross-chain settlement."""
    orchestrator_service = OrchestratorService(session)

    try:
        result = await orchestrator_service.initiate_settlement(
            source_chain=request.source_chain,
            destination_chain=request.destination_chain,
            amount=request.amount,
            asset=request.asset,
            source_address=request.source_address,
            destination_address=request.destination_address,
            preferred_protocol=request.preferred_protocol,
        )
        return result
    except Exception as e:
        logger.error(f"Failed to initiate settlement: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collateral/{user_id}", response_model=CollateralSnapshot)
async def get_collateral_snapshot(user_id: str, session: AsyncSession = Depends(get_session)):
    """Get aggregated collateral snapshot across all chains."""
    orchestrator_service = OrchestratorService(session)

    try:
        snapshot = await orchestrator_service.get_collateral_snapshot(user_id)
        return snapshot
    except Exception as e:
        logger.error(f"Failed to get collateral snapshot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{settlement_id}")
async def get_settlement_status(settlement_id: str, session: AsyncSession = Depends(get_session)):
    """Get cross-chain settlement status."""
    orchestrator_service = OrchestratorService(session)

    try:
        status = await orchestrator_service.get_settlement_status(settlement_id)
        return status
    except Exception as e:
        logger.error(f"Failed to get settlement status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
