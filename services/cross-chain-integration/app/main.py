"""Cross-Chain Integration Service - Monitors and orchestrates cross-chain messages."""

import logging
from contextlib import asynccontextmanager

from app.routes import health, messages, orchestrator
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
    logger.info("🚀 Cross-Chain Integration Service starting up")

    # Initialize database connections (non-blocking)
    # Don't fail startup if DB isn't ready - service can still serve health checks
    try:
        from infrastructure.db.session import get_session_factory

        session_factory = get_session_factory()
        async with session_factory() as session:
            logger.info("✅ Database connection established")
    except Exception as e:
        logger.warning(f"⚠️  Database connection issue (non-blocking): {e}")
        logger.info(
            "Service will continue - database operations may fail until connection is established"
        )

    # Initialize message monitor (if configured) - non-blocking
    try:
        from app.core.message_monitor import MessageMonitor
        from infrastructure.db.session import get_session_factory

        session_factory = get_session_factory()
        monitor = MessageMonitor(session_factory=session_factory)
        await monitor.start()
        app.state.message_monitor = monitor
        logger.info("✅ Message monitor started")
    except Exception as e:
        logger.warning(f"⚠️  Message monitor not started: {e}")
        app.state.message_monitor = None

    logger.info("✅ Cross-Chain Integration Service ready")

    yield

    # Cleanup
    if hasattr(app.state, "message_monitor") and app.state.message_monitor:
        await app.state.message_monitor.stop()
    logger.info("🛑 Cross-Chain Integration Service shutting down")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Cross-Chain Integration Service",
        description="Monitors and orchestrates cross-chain messages via Axelar and CCIP",
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
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(messages.router, prefix="/api/v1/messages", tags=["messages"])
    app.include_router(orchestrator.router, prefix="/api/v1/orchestrator", tags=["orchestrator"])

    return app


app = create_app()
