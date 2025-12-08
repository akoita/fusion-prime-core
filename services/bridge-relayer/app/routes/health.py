"""Health check routes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "bridge-relayer"}


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {"status": "ready", "service": "bridge-relayer"}
