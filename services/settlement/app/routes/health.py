from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def readiness() -> dict[str, str]:
    return {"status": "ok"}
