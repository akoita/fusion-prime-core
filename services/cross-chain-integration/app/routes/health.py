"""Health check endpoint for Cross-Chain Integration Service."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
@router.get("/")
async def health_check():
    """
    Health check endpoint.

    Returns basic service status without database dependency.
    Database health can be checked separately via /health/db.
    """
    return {
        "status": "healthy",
        "service": "cross-chain-integration-service",
    }


@router.get("/db")
async def database_health_check():
    """
    Database health check endpoint.

    Attempts to connect to the database to verify connectivity.
    """
    try:
        from infrastructure.db.session import get_session_factory

        session_factory = get_session_factory()
        async with session_factory() as session:
            # Simple query to verify connection
            await session.execute("SELECT 1")
            return {
                "status": "healthy",
                "database": "connected",
            }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
            },
        )
