from app.dependencies import get_session
from app.services.commands import fetch_command_status
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/commands", tags=["commands"])


@router.get("/{command_id}")
async def get_command_status(
    command_id: str, session: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    record = await fetch_command_status(session, command_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Command not found")
    return {"command_id": record.command_id, "status": record.status}
