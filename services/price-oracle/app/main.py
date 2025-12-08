"""
Price Oracle Service - Main FastAPI Application

Provides real-time and historical crypto price data with automatic publishing to Pub/Sub.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from app.core.price_oracle_client import PriceOracleClient
from app.routes import health, prices
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from infrastructure.pubsub.publisher import PricePublisher

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances (initialized in lifespan)
price_oracle_client: Optional[PriceOracleClient] = None
price_publisher: Optional[PricePublisher] = None
background_task: Optional[asyncio.Task] = None

# Configuration from environment
GCP_PROJECT = os.getenv("GCP_PROJECT", "fusion-prime")
ETH_RPC_URL = os.getenv("ETH_RPC_URL", "https://sepolia.gateway.tenderly.co/72gZoWFjAN7SQMDZ2D3llq")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")  # Optional
PRICE_CACHE_TTL = int(os.getenv("PRICE_CACHE_TTL", "60"))  # 60 seconds
PRICE_UPDATE_INTERVAL = int(os.getenv("PRICE_UPDATE_INTERVAL", "30"))  # 30 seconds
PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC", "market.prices.v1")

# Assets to track
TRACKED_ASSETS = ["ETH", "BTC", "USDC", "USDT"]


async def publish_prices_periodically():
    """
    Background task to fetch and publish prices periodically.

    Runs every PRICE_UPDATE_INTERVAL seconds and publishes to Pub/Sub.
    """
    global price_oracle_client, price_publisher

    logger.info(f"Starting periodic price publisher (interval: {PRICE_UPDATE_INTERVAL}s)")

    while True:
        try:
            # Fetch current prices for all tracked assets
            prices = await price_oracle_client.get_multiple_prices(
                TRACKED_ASSETS, force_refresh=True  # Always fetch fresh for publishing
            )

            logger.info(f"Fetched {len(prices)} prices: {prices}")

            # Publish to Pub/Sub
            await price_publisher.publish_multiple_prices(
                prices, source="chainlink", metadata=None  # Primary source
            )

            logger.info(f"Published {len(prices)} prices to Pub/Sub")

        except Exception as e:
            logger.error(f"Error in periodic price publisher: {e}")

        # Wait for next interval
        await asyncio.sleep(PRICE_UPDATE_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Initializes services on startup and cleans up on shutdown.
    """
    global price_oracle_client, price_publisher, background_task

    logger.info("Starting Price Oracle Service...")

    # Initialize price oracle client
    price_oracle_client = PriceOracleClient(
        eth_rpc_url=ETH_RPC_URL,
        coingecko_api_key=COINGECKO_API_KEY,
        cache_ttl=PRICE_CACHE_TTL,
        timeout=5.0,
    )

    logger.info(
        f"Price oracle client initialized (cache_ttl={PRICE_CACHE_TTL}s, "
        f"rpc_url={ETH_RPC_URL[:50]}...)"
    )

    # Initialize Pub/Sub publisher
    price_publisher = PricePublisher(project_id=GCP_PROJECT, topic_name=PUBSUB_TOPIC)

    logger.info(f"Pub/Sub publisher initialized (topic={PUBSUB_TOPIC})")

    # Start background price publishing task
    background_task = asyncio.create_task(publish_prices_periodically())

    logger.info("Price Oracle Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Price Oracle Service...")

    # Cancel background task
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass

    # Close clients
    if price_oracle_client:
        await price_oracle_client.close()

    if price_publisher:
        price_publisher.close()

    logger.info("Price Oracle Service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Fusion Prime - Price Oracle Service",
    description="Real-time and historical crypto price data with Pub/Sub integration",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(prices.router)
app.include_router(health.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "price-oracle",
        "version": "1.0.0",
        "status": "running",
        "tracked_assets": TRACKED_ASSETS,
        "update_interval_seconds": PRICE_UPDATE_INTERVAL,
        "cache_ttl_seconds": PRICE_CACHE_TTL,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
        reload=os.getenv("ENV", "production") == "development",
        log_level="info",
    )
