"""
Health check endpoint for price oracle service.
"""

import logging
from datetime import datetime

from app.core.price_oracle_client import PriceOracleClient
from app.models.price import HealthResponse
from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


def get_price_oracle() -> PriceOracleClient:
    """Dependency injection for price oracle client."""
    from app.main import price_oracle_client

    return price_oracle_client


@router.get("/health", response_model=HealthResponse)
async def health_check(oracle: PriceOracleClient = Depends(get_price_oracle)):
    """
    Health check endpoint.

    Checks:
    - Service is running
    - Can fetch at least one price (ETH)
    - Pub/Sub publisher is initialized

    Returns:
        Health status with component checks
    """
    components = {}
    overall_status = "healthy"

    # Check price oracle
    try:
        # Try to fetch ETH price as canary
        await oracle.get_price("ETH")
        components["price_oracle"] = "healthy"
    except Exception as e:
        logger.error(f"Price oracle health check failed: {e}")
        components["price_oracle"] = "unhealthy"
        overall_status = "degraded"

    # Check Pub/Sub publisher
    try:
        from app.main import price_publisher

        if price_publisher:
            components["pubsub_publisher"] = "healthy"
        else:
            components["pubsub_publisher"] = "not_initialized"
            overall_status = "degraded"
    except Exception as e:
        logger.error(f"Pub/Sub publisher health check failed: {e}")
        components["pubsub_publisher"] = "unhealthy"
        overall_status = "degraded"

    # Check cache
    try:
        cache_size = len(oracle.cache)
        components["cache"] = f"healthy (size: {cache_size})"
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        components["cache"] = "unhealthy"

    return HealthResponse(
        status=overall_status, timestamp=datetime.utcnow(), version="1.0.0", components=components
    )


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness probe for Kubernetes/Cloud Run.

    Simple check that service can accept requests.
    """
    return {"status": "ready", "timestamp": datetime.utcnow().isoformat() + "Z"}


@router.get("/health/live")
async def liveness_check():
    """
    Liveness probe for Kubernetes/Cloud Run.

    Simple check that service is alive.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat() + "Z"}
