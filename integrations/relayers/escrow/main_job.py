"""
Batch job entry point for escrow event relayer
Designed to run as a Cloud Run Job triggered by Cloud Scheduler
"""

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timedelta

from abi import ESCROW_CONTRACT_ABI, FACTORY_ABI
from production_relayer import ProductionEventRelayer, RelayerConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

# Global shutdown flag
shutdown_flag = False


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global shutdown_flag
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_flag = True


def get_relayer_config() -> RelayerConfig:
    """Build relayer configuration from environment variables"""

    # Required environment variables
    chain_id = os.getenv("CHAIN_ID", "31337")  # Default to Anvil
    rpc_url = os.getenv("RPC_URL", "http://localhost:8545")
    contract_address = os.getenv("CONTRACT_ADDRESS")
    if not contract_address:
        raise ValueError("CONTRACT_ADDRESS environment variable is required")

    pubsub_project_id = os.getenv("PUBSUB_PROJECT_ID", "local-project")
    pubsub_topic_id = os.getenv("PUBSUB_TOPIC_ID", "settlement.events.v1")

    # Optional configuration
    start_block = int(os.getenv("START_BLOCK", "0"))
    poll_interval = int(os.getenv("POLL_INTERVAL_SECONDS", "12"))
    batch_size = int(os.getenv("BATCH_SIZE", "1000"))
    checkpoint_interval = int(os.getenv("CHECKPOINT_INTERVAL_BLOCKS", "100"))

    # Checkpoint store configuration
    checkpoint_store_type = os.getenv("CHECKPOINT_STORE_TYPE", "sqlite")
    checkpoint_store_url = os.getenv("CHECKPOINT_STORE_URL")

    # Events to monitor
    event_names = os.getenv("EVENT_NAMES", "EscrowDeployed").split(",")

    return RelayerConfig(
        chain_id=chain_id,
        rpc_url=rpc_url,
        contract_address=contract_address,
        contract_abi=FACTORY_ABI,  # Factory ABI for EscrowDeployed events
        event_names=event_names,
        pubsub_project_id=pubsub_project_id,
        pubsub_topic_id=pubsub_topic_id,
        start_block=start_block,
        poll_interval_seconds=poll_interval,
        batch_size=batch_size,
        checkpoint_interval_blocks=checkpoint_interval,
        checkpoint_store_type=checkpoint_store_type,
        checkpoint_store_url=checkpoint_store_url,
    )


async def run_relayer_batch(relayer: ProductionEventRelayer, duration_minutes: int):
    """Run relayer for a specified duration then exit"""
    end_time = datetime.utcnow() + timedelta(minutes=duration_minutes)

    logger.info(f"Starting batch run for {duration_minutes} minutes (until {end_time})")

    # Start relayer in background
    relayer_task = asyncio.create_task(relayer.start())

    try:
        # Poll until time limit or shutdown signal
        while datetime.utcnow() < end_time and not shutdown_flag:
            await asyncio.sleep(10)  # Check every 10 seconds

            # Log progress
            metrics = relayer.get_metrics()
            logger.debug(
                f"Progress: processed={metrics['total_events_processed']}, "
                f"published={metrics['total_events_published']}, "
                f"last_block={metrics['last_processed_block']}, "
                f"errors={metrics['errors_count']}"
            )
    finally:
        logger.info("Batch run complete, shutting down relayer...")
        await relayer.shutdown()

        # Cancel relayer task if still running
        if not relayer_task.done():
            relayer_task.cancel()
            try:
                await relayer_task
            except asyncio.CancelledError:
                pass


async def main():
    """Main entry point for batch job"""
    logger.info("=" * 80)
    logger.info("Starting Fusion Prime Escrow Event Relayer (Batch Job Mode)")
    logger.info("=" * 80)

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Load configuration
        config = get_relayer_config()

        logger.info(f"Configuration:")
        logger.info(f"  Chain ID: {config.chain_id}")
        logger.info(f"  RPC URL: {config.rpc_url}")
        logger.info(f"  Contract: {config.contract_address}")
        logger.info(f"  Events: {config.event_names}")
        logger.info(f"  Pub/Sub Topic: {config.pubsub_topic_id}")
        logger.info(f"  Checkpoint Store: {config.checkpoint_store_type}")
        logger.info(f"  Start Block: {config.start_block}")

        # Get batch duration (default 5 minutes)
        batch_duration = int(os.getenv("BATCH_DURATION_MINUTES", "5"))
        logger.info(f"  Batch Duration: {batch_duration} minutes")

        # Create relayer
        relayer = ProductionEventRelayer(config)

        # Run batch processing
        await run_relayer_batch(relayer, batch_duration)

        # Final metrics
        final_metrics = relayer.get_metrics()
        logger.info("=" * 80)
        logger.info("Batch Job Complete - Final Metrics:")
        logger.info(f"  Events Processed: {final_metrics['total_events_processed']}")
        logger.info(f"  Events Published: {final_metrics['total_events_published']}")
        logger.info(f"  Last Block: {final_metrics['last_processed_block']}")
        logger.info(f"  Errors: {final_metrics['errors_count']}")
        logger.info(f"  Duration: {final_metrics['uptime_seconds']:.0f}s")
        logger.info("=" * 80)

        # Exit with success
        sys.exit(0)

    except Exception as e:
        logger.error(f"Fatal error in batch job: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
