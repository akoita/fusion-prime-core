"""
Compliance Service - Team B: Compliance & Identity

Main FastAPI application for compliance, KYC/KYB, and AML monitoring.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict

from app.dependencies import get_compliance_engine, get_identity_service
from app.middleware import configure_observability, get_logger
from app.routes import compliance, health, identity, webhooks
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = get_logger(__name__, service="compliance-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Compliance Service starting up")

    # Initialize compliance engine
    try:
        compliance_engine = get_compliance_engine()
        logger.info("Starting compliance engine initialization...")
        await compliance_engine.initialize()
        app.state.compliance_engine = compliance_engine
        logger.info("✅ Compliance engine initialized successfully")
    except Exception as e:
        logger.error(
            f"❌ Failed to initialize compliance engine: {e}",
            exc_info=True,  # Include full traceback
        )
        app.state.compliance_engine = None

    # Initialize identity service
    try:
        identity_service = get_identity_service()
        logger.info("Starting identity service initialization...")
        await identity_service.initialize()
        app.state.identity_service = identity_service
        logger.info("✅ Identity service initialized successfully")
    except Exception as e:
        logger.error(
            f"❌ Failed to initialize identity service: {e}",
            exc_info=True,  # Include full traceback
        )
        app.state.identity_service = None

    logger.info("Compliance Service ready")

    try:
        yield
    finally:
        logger.info("Compliance Service shutting down")
        try:
            if hasattr(app.state, "compliance_engine") and app.state.compliance_engine:
                await app.state.compliance_engine.cleanup()
        except Exception as e:
            logger.warning(f"Error cleaning up compliance engine: {e}")

        try:
            if hasattr(app.state, "identity_service") and app.state.identity_service:
                await app.state.identity_service.cleanup()
        except Exception as e:
            logger.warning(f"Error cleaning up identity service: {e}")


# Create FastAPI application
app = FastAPI(
    title="Fusion Prime Compliance Service",
    description="Compliance, KYC/KYB, and AML monitoring service",
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
configure_observability(app, service_name="compliance-service")

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(compliance.router, prefix="/compliance", tags=["compliance"])
app.include_router(identity.router, prefix="/identity", tags=["identity"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Compliance Service",
        "version": "0.1.0",
        "status": "operational",
        "team": "Team B: Compliance & Identity",
    }


if __name__ == "__main__":
    import uvicorn

    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "info")

    logger.info(f"Starting Compliance Service on {host}:{port}")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=os.getenv("ENVIRONMENT") == "development",
    )
