"""Fiat Gateway Service - Handles fiat on/off-ramps via Circle and Stripe."""

import logging
from contextlib import asynccontextmanager

from app.routes import health, payments, transactions, webhooks
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from infrastructure.db.session import get_session

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("🚀 Fiat Gateway Service starting up")

    # Initialize database connections (non-blocking)
    # Don't fail startup if DB isn't ready - service can still serve health checks
    try:
        # Test database connection
        async with get_session() as session:
            logger.info("✅ Database connection established")
    except Exception as e:
        logger.warning(f"⚠️  Database connection issue (non-blocking): {e}")
        logger.info(
            "Service will continue - database operations may fail until connection is established"
        )

    logger.info("✅ Fiat Gateway Service ready")

    yield

    logger.info("🛑 Fiat Gateway Service shutting down")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Fiat Gateway Service",
        description="Handles fiat on/off-ramps via Circle USDC and Stripe",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
    app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["transactions"])
    app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "fiat-gateway"}

    return app


app = create_app()
