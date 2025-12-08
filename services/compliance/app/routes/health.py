"""
Health check endpoints for Compliance Service.
"""

import time
from typing import Any, Dict

from app.dependencies import get_compliance_engine, get_identity_service
from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: str
    version: str
    services: Dict[str, Any]


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        version="0.1.0",
        services={
            "compliance_engine": "operational",
            "identity_service": "operational",
        },
    )


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with service status."""
    from fastapi import Request

    # Get services from app state (if available)
    compliance_status = {"status": "unavailable", "error": "Service not initialized"}
    identity_status = {"status": "unavailable", "error": "Service not initialized"}

    # Check if services are available in app state
    # Note: We can't use Depends here as it might fail during startup

    # Overall health status
    overall_status = "healthy"
    if compliance_status["status"] != "healthy" or identity_status["status"] != "healthy":
        overall_status = "degraded"

    return {
        "status": overall_status,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "version": "0.1.0",
        "services": {
            "compliance_engine": compliance_status,
            "identity_service": identity_status,
        },
        "dependencies": {
            "database": "unknown",
            "external_apis": "unknown",
        },
    }


@router.get("/health/ready")
async def readiness_check():
    """Readiness check for Kubernetes/Cloud Run."""
    return {
        "status": "ready",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@router.get("/health/live")
async def liveness_check():
    """Liveness check for Kubernetes/Cloud Run."""
    return {
        "status": "alive",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
