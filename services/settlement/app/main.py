import os
from contextlib import asynccontextmanager

from app.middleware import configure_observability, get_logger
from app.routes import commands, escrows, health, status, webhooks
from fastapi import FastAPI
from infrastructure.consumers.pubsub_consumer import (
    SettlementEventConsumer,
    settlement_event_handler,
)

logger = get_logger(__name__, service="settlement-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Settlement service starting up")

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
        # Don't fail startup for database issues - let the service start and handle errors gracefully

    project_id = os.environ.get("GCP_PROJECT", "local-project")
    subscription_id = os.environ.get("SETTLEMENT_SUBSCRIPTION", "settlement-events-consumer")

    logger.info(
        "Initializing Pub/Sub consumer",
        extra={"project_id": project_id, "subscription_id": subscription_id},
    )

    # Get session factory for database persistence
    import asyncio

    from app.dependencies import get_session_factory

    session_factory = get_session_factory()
    event_loop = asyncio.get_event_loop()

    consumer = SettlementEventConsumer(
        project_id,
        subscription_id,
        settlement_event_handler,
        session_factory=session_factory,
        loop=event_loop,
    )
    future = consumer.start()
    app.state.consumer_future = future

    logger.info("Settlement service ready")

    try:
        yield
    finally:
        logger.info("Settlement service shutting down")
        future.cancel()
        logger.info("Settlement service stopped")


app = FastAPI(
    title="Fusion Prime Settlement Service",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure observability (must be done before including routers)
configure_observability(app, service_name="settlement-service")

# Include routers
app.include_router(health.router)
app.include_router(commands.router)
app.include_router(escrows.router)
app.include_router(status.router)
app.include_router(webhooks.router)

logger.info("Settlement service initialized")
