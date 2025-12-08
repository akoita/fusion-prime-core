"""
Identity Service - Main FastAPI application.

Handles identity creation and claim issuance on the blockchain.
"""

import logging
import os
from contextlib import asynccontextmanager

from app.config import settings
from app.routes import auth, identity
from app.services.identity_service import IdentityService
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from infrastructure.blockchain.web3_client import Web3Client
from infrastructure.db.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Identity Service starting up")

    # Initialize database
    try:
        logger.info("Initializing database...")
        await init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️  Database initialization failed (will continue without DB): {e}")

    # Initialize Web3 client
    try:
        logger.info("Initializing Web3 client...")
        web3_client = Web3Client(
            rpc_url=settings.rpc_url,
            private_key=settings.backend_private_key,
            chain_id=settings.chain_id,
            identity_factory_address=settings.identity_factory_address,
            claim_issuer_registry_address=settings.claim_issuer_registry_address,
        )

        if not web3_client.is_connected():
            logger.error("❌ Web3 client not connected")
            raise Exception("Failed to connect to blockchain")

        logger.info(
            f"✅ Web3 client connected: network={settings.blockchain_network}, "
            f"address={web3_client.address}"
        )

        # Initialize Identity Service
        identity_service = IdentityService(web3_client)
        app.state.identity_service = identity_service
        logger.info("✅ Identity service initialized successfully")

    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}", exc_info=True)
        app.state.identity_service = None

    logger.info("Identity Service ready")

    try:
        yield
    finally:
        logger.info("Identity Service shutting down")


# Create FastAPI application
app = FastAPI(
    title="Fusion Prime Identity Service",
    description="Identity and claim management service using ERC-734/735",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(identity.router, prefix="/identity", tags=["identity"])


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Identity Service",
        "version": "0.1.0",
        "status": "operational",
        "network": settings.blockchain_network,
        "chain_id": settings.chain_id,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    identity_service = getattr(app.state, "identity_service", None)

    if identity_service is None:
        return {"status": "unhealthy", "error": "Identity service not initialized"}

    # Check blockchain connection
    try:
        is_connected = identity_service.web3_client.is_connected()

        if not is_connected:
            return {
                "status": "unhealthy",
                "error": "Blockchain not connected",
                "network": settings.blockchain_network,
            }

        backend_balance = identity_service.web3_client.get_balance(
            identity_service.web3_client.address
        )

        return {
            "status": "healthy",
            "service": "identity-service",
            "network": settings.blockchain_network,
            "chain_id": settings.chain_id,
            "backend_address": identity_service.web3_client.address,
            "backend_balance_wei": backend_balance,
            "backend_balance_eth": float(backend_balance) / 1e18,
            "contracts": {
                "identity_factory": settings.identity_factory_address,
                "claim_issuer_registry": settings.claim_issuer_registry_address,
            },
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", settings.port))

    logger.info(f"Starting Identity Service on {host}:{port}")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level=settings.log_level.lower(),
        reload=settings.environment == "development",
    )
