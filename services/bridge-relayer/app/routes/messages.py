"""Message bridge routes."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class MessageRequest(BaseModel):
    """Message bridge request."""

    source_chain_id: int
    dest_chain_id: int
    sender: str
    recipient: str
    payload: str  # Hex encoded bytes


class MessageResponse(BaseModel):
    """Message bridge response."""

    message_id: str
    status: str


@router.post("/send", response_model=MessageResponse)
async def send_message(request: MessageRequest):
    """Send a cross-chain message."""
    try:
        from app.core.bridge_client import BridgeClient

        client = BridgeClient()
        message_id = await client.send_message(
            source_chain_id=request.source_chain_id,
            dest_chain_id=request.dest_chain_id,
            sender=request.sender,
            recipient=request.recipient,
            payload=bytes.fromhex(request.payload.removeprefix("0x")),
        )

        return MessageResponse(message_id=message_id, status="pending")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{message_id}")
async def get_message(message_id: str):
    """Get message status."""
    try:
        from app.core.bridge_client import BridgeClient

        client = BridgeClient()
        message = await client.get_message(message_id)

        return message
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
