"""Transfer bridge routes."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class NativeTransferRequest(BaseModel):
    """Native transfer request."""

    dest_chain_id: int
    recipient: str
    amount: str  # Wei amount as string


class ERC20TransferRequest(BaseModel):
    """ERC20 transfer request."""

    dest_chain_id: int
    token: str
    recipient: str
    amount: str  # Token amount as string


class TransferResponse(BaseModel):
    """Transfer response."""

    transfer_id: str
    status: str


@router.post("/native", response_model=TransferResponse)
async def send_native_transfer(request: NativeTransferRequest):
    """Send a native currency transfer."""
    try:
        from app.core.bridge_client import BridgeClient

        client = BridgeClient()
        transfer_id = await client.send_native_transfer(
            dest_chain_id=request.dest_chain_id,
            recipient=request.recipient,
            amount=int(request.amount),
        )

        return TransferResponse(transfer_id=transfer_id, status="pending")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/erc20", response_model=TransferResponse)
async def send_erc20_transfer(request: ERC20TransferRequest):
    """Send an ERC20 token transfer."""
    try:
        from app.core.bridge_client import BridgeClient

        client = BridgeClient()
        transfer_id = await client.send_erc20_transfer(
            dest_chain_id=request.dest_chain_id,
            token=request.token,
            recipient=request.recipient,
            amount=int(request.amount),
        )

        return TransferResponse(transfer_id=transfer_id, status="pending")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/native/{transfer_id}")
async def get_native_transfer(transfer_id: str):
    """Get native transfer status."""
    try:
        from app.core.bridge_client import BridgeClient

        client = BridgeClient()
        transfer = await client.get_native_transfer(transfer_id)

        return transfer
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/erc20/{transfer_id}")
async def get_erc20_transfer(transfer_id: str):
    """Get ERC20 transfer status."""
    try:
        from app.core.bridge_client import BridgeClient

        client = BridgeClient()
        transfer = await client.get_erc20_transfer(transfer_id)

        return transfer
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
