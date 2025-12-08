"""
Production entry point for escrow event relayer
"""

import asyncio
import logging
import os
import sys

from abi import ESCROW_CONTRACT_ABI, FACTORY_ABI
from production_relayer import ProductionEventRelayer, RelayerConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


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


async def main():
    """Main entry point"""
    logger.info("Starting Fusion Prime Escrow Event Relayer (Production)")

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

        # Create and start relayer
        relayer = ProductionEventRelayer(config)

        # Start metrics logging task
        async def log_metrics():
            while True:
                await asyncio.sleep(60)  # Log every minute
                metrics = relayer.get_metrics()
                logger.info(
                    f"Metrics: processed={metrics['total_events_processed']}, "
                    f"published={metrics['total_events_published']}, "
                    f"last_block={metrics['last_processed_block']}, "
                    f"errors={metrics['errors_count']}, "
                    f"uptime={metrics['uptime_seconds']:.0f}s"
                )

        metrics_task = asyncio.create_task(log_metrics())

        # Start relayer (blocks until shutdown)
        await relayer.start()

        # Cancel metrics task
        metrics_task.cancel()
        try:
            await metrics_task
        except asyncio.CancelledError:
            pass

        logger.info("Relayer stopped successfully")

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
