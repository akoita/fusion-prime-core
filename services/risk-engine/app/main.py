"""
Risk Engine Service - Team A: Risk & Analytics

Main FastAPI application for risk calculation and portfolio analytics.
"""

import asyncio
import logging
import os

# Configure root logger for all modules
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict

from app.dependencies import get_analytics_engine, get_risk_calculator
from app.infrastructure.consumers import (
    PriceEventConsumer,
    RiskEventConsumer,
    create_price_cache_handler,
    escrow_event_handler,
)
from app.middleware import configure_observability, get_logger
from app.routes import analytics, health, margin, risk
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
if not root_logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
    root_logger.addHandler(handler)

logger = get_logger(__name__, service="risk-engine")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Risk Engine Service starting up")

    # Initialize database tables
    try:
        from app.dependencies import get_engine
        from infrastructure.db.models import Base

        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")

    # Initialize risk calculator
    try:
        risk_calculator = get_risk_calculator()
        await risk_calculator.initialize()
        app.state.risk_calculator = risk_calculator
        logger.info("Risk calculator initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize risk calculator: {e}")
        app.state.risk_calculator = None

    # Initialize analytics engine
    try:
        analytics_engine = get_analytics_engine()
        await analytics_engine.initialize()
        app.state.analytics_engine = analytics_engine
        logger.info("Analytics engine initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize analytics engine: {e}")
        app.state.analytics_engine = None

    # Initialize Pub/Sub consumer for escrow events
    project_id = os.environ.get("GCP_PROJECT", "local-project")
    subscription_id = os.environ.get("RISK_SUBSCRIPTION", "risk-events-consumer")

    logger.info(
        "Initializing Pub/Sub consumer for escrow events",
        extra={"project_id": project_id, "subscription_id": subscription_id},
    )

    # Get session factory for database persistence
    from app.dependencies import get_session_factory

    session_factory = get_session_factory()
    event_loop = asyncio.get_event_loop()

    consumer = RiskEventConsumer(
        project_id,
        subscription_id,
        escrow_event_handler,
        session_factory=session_factory,
        loop=event_loop,
    )
    future = consumer.start()
    app.state.consumer_future = future

    # Initialize Pub/Sub consumer for price updates
    price_subscription_id = os.environ.get("PRICE_SUBSCRIPTION", "risk-engine-prices-consumer")

    logger.info(
        "Initializing Pub/Sub consumer for price updates",
        extra={"project_id": project_id, "subscription_id": price_subscription_id},
    )

    # Create price cache handler using price oracle client
    if hasattr(app.state, "risk_calculator") and app.state.risk_calculator:
        price_oracle_client = getattr(app.state.risk_calculator, "price_oracle_client", None)

        if price_oracle_client:
            price_cache_handler = create_price_cache_handler(price_oracle_client, loop=event_loop)

            price_consumer = PriceEventConsumer(
                project_id,
                price_subscription_id,
                price_cache_handler,
                loop=event_loop,
            )
            price_future = price_consumer.start()
            app.state.price_consumer_future = price_future
            logger.info("Price event consumer started successfully")
        else:
            logger.warning(
                "Price oracle client not available, skipping price consumer initialization"
            )
    else:
        logger.warning("Risk calculator not available, skipping price consumer initialization")

    logger.info("Risk Engine Service ready")

    try:
        yield
    finally:
        logger.info("Risk Engine Service shutting down")
        try:
            if hasattr(app.state, "consumer_future"):
                app.state.consumer_future.cancel()
                logger.info("Escrow event consumer stopped")
        except Exception as e:
            logger.warning(f"Error stopping escrow event consumer: {e}")

        try:
            if hasattr(app.state, "price_consumer_future"):
                app.state.price_consumer_future.cancel()
                logger.info("Price event consumer stopped")
        except Exception as e:
            logger.warning(f"Error stopping price event consumer: {e}")

        try:
            if hasattr(app.state, "risk_calculator") and app.state.risk_calculator:
                await app.state.risk_calculator.cleanup()
        except Exception as e:
            logger.warning(f"Error cleaning up risk calculator: {e}")

        try:
            if hasattr(app.state, "analytics_engine") and app.state.analytics_engine:
                await app.state.analytics_engine.cleanup()
        except Exception as e:
            logger.warning(f"Error cleaning up analytics engine: {e}")


# Create FastAPI application
app = FastAPI(
    title="Fusion Prime Risk Engine",
    description="Risk calculation and portfolio analytics service",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure observability
configure_observability(app, service_name="risk-engine")

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(risk.router, prefix="/risk", tags=["risk"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(margin.router, prefix="/api/v1/margin", tags=["margin"])


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Risk Engine",
        "version": "0.1.0",
        "status": "operational",
        "team": "Team A: Risk & Analytics",
    }


if __name__ == "__main__":
    import uvicorn

    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "info")

    logger.info(f"Starting Risk Engine Service on {host}:{port}")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=os.getenv("ENVIRONMENT") == "development",
    )
