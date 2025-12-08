"""Bridge Relayer Service - Monitors and relays cross-chain bridge messages."""

import logging
from contextlib import asynccontextmanager

from app.routes import health, messages, transfers
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("🚀 Bridge Relayer Service starting up")

    # Initialize bridge monitor (non-blocking)
    try:
        from app.core.bridge_monitor import BridgeMonitor

        monitor = BridgeMonitor()
        await monitor.start()
        app.state.bridge_monitor = monitor
        logger.info("✅ Bridge monitor started")
    except Exception as e:
        logger.warning(f"⚠️  Bridge monitor not started: {e}")
        app.state.bridge_monitor = None

    logger.info("✅ Bridge Relayer Service ready")

    yield

    # Cleanup
    if hasattr(app.state, "bridge_monitor") and app.state.bridge_monitor:
        await app.state.bridge_monitor.stop()
    logger.info("🛑 Bridge Relayer Service shutting down")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Bridge Relayer Service",
        description="Monitors and relays cross-chain bridge messages, native transfers, and ERC20 transfers",
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
    app.include_router(transfers.router, prefix="/api/v1/transfers", tags=["transfers"])

    return app


app = create_app()
