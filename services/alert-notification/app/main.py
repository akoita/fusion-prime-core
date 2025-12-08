"""
Alert Notification Service - Team B: Compliance & Identity (extended)

Main FastAPI application for consuming margin alerts and sending notifications
via email (SendGrid), SMS (Twilio), and webhook callbacks.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict

from app.consumer.alert_consumer import AlertEventConsumer, create_alert_handler
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Alert Notification Service starting up")

    # Initialize notification manager with database connection
    # Support multiple environment variable names for dev/test environments:
    # - DATABASE_URL (used in production/cloud deployments)
    # - RISK_DATABASE_URL (used in .env.dev for test environments)
    # - RISK_ENGINE_DATABASE_URL (backwards compatibility)
    try:
        from app.core.notification_manager import NotificationManager

        # Get database URL with fallback for dev/test environments
        database_url = (
            os.getenv("DATABASE_URL")
            or os.getenv("RISK_DATABASE_URL")
            or os.getenv("RISK_ENGINE_DATABASE_URL")
            or ""
        )

        # Log which environment variable was used (for debugging)
        if os.getenv("DATABASE_URL"):
            db_source = "DATABASE_URL"
        elif os.getenv("RISK_DATABASE_URL"):
            db_source = "RISK_DATABASE_URL"
        elif os.getenv("RISK_ENGINE_DATABASE_URL"):
            db_source = "RISK_ENGINE_DATABASE_URL"
        else:
            db_source = "none (database persistence disabled)"

        if database_url:
            logger.info(f"Database URL found from {db_source}, notification persistence enabled")
        else:
            logger.warning(
                f"No database URL configured ({db_source}), notification persistence will be disabled"
            )

        notification_manager = NotificationManager(
            database_url=database_url,
            sendgrid_api_key=os.getenv("SENDGRID_API_KEY", ""),
            twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
            twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
        )
        # Note: Don't call initialize() as it starts the old polling consumer
        # We're using the new streaming consumer instead
        app.state.notification_manager = notification_manager
        logger.info("Notification manager initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize notification manager: {e}")
        app.state.notification_manager = None

    # Initialize Pub/Sub consumer for margin alerts
    project_id = os.environ.get("GCP_PROJECT", "fusion-prime")
    subscription_id = os.environ.get("ALERT_SUBSCRIPTION", "alert-notification-service")

    logger.info(
        "Initializing Pub/Sub consumer for margin alerts",
        extra={"project_id": project_id, "subscription_id": subscription_id},
    )

    # Get event loop
    event_loop = asyncio.get_event_loop()

    # Create alert handler that uses notification manager (pass event loop)
    alert_handler = create_alert_handler(notification_manager, loop=event_loop)

    # Create and start consumer
    consumer = AlertEventConsumer(
        project_id,
        subscription_id,
        alert_handler,
        loop=event_loop,
    )
    future = consumer.start()
    app.state.consumer_future = future

    logger.info("Alert Notification Service ready")

    try:
        yield
    finally:
        logger.info("Alert Notification Service shutting down")
        try:
            if hasattr(app.state, "consumer_future"):
                app.state.consumer_future.cancel()
                logger.info("Pub/Sub consumer stopped")
        except Exception as e:
            logger.warning(f"Error stopping Pub/Sub consumer: {e}")

        try:
            if hasattr(app.state, "notification_manager") and app.state.notification_manager:
                await app.state.notification_manager.cleanup()
        except Exception as e:
            logger.warning(f"Error cleaning up notification manager: {e}")


# Create FastAPI application
app = FastAPI(
    title="Fusion Prime Alert Notification Service",
    description="Consumes margin alerts and sends notifications via email/SMS/webhook",
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

# Import routes
from app.routes import health, notifications

# Register routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])


# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {"service": "alert-notification", "version": "0.1.0", "status": "operational"}
