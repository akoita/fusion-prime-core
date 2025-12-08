"""
Production-grade event relayer with checkpoint persistence and monitoring
"""

import asyncio
import logging
import signal
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

from abi import ESCROW_CONTRACT_ABI, FACTORY_ABI
from checkpoint_store import (
    Checkpoint,
    CheckpointStore,
    PostgreSQLCheckpointStore,
    ProcessedEvent,
    SQLiteCheckpointStore,
)
from escrow_registry import EscrowRegistry
from google.cloud import pubsub_v1
from web3 import Web3
from web3.contract import Contract
from web3.types import EventData

logger = logging.getLogger(__name__)


@dataclass
class RelayerConfig:
    """Configuration for the event relayer"""

    chain_id: str
    rpc_url: str
    contract_address: str
    contract_abi: List[Dict[str, Any]]
    event_names: List[str]
    pubsub_project_id: str
    pubsub_topic_id: str
    start_block: int = 0
    poll_interval_seconds: int = 12
    batch_size: int = 5  # Alchemy free tier limit - very conservative
    max_retries: int = 3
    rpc_rate_limit_delay: float = 0.1  # 100ms delay between RPC calls
    rpc_max_retries: int = 5  # Max retries for RPC calls
    rpc_backoff_factor: float = 2.0  # Exponential backoff factor
    rpc_max_backoff: float = 60.0  # Max backoff time in seconds
    max_concurrent_requests: int = 10  # Max concurrent RPC requests for escrow queries
    checkpoint_interval_blocks: int = 100
    cleanup_interval_hours: int = 24
    checkpoint_store_type: str = "sqlite"  # "sqlite" or "postgresql"
    checkpoint_store_url: Optional[str] = None


@dataclass
class RelayerMetrics:
    """Relayer metrics for monitoring"""

    total_events_processed: int = 0
    total_events_published: int = 0
    last_processed_block: int = 0
    last_checkpoint_time: Optional[datetime] = None
    errors_count: int = 0
    started_at: datetime = datetime.now(timezone.utc)
    is_running: bool = False


EventHandler = Callable[[EventData], Awaitable[bytes]]


class ProductionEventRelayer:
    """Production-grade event relayer with checkpoint persistence and monitoring"""

    def __init__(self, config: RelayerConfig):
        self.config = config
        self.metrics = RelayerMetrics()
        self._running = False
        self._shutdown_event = asyncio.Event()

        # Initialize Web3 with appropriate provider
        if config.rpc_url.startswith("wss://"):
            from web3.providers import WebsocketProvider

            logger.info(f"Using WebsocketProvider for WebSocket connection: {config.rpc_url}")
            self.web3 = Web3(WebsocketProvider(config.rpc_url))
        else:
            self.web3 = Web3(Web3.HTTPProvider(config.rpc_url))

        if not self.web3.is_connected():
            raise ConnectionError(f"Cannot connect to RPC: {config.rpc_url}")

        # Initialize contract
        self.contract: Contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(config.contract_address),
            abi=config.contract_abi,
        )

        # Initialize Pub/Sub publisher (with fallback for testing)
        try:
            self.publisher = pubsub_v1.PublisherClient()
            self.topic_path = self.publisher.topic_path(
                config.pubsub_project_id, config.pubsub_topic_id
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Pub/Sub client: {e}")
            logger.warning("Running in test mode without Pub/Sub")
            self.publisher = None
            self.topic_path = None

        # Initialize checkpoint store
        if config.checkpoint_store_type == "postgresql":
            if not config.checkpoint_store_url:
                raise ValueError("checkpoint_store_url required for PostgreSQL")
            self.checkpoint_store: CheckpointStore = PostgreSQLCheckpointStore(
                config.checkpoint_store_url
            )
        else:
            db_path = (
                config.checkpoint_store_url
                or f"relayer_{config.chain_id}_{config.contract_address}.db"
            )
            self.checkpoint_store = SQLiteCheckpointStore(db_path)

        # Initialize escrow registry for dynamic escrow discovery
        registry_path = f"/tmp/escrow_registry_{config.chain_id}.json"
        self.escrow_registry = EscrowRegistry(checkpoint_file=registry_path)
        logger.info(f"Initialized escrow registry with {self.escrow_registry.count()} escrows")

        # Initialize semaphore for concurrent request limiting
        self._query_semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        logger.info(f"Concurrent query limit: {config.max_concurrent_requests} requests")

        logger.info(
            f"Initialized relayer for {config.chain_id}:{config.contract_address}, "
            f"monitoring events: {config.event_names}"
        )

    async def start(self) -> None:
        """Start the relayer"""
        if self._running:
            logger.warning("Relayer is already running")
            return

        self._running = True
        self.metrics.is_running = True
        self.metrics.started_at = datetime.now(timezone.utc)

        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))

        logger.info("Starting production event relayer...")

        try:
            # Start background tasks
            relay_task = asyncio.create_task(self._relay_loop())
            cleanup_task = asyncio.create_task(self._cleanup_loop())

            # Wait for shutdown signal
            await self._shutdown_event.wait()

            # Cancel tasks
            relay_task.cancel()
            cleanup_task.cancel()

            try:
                await relay_task
            except asyncio.CancelledError:
                pass

            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass

        finally:
            await self.checkpoint_store.close()
            logger.info("Relayer shut down gracefully")

    async def shutdown(self) -> None:
        """Graceful shutdown"""
        if not self._running:
            return

        logger.info("Shutting down relayer...")
        self._running = False
        self.metrics.is_running = False
        self._shutdown_event.set()

    async def _relay_loop(self) -> None:
        """Main relay loop"""
        while self._running:
            try:
                # Get last checkpoint
                checkpoint = await self.checkpoint_store.get_checkpoint(
                    self.config.chain_id, self.config.contract_address
                )

                # Determine starting block
                if checkpoint:
                    from_block = checkpoint.last_processed_block + 1
                    logger.info(f"Resuming from block {from_block} (checkpoint found)")
                else:
                    from_block = self.config.start_block
                    logger.info(f"Starting from block {from_block} (no checkpoint)")

                # Get current block with rate limiting retry
                latest_block = await self._get_latest_block_with_retry()
                to_block = min(from_block + self.config.batch_size - 1, latest_block)

                if from_block > latest_block:
                    # No new blocks, wait
                    await asyncio.sleep(self.config.poll_interval_seconds)
                    continue

                logger.info(f"Processing blocks {from_block} to {to_block}")

                # Process events in smaller batches to respect Alchemy free tier limits
                events_processed = 0
                current_from = from_block
                while current_from <= to_block:
                    current_to = min(current_from + self.config.batch_size - 1, to_block)
                    logger.info(f"Processing batch: blocks {current_from} to {current_to}")
                    batch_events = await self._process_block_range(current_from, current_to)
                    events_processed += batch_events
                    current_from = current_to + 1

                # Save checkpoint after every batch to track progress
                # This ensures we don't reprocess the same blocks on restart
                await self._save_checkpoint(to_block, events_processed)

                # Update metrics
                self.metrics.last_processed_block = to_block
                self.metrics.total_events_processed += events_processed

                # Wait before next iteration
                await asyncio.sleep(self.config.poll_interval_seconds)

            except Exception as e:
                logger.error(f"Error in relay loop: {e}", exc_info=True)
                self.metrics.errors_count += 1
                await asyncio.sleep(self.config.poll_interval_seconds * 2)

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if the error is a rate limiting error"""
        error_str = str(error).lower()
        rate_limit_indicators = [
            "rate limit",
            "too many requests",
            "429",
            "quota exceeded",
            "throttled",
            "request limit",
            "rate exceeded",
            "free tier",
            "block range",
            "eth_newfilter",
        ]
        return any(indicator in error_str for indicator in rate_limit_indicators)

    async def _fetch_events_with_retry(
        self, event_filter, from_block: int, to_block: int
    ) -> List[EventData]:
        """Fetch events with rate limiting retry logic"""
        for attempt in range(self.config.rpc_max_retries):
            try:
                # Rate limiting: Add delay before RPC call
                await asyncio.sleep(self.config.rpc_rate_limit_delay)

                # Use WebSocket filter for real-time event monitoring
                if self.config.rpc_url.startswith("wss://"):
                    # Create a filter and get all entries for WebSocket connections
                    filter_id = event_filter.create_filter(fromBlock=from_block, toBlock=to_block)
                    events = filter_id.get_all_entries()
                    # Clean up the filter
                    self.web3.eth.uninstall_filter(filter_id.filter_id)
                else:
                    # Use HTTP for non-WebSocket connections
                    events = event_filter.get_logs(fromBlock=from_block, toBlock=to_block)
                return events

            except Exception as e:
                if self._is_rate_limit_error(e):
                    if attempt < self.config.rpc_max_retries - 1:
                        # Calculate exponential backoff with jitter
                        backoff_time = min(
                            self.config.rpc_rate_limit_delay
                            * (self.config.rpc_backoff_factor**attempt),
                            self.config.rpc_max_backoff,
                        )
                        logger.warning(
                            f"Rate limit hit (attempt {attempt + 1}/{self.config.rpc_max_retries}): {e}. Retrying in {backoff_time:.2f}s"
                        )
                        await asyncio.sleep(backoff_time)
                        continue
                    else:
                        logger.error(
                            f"Rate limit exceeded after {self.config.rpc_max_retries} attempts: {e}"
                        )
                        raise
                else:
                    # Non-rate-limit error, re-raise immediately
                    logger.error(f"Non-rate-limit RPC error: {e}")
                    raise

        return []

    async def _get_latest_block_with_retry(self) -> int:
        """Get latest block with rate limiting retry logic"""
        for attempt in range(self.config.rpc_max_retries):
            try:
                # Rate limiting: Add delay before RPC call
                await asyncio.sleep(self.config.rpc_rate_limit_delay)

                # Get latest block
                latest_block = self.web3.eth.block_number
                return latest_block

            except Exception as e:
                if self._is_rate_limit_error(e):
                    if attempt < self.config.rpc_max_retries - 1:
                        # Calculate exponential backoff with jitter
                        backoff_time = min(
                            self.config.rpc_rate_limit_delay
                            * (self.config.rpc_backoff_factor**attempt),
                            self.config.rpc_max_backoff,
                        )
                        logger.warning(
                            f"Rate limit hit getting latest block (attempt {attempt + 1}/{self.config.rpc_max_retries}): {e}. Retrying in {backoff_time:.2f}s"
                        )
                        await asyncio.sleep(backoff_time)
                        continue
                    else:
                        logger.error(
                            f"Rate limit exceeded getting latest block after {self.config.rpc_max_retries} attempts: {e}"
                        )
                        raise
                else:
                    # Non-rate-limit error, re-raise immediately
                    logger.error(f"Non-rate-limit RPC error getting latest block: {e}")
                    raise

        # This should never be reached, but just in case
        raise Exception("Failed to get latest block after all retries")

    def _get_contract(self, contract_address: str, abi: List[Dict[str, Any]]) -> Contract:
        """
        Get contract instance for specific address and ABI.

        Args:
            contract_address: Contract address (hex string)
            abi: Contract ABI

        Returns:
            Web3 Contract instance
        """
        return self.web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=abi,
        )

    async def _query_contract_events(
        self,
        contract_address: str,
        abi: List[Dict[str, Any]],
        event_name: str,
        from_block: int,
        to_block: int,
    ) -> List[EventData]:
        """
        Query events from a specific contract.

        This is a generic method that can query events from any contract address
        with any ABI. Used for dynamic escrow monitoring.

        Args:
            contract_address: Contract address to query
            abi: Contract ABI
            event_name: Event name to query
            from_block: Starting block
            to_block: Ending block

        Returns:
            List of event data

        Raises:
            Exception: If query fails after retries
        """
        try:
            # Get contract instance
            contract = self._get_contract(contract_address, abi)

            # Get event filter
            event_filter = getattr(contract.events, event_name)

            # Fetch events with retry logic
            events = await self._fetch_events_with_retry(event_filter, from_block, to_block)

            return events

        except AttributeError as e:
            logger.error(
                f"Event '{event_name}' not found in ABI for contract {contract_address}: {e}"
            )
            return []
        except Exception as e:
            logger.error(
                f"Failed to query {event_name} from {contract_address} "
                f"(blocks {from_block}-{to_block}): {e}"
            )
            raise

    async def _query_escrow_events(
        self, escrow_address: str, from_block: int, to_block: int
    ) -> List[EventData]:
        """
        Query all lifecycle events from a single escrow contract with rate limiting.

        Uses semaphore to limit concurrent RPC requests.

        Args:
            escrow_address: Escrow contract address
            from_block: Starting block
            to_block: Ending block

        Returns:
            List of all events (Approved, EscrowReleased, EscrowRefunded) from this escrow
        """
        escrow_events: List[EventData] = []
        event_names = ["Approved", "EscrowReleased", "EscrowRefunded"]

        async with self._query_semaphore:  # Rate limiting
            for event_name in event_names:
                try:
                    events = await self._query_contract_events(
                        contract_address=escrow_address,
                        abi=ESCROW_CONTRACT_ABI,
                        event_name=event_name,
                        from_block=from_block,
                        to_block=to_block,
                    )

                    if events:
                        logger.debug(
                            f"Found {len(events)} {event_name} events from {escrow_address[:10]}..."
                        )
                        escrow_events.extend(events)

                except Exception as e:
                    # Log error but don't fail entire batch
                    logger.warning(
                        f"Failed to query {event_name} from {escrow_address[:10]}...: {e}"
                    )
                    self.metrics.errors_count += 1

        return escrow_events

    async def _process_block_range(self, from_block: int, to_block: int) -> int:
        """
        Process events in a block range with dynamic escrow monitoring.

        This method:
        1. Queries Factory for EscrowDeployed events to discover new escrows
        2. Registers newly discovered escrow addresses
        3. Queries all registered escrows for lifecycle events (Approved, Released, Refunded)
        4. Publishes all events to Pub/Sub
        5. Saves registry checkpoint
        """
        events_processed = 0
        all_events: List[EventData] = []

        # Step 1: Query Factory for EscrowDeployed events
        logger.debug(f"Querying Factory for EscrowDeployed events (blocks {from_block}-{to_block})")
        try:
            factory_events = await self._query_contract_events(
                contract_address=self.config.contract_address,  # Factory address
                abi=FACTORY_ABI,
                event_name="EscrowDeployed",
                from_block=from_block,
                to_block=to_block,
            )

            all_events.extend(factory_events)

            # Step 2: Register newly discovered escrows
            for event in factory_events:
                escrow_address = event["args"]["escrow"]
                is_new = self.escrow_registry.add_escrow(escrow_address)
                if is_new:
                    logger.info(
                        f"🆕 Discovered new escrow: {escrow_address} at block {event['blockNumber']}"
                    )

        except Exception as e:
            logger.error(f"Failed to query Factory for EscrowDeployed: {e}", exc_info=True)
            self.metrics.errors_count += 1

        # Step 3: Get all registered escrows
        all_escrows = self.escrow_registry.get_all_escrows()
        logger.debug(f"Monitoring {len(all_escrows)} escrows for lifecycle events")

        # Step 4: Query all escrows concurrently for lifecycle events
        # Events to monitor: Approved, EscrowReleased, EscrowRefunded
        # Use asyncio.gather() for parallel queries with semaphore rate limiting
        if all_escrows:
            logger.info(
                f"Querying {len(all_escrows)} escrows concurrently "
                f"(max {self.config.max_concurrent_requests} concurrent)"
            )

            # Create tasks for all escrows
            escrow_query_tasks = [
                self._query_escrow_events(escrow_address, from_block, to_block)
                for escrow_address in all_escrows
            ]

            # Execute all queries concurrently
            escrow_results = await asyncio.gather(*escrow_query_tasks, return_exceptions=True)

            # Collect results
            for escrow_address, result in zip(all_escrows, escrow_results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to query escrow {escrow_address[:10]}...: {result}")
                    self.metrics.errors_count += 1
                elif isinstance(result, list):
                    all_events.extend(result)

            logger.debug(f"Collected {len(all_events) - len(factory_events)} events from escrows")

        # Step 5: Process and publish all collected events
        for event in all_events:
            try:
                # Generate event ID for deduplication
                event_id = (
                    f"{self.config.chain_id}:{event['transactionHash'].hex()}:{event['logIndex']}"
                )

                # Check if already processed (replay protection)
                if await self.checkpoint_store.is_event_processed(event_id):
                    logger.debug(f"Skipping already processed event {event_id}")
                    continue

                # Publish event (contract address will be extracted from event['address'])
                await self._publish_event(event)

                # Mark as processed
                # Use actual contract address from the event
                contract_address = (
                    event["address"] if "address" in event else self.config.contract_address
                )

                processed_event = ProcessedEvent(
                    event_id=event_id,
                    chain_id=self.config.chain_id,
                    contract_address=contract_address,
                    block_number=event["blockNumber"],
                    transaction_hash=event["transactionHash"].hex(),
                    log_index=event["logIndex"],
                    event_name=event["event"],
                    processed_at=datetime.now(timezone.utc),
                    published=True,
                    event_metadata={"args": dict(event["args"])},
                )

                await self.checkpoint_store.mark_event_processed(processed_event)
                events_processed += 1

                logger.info(
                    f"✅ Processed {event['event']} from {contract_address[:10]}... "
                    f"at block {event['blockNumber']}, tx {event['transactionHash'].hex()[:10]}..."
                )

            except Exception as e:
                logger.error(f"Failed to process event {event}: {e}", exc_info=True)
                self.metrics.errors_count += 1

        # Step 6: Save registry checkpoint (persist discovered escrows)
        if events_processed > 0:
            self.escrow_registry.save()
            logger.debug(f"Saved escrow registry with {self.escrow_registry.count()} escrows")

        return events_processed

    async def _publish_event(self, event: EventData) -> None:
        """Publish event to Pub/Sub"""
        # Convert event to protobuf message
        # For now, we'll serialize as JSON (replace with proper protobuf later)

        # Use the actual contract address that emitted the event
        # For Factory events: this is the Factory address
        # For Escrow events: this is the Escrow contract address
        contract_address = event["address"] if "address" in event else self.config.contract_address

        message_data = {
            "chain_id": self.config.chain_id,
            "contract_address": contract_address,
            "event_name": event["event"],
            "block_number": event["blockNumber"],
            "transaction_hash": event["transactionHash"].hex(),
            "log_index": event["logIndex"],
            "args": {k: str(v) for k, v in event["args"].items()},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        import json

        message_bytes = json.dumps(message_data).encode("utf-8")

        # Fail if publisher is None (should not happen in production)
        if self.publisher is None:
            error_msg = "Cannot publish event: Pub/Sub publisher not initialized"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        for attempt in range(self.config.max_retries):
            try:
                future = self.publisher.publish(
                    self.topic_path,
                    message_bytes,
                    chain_id=str(self.config.chain_id),
                    event_name=event["event"],
                )

                # Wait for publish to complete
                message_id = future.result(timeout=10.0)
                logger.info(
                    f"Published {event['event']} event to Pub/Sub, message_id={message_id}, block={event['blockNumber']}"
                )

                self.metrics.total_events_published += 1
                return

            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    logger.warning(f"Publish attempt {attempt + 1} failed: {e}, retrying...")
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                else:
                    logger.error(
                        f"Failed to publish event after {self.config.max_retries} attempts: {e}",
                        exc_info=True,
                    )
                    raise

    async def _save_checkpoint(self, block_number: int, events_count: int) -> None:
        """Save checkpoint"""
        checkpoint = Checkpoint(
            chain_id=self.config.chain_id,
            contract_address=self.config.contract_address,
            last_processed_block=block_number,
            last_processed_timestamp=datetime.now(timezone.utc),
            total_events_processed=self.metrics.total_events_processed + events_count,
            event_metadata={
                "last_checkpoint_time": datetime.now(timezone.utc).isoformat(),
                "events_in_batch": events_count,
            },
        )

        await self.checkpoint_store.save_checkpoint(checkpoint)
        self.metrics.last_checkpoint_time = datetime.now(timezone.utc)

    async def _cleanup_loop(self) -> None:
        """Periodic cleanup of old processed events"""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval_hours * 3600)

                # Clean up events older than 7 days
                cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)
                removed = await self.checkpoint_store.cleanup_old_events(cutoff_time)

                logger.info(f"Cleaned up {removed} old processed events")

            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        uptime = datetime.now(timezone.utc) - self.metrics.started_at
        return {
            "is_running": self.metrics.is_running,
            "total_events_processed": self.metrics.total_events_processed,
            "total_events_published": self.metrics.total_events_published,
            "last_processed_block": self.metrics.last_processed_block,
            "last_checkpoint_time": (
                self.metrics.last_checkpoint_time.isoformat()
                if self.metrics.last_checkpoint_time
                else None
            ),
            "errors_count": self.metrics.errors_count,
            "uptime_seconds": uptime.total_seconds(),
            "started_at": self.metrics.started_at.isoformat(),
            "chain_id": self.config.chain_id,
            "contract_address": self.config.contract_address,
        }
