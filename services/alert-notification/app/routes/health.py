"""
Health endpoints for Alert Notification Service.
"""

from datetime import datetime
from typing import Dict

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: str
    version: str
    services: Dict[str, str]


@router.get("/")
async def health():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "0.1.0",
    }


@router.get("/detailed")
async def detailed_health():
    """Detailed health check with service status."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "0.1.0",
        "services": {
            "notification_manager": "operational",
            "pubsub_subscriber": "operational",
            "database": "operational",
        },
    }


@router.get("/live")
async def liveness():
    """Liveness probe."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness():
    """Readiness probe."""
    return {"status": "ready"}
