"""
HTTP Service wrapper for the relayer to expose health and status endpoints
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from google.cloud import storage
from production_relayer import ProductionEventRelayer, RelayerConfig, RelayerMetrics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Escrow Event Relayer Service", version="1.0.0")

# Global relayer instance
relayer: ProductionEventRelayer = None
relayer_task = None

# Container restart tracking
RESTART_TRACKING_FILE = "/tmp/relayer_restarts.json"
container_start_time = datetime.now(timezone.utc)


def load_abi_from_gcs(gcs_url: str) -> list:
    """Load contract ABI from Google Cloud Storage URL"""
    try:
        # Parse GCS URL: gs://bucket/path/to/file.json
        if not gcs_url.startswith("gs://"):
            raise ValueError(f"Invalid GCS URL format: {gcs_url}")

        # Remove gs:// prefix
        path = gcs_url[5:]  # Remove "gs://"
        bucket_name, blob_name = path.split("/", 1)

        # Initialize GCS client
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # Download and parse JSON
        content = blob.download_as_text()
        abi_data = json.loads(content)

        # Extract ABI from the JSON structure
        if isinstance(abi_data, dict) and "abi" in abi_data:
            abi = abi_data["abi"]
        elif isinstance(abi_data, list):
            abi = abi_data
        else:
            raise ValueError(f"Unexpected ABI format in {gcs_url}")

        logger.info(f"Successfully loaded ABI from {gcs_url} ({len(abi)} items)")
        return abi

    except Exception as e:
        logger.error(f"Failed to load ABI from {gcs_url}: {e}")
        # Return minimal ABI as fallback
        return [
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "escrow", "type": "address"},
                    {"indexed": True, "name": "payer", "type": "address"},
                    {"indexed": True, "name": "payee", "type": "address"},
                    {"indexed": False, "name": "amount", "type": "uint256"},
                    {"indexed": False, "name": "releaseDelay", "type": "uint256"},
                    {"indexed": False, "name": "approvalsRequired", "type": "uint8"},
                ],
                "name": "EscrowDeployed",
                "type": "event",
            }
        ]


def track_container_restart():
    """Track container restarts by persisting restart history"""
    try:
        restart_data = {"restarts": [], "total_restarts": 0}

        # Load existing restart history
        if Path(RESTART_TRACKING_FILE).exists():
            with open(RESTART_TRACKING_FILE, "r") as f:
                restart_data = json.load(f)

        # Add new restart event
        restart_data["restarts"].append(
            {
                "timestamp": container_start_time.isoformat(),
                "restart_count": restart_data["total_restarts"] + 1,
            }
        )
        restart_data["total_restarts"] += 1

        # Keep only last 10 restarts
        restart_data["restarts"] = restart_data["restarts"][-10:]

        # Persist to file
        with open(RESTART_TRACKING_FILE, "w") as f:
            json.dump(restart_data, f)

        logger.info(
            f"Container restart #{restart_data['total_restarts']} tracked at {container_start_time.isoformat()}"
        )
        return restart_data

    except Exception as e:
        logger.warning(f"Failed to track container restart: {e}")
        return {"restarts": [], "total_restarts": 0}


def get_restart_metrics():
    """Get container restart metrics"""
    try:
        if Path(RESTART_TRACKING_FILE).exists():
            with open(RESTART_TRACKING_FILE, "r") as f:
                return json.load(f)
        return {"restarts": [], "total_restarts": 0}
    except Exception as e:
        logger.warning(f"Failed to load restart metrics: {e}")
        return {"restarts": [], "total_restarts": 0}


async def get_blockchain_lag(relayer: ProductionEventRelayer) -> Dict[str, Any]:
    """Calculate blockchain lag (blocks behind current chain height)"""
    try:
        # Get checkpoint
        checkpoint = await relayer.checkpoint_store.get_checkpoint(
            relayer.config.chain_id, relayer.config.contract_address
        )
        last_processed_block = (
            checkpoint.last_processed_block if checkpoint else relayer.config.start_block
        )

        # Get current blockchain height
        current_block = relayer.web3.eth.get_block("latest")["number"]

        # Calculate lag
        lag = current_block - last_processed_block

        return {
            "last_processed_block": last_processed_block,
            "current_blockchain_height": current_block,
            "blocks_behind": lag,
            "status": "critical" if lag > 100 else "healthy" if lag < 50 else "warning",
        }
    except Exception as e:
        logger.error(f"Failed to calculate blockchain lag: {e}")
        return {
            "last_processed_block": None,
            "current_blockchain_height": None,
            "blocks_behind": None,
            "status": "unknown",
            "error": str(e),
        }


@app.on_event("startup")
async def startup_event():
    """Initialize the relayer on startup"""
    global relayer, relayer_task

    # Track container restart
    restart_data = track_container_restart()
    logger.info(f"Container started (total restarts: {restart_data['total_restarts']})")

    try:
        # Load contract ABI from GCS URL
        abi_url = os.getenv("ESCROW_FACTORY_ABI_URL")
        if abi_url:
            logger.info(f"Loading ABI from GCS: {abi_url}")
            contract_abi = load_abi_from_gcs(abi_url)
        else:
            logger.warning("ESCROW_FACTORY_ABI_URL not set, using minimal ABI")
            contract_abi = [
                {
                    "anonymous": False,
                    "inputs": [
                        {"indexed": True, "name": "escrow", "type": "address"},
                        {"indexed": True, "name": "payer", "type": "address"},
                        {"indexed": True, "name": "payee", "type": "address"},
                        {"indexed": False, "name": "amount", "type": "uint256"},
                        {"indexed": False, "name": "releaseDelay", "type": "uint256"},
                        {"indexed": False, "name": "approvalsRequired", "type": "uint8"},
                    ],
                    "name": "EscrowDeployed",
                    "type": "event",
                }
            ]

        # Create relayer configuration
        config = RelayerConfig(
            chain_id=os.getenv("CHAIN_ID", "11155111"),
            rpc_url=os.getenv("RPC_URL", "https://rpc.sepolia.org"),
            contract_address=os.getenv(
                "CONTRACT_ADDRESS", "0x740ca091aC2371524a6E1aAE1BBC3c2308C2d9A5"
            ),
            contract_abi=contract_abi,
            event_names=["EscrowDeployed"],
            pubsub_project_id=os.getenv("PUBSUB_PROJECT_ID", "fusion-prime"),
            pubsub_topic_id=os.getenv("PUBSUB_TOPIC", "settlement.events.v1"),
            start_block=int(os.getenv("START_BLOCK", "9442989")),
            poll_interval_seconds=int(os.getenv("RELAYER_POLL_INTERVAL", "12")),
            batch_size=int(os.getenv("RELAYER_BATCH_SIZE", "10")),  # Configurable batch size
            max_retries=3,
            rpc_rate_limit_delay=0.1,
            rpc_max_retries=5,
            rpc_backoff_factor=2.0,
            rpc_max_backoff=60.0,
            checkpoint_interval_blocks=int(os.getenv("RELAYER_CHECKPOINT_INTERVAL", "100")),
            cleanup_interval_hours=24,
            checkpoint_store_type="sqlite",
            checkpoint_store_url=None,
            max_concurrent_requests=int(
                os.getenv("MAX_CONCURRENT_REQUESTS", "10")
            ),  # Phase 5: concurrent queries
        )

        # Initialize relayer with error handling
        try:
            relayer = ProductionEventRelayer(config)
            logger.info("Relayer initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize relayer: {e}")
            relayer = None

        # Start relayer in background task if initialization succeeded
        if relayer:
            try:
                relayer_task = asyncio.create_task(relayer.start())
                logger.info("Relayer service started successfully")
            except Exception as e:
                logger.warning(f"Failed to start relayer task: {e}")
                relayer_task = None
        else:
            logger.warning("Relayer service started in degraded mode (relayer not initialized)")

    except Exception as e:
        logger.error(f"Failed to start relayer service: {e}")
        # Don't raise - allow service to start in degraded mode
        relayer = None
        relayer_task = None


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown the relayer gracefully"""
    global relayer, relayer_task

    if relayer:
        await relayer.shutdown()
        relayer = None
    if relayer_task:
        relayer_task.cancel()
        relayer_task = None
        try:
            await relayer_task
        except asyncio.CancelledError:
            pass

    logger.info("Relayer service stopped")


@app.get("/health")
async def health_check():
    """Health check endpoint with blockchain lag monitoring"""
    try:
        restart_metrics = get_restart_metrics()

        if not relayer:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "degraded",
                    "service": "escrow-event-relayer",
                    "version": "1.0.0",
                    "message": "Relayer not initialized - service running in degraded mode",
                    "container_restarts": restart_metrics["total_restarts"],
                },
            )

        # Check if relayer is running
        if not relayer.metrics.is_running:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "degraded",
                    "service": "escrow-event-relayer",
                    "version": "1.0.0",
                    "message": "Relayer not running - service running in degraded mode",
                    "container_restarts": restart_metrics["total_restarts"],
                },
            )

        # Get blockchain lag
        lag_info = await get_blockchain_lag(relayer)

        # Determine overall health status
        overall_status = "healthy"
        alerts = []

        if lag_info["status"] == "critical":
            overall_status = "warning"
            alerts.append(f"Blockchain lag critical: {lag_info['blocks_behind']} blocks behind")
        elif lag_info["status"] == "warning":
            alerts.append(f"Blockchain lag elevated: {lag_info['blocks_behind']} blocks behind")

        if relayer.metrics.errors_count > 0:
            alerts.append(f"Errors detected: {relayer.metrics.errors_count} total errors")

        return JSONResponse(
            status_code=200,
            content={
                "status": overall_status,
                "service": "escrow-event-relayer",
                "version": "1.0.0",
                "uptime": relayer.get_metrics()["uptime_seconds"],
                "processed_events": relayer.metrics.total_events_processed,
                "published_events": relayer.metrics.total_events_published,
                "errors": relayer.metrics.errors_count,
                "blockchain_sync": {
                    "last_processed_block": lag_info["last_processed_block"],
                    "current_blockchain_height": lag_info["current_blockchain_height"],
                    "blocks_behind": lag_info["blocks_behind"],
                    "sync_status": lag_info["status"],
                },
                "container_restarts": restart_metrics["total_restarts"],
                "alerts": alerts if alerts else None,
            },
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        restart_metrics = get_restart_metrics()
        return JSONResponse(
            status_code=200,
            content={
                "status": "degraded",
                "service": "escrow-event-relayer",
                "version": "1.0.0",
                "message": f"Health check failed: {str(e)}",
                "container_restarts": restart_metrics["total_restarts"],
            },
        )


@app.get("/status")
async def status_check():
    """Detailed status endpoint with blockchain sync and restart tracking"""
    try:
        if not relayer:
            raise HTTPException(status_code=503, detail="Relayer not initialized")

        # Get current checkpoint
        checkpoint = await relayer.checkpoint_store.get_checkpoint(
            relayer.config.chain_id, relayer.config.contract_address
        )

        # Get blockchain lag
        lag_info = await get_blockchain_lag(relayer)

        # Get restart metrics
        restart_metrics = get_restart_metrics()

        status_data = {
            "status": "running" if relayer.metrics.is_running else "stopped",
            "service": "escrow-event-relayer",
            "version": "1.0.0",
            "metrics": {
                "uptime_seconds": relayer.get_metrics()["uptime_seconds"],
                "total_events_processed": relayer.metrics.total_events_processed,
                "total_events_published": relayer.metrics.total_events_published,
                "errors_count": relayer.metrics.errors_count,
                "last_processed_block": (checkpoint.last_processed_block if checkpoint else None),
            },
            "blockchain_sync": {
                "last_processed_block": lag_info["last_processed_block"],
                "current_blockchain_height": lag_info["current_blockchain_height"],
                "blocks_behind": lag_info["blocks_behind"],
                "sync_status": lag_info["status"],
            },
            "container_lifecycle": {
                "total_restarts": restart_metrics["total_restarts"],
                "current_start_time": container_start_time.isoformat(),
                "recent_restarts": restart_metrics["restarts"][-5:],  # Last 5 restarts
            },
            "configuration": {
                "chain_id": relayer.config.chain_id,
                "contract_address": relayer.config.contract_address,
                "start_block": relayer.config.start_block,
                "poll_interval_seconds": relayer.config.poll_interval_seconds,
                "rpc_rate_limit_delay": relayer.config.rpc_rate_limit_delay,
            },
        }

        return JSONResponse(status_code=200, content=status_data)

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@app.get("/metrics")
async def get_metrics():
    """Metrics endpoint"""
    try:
        if not relayer:
            raise HTTPException(status_code=503, detail="Relayer not initialized")

        metrics_data = {
            "uptime_seconds": relayer.get_metrics()["uptime_seconds"],
            "total_events_processed": relayer.metrics.total_events_processed,
            "total_events_published": relayer.metrics.total_events_published,
            "errors_count": relayer.metrics.errors_count,
            "last_processed_block": None,
        }

        # Get last processed block from checkpoint
        try:
            checkpoint = await relayer.checkpoint_store.get_checkpoint(
                relayer.config.chain_id, relayer.config.contract_address
            )
            if checkpoint:
                metrics_data["last_processed_block"] = checkpoint.last_processed_block
        except Exception:
            pass  # Ignore checkpoint errors for metrics

        return JSONResponse(status_code=200, content=metrics_data)

    except Exception as e:
        logger.error(f"Metrics check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Metrics check failed: {str(e)}")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
