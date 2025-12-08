"""
Blockchain Event Relayer Service

Monitors blockchain for smart contract events and publishes them to Pub/Sub.
This is the critical link between blockchain transactions and the event-driven system.

Runs as a Cloud Run Service with continuous blockchain monitoring.
"""

import asyncio
import json
import logging
import os
import sys
import threading
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request
from google.cloud import pubsub_v1
from web3 import Web3
from web3.contract import Contract

# Import contract registry for ABI loading
try:
    from services.shared.contract_registry import ContractRegistry

    CONTRACT_REGISTRY_AVAILABLE = True
except ImportError:
    CONTRACT_REGISTRY_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Flask app for health checks
app = Flask(__name__)

# Global relayer instance for status reporting
relayer_instance = None


class BlockchainEventRelayer:
    """Relays blockchain events to Pub/Sub."""

    def __init__(
        self,
        rpc_url: str,
        factory_address: str,
        factory_abi: list,
        gcp_project: str,
        pubsub_topic: str,
        poll_interval: int = 5,
        start_block: Optional[int] = None,
        escrow_abi: Optional[list] = None,
        batch_size: int = 100,
    ):
        """
        Initialize the relayer.

        Args:
            rpc_url: Blockchain RPC URL (Anvil/Sepolia)
            factory_address: EscrowFactory contract address
            factory_abi: EscrowFactory ABI as list of dictionaries
            gcp_project: GCP project ID
            pubsub_topic: Pub/Sub topic to publish events
            poll_interval: Seconds between polls (default: 3, can be overridden via RELAYER_POLL_INTERVAL)
            start_block: Block to start scanning from (default: latest)
            escrow_abi: Escrow contract ABI for monitoring individual escrows
            batch_size: Number of blocks to process in parallel (default: 100)
        """
        self.rpc_url = rpc_url
        self.factory_address = Web3.to_checksum_address(factory_address)
        self.gcp_project = gcp_project
        self.pubsub_topic = pubsub_topic
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self.is_running = False
        self.events_processed = 0
        self.auto_fast_forward_threshold = int(
            os.getenv("RELAYER_AUTO_FAST_FORWARD_THRESHOLD", "500")
        )  # Auto fast-forward if >500 blocks behind
        self.last_fast_forward_check = (
            0  # Track when we last checked for fast-forward to avoid constant resets
        )

        # Initialize Web3
        logger.info(f"Connecting to blockchain: {rpc_url}")
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to blockchain at {rpc_url}")

        chain_id = self.w3.eth.chain_id
        logger.info(f"✅ Connected to blockchain (Chain ID: {chain_id})")

        # Use provided ABI directly
        logger.info("Using provided contract ABI")

        # Initialize contract
        self.factory_contract: Contract = self.w3.eth.contract(
            address=self.factory_address, abi=factory_abi
        )
        logger.info(f"✅ Loaded EscrowFactory contract at {self.factory_address}")

        # Initialize Pub/Sub publisher
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(gcp_project, pubsub_topic)
        logger.info(f"✅ Pub/Sub publisher initialized (topic: {pubsub_topic})")

        # Track last processed block
        self.last_processed_block = start_block or self.w3.eth.block_number
        logger.info(f"Starting from block: {self.last_processed_block}")

        # Event processors for EscrowFactory events
        self.event_processors = {
            "EscrowDeployed": self._process_escrow_deployed,
        }

        # Escrow contract monitoring
        self.escrow_abi = escrow_abi
        self.tracked_escrows = set()  # Set of escrow addresses being monitored

        if self.escrow_abi:
            logger.info("✅ Escrow ABI loaded - will monitor individual escrow contracts")
            # Event processors for individual Escrow contract events
            self.escrow_event_processors = {
                "EscrowCreated": self._process_escrow_created,
                "Approved": self._process_approved,
                "EscrowReleased": self._process_escrow_released,
                "EscrowRefunded": self._process_escrow_refunded,
            }
        else:
            logger.warning(
                "⚠️  No Escrow ABI provided - escrow lifecycle events will not be monitored"
            )
            self.escrow_event_processors = {}

    def _process_escrow_deployed(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process EscrowDeployed event and register escrow for monitoring."""
        args = event["args"]
        escrow_address = args["escrow"].lower()

        # ALWAYS track this escrow for lifecycle event monitoring
        # Even if escrow_abi is None, register it so we can monitor it later if ABI becomes available
        if escrow_address not in self.tracked_escrows:
            self.tracked_escrows.add(escrow_address)
            if self.escrow_abi:
                logger.info(
                    f"📝 Registered escrow {escrow_address} for monitoring (total: {len(self.tracked_escrows)})"
                )
            else:
                logger.warning(
                    f"⚠️  Registered escrow {escrow_address} but Escrow ABI not loaded - cannot monitor lifecycle events (total: {len(self.tracked_escrows)})"
                )

        return {
            "escrow": escrow_address,
            "payer": args["payer"].lower(),
            "payee": args["payee"].lower(),
            "amount": str(args["amount"]),
            "releaseDelay": args.get("releaseDelay", 0),
            "approvalsRequired": args.get("approvalsRequired", 0),
            "arbiter": args.get("arbiter", "0x" + "0" * 40).lower(),
            "transaction_hash": event["transactionHash"].hex(),
            "block_number": event["blockNumber"],
            "chain_id": self.w3.eth.chain_id,
        }

    def _process_escrow_created(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process EscrowCreated event from individual escrow contract."""
        args = event["args"]
        return {
            "contract_address": event["address"].lower(),  # Escrow contract that emitted the event
            "payer": args["payer"].lower(),
            "payee": args["payee"].lower(),
            "amount": str(args["amount"]),
            "release_time": int(args["releaseTime"]),
            "approvals_required": int(args["approvalsRequired"]),
            "transaction_hash": event["transactionHash"].hex(),
            "block_number": event["blockNumber"],
            "chain_id": self.w3.eth.chain_id,
        }

    def _process_approved(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process Approved event from individual escrow contract."""
        args = event["args"]
        return {
            "contract_address": event["address"].lower(),  # Escrow contract that emitted the event
            "approver": args["approver"].lower(),
            "transaction_hash": event["transactionHash"].hex(),
            "block_number": event["blockNumber"],
            "chain_id": self.w3.eth.chain_id,
        }

    def _process_escrow_released(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process EscrowReleased event from individual escrow contract."""
        args = event["args"]
        result = {
            "contract_address": event["address"].lower(),  # Escrow contract that emitted the event
            "payee": args["payee"].lower(),
            "amount": str(args["amount"]),
            "transaction_hash": event["transactionHash"].hex(),
            "block_number": event["blockNumber"],
            "chain_id": self.w3.eth.chain_id,
        }
        # Include timestamp if present (event signature includes timestamp parameter)
        if "timestamp" in args:
            result["timestamp"] = int(args["timestamp"])
        return result

    def _process_escrow_refunded(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process EscrowRefunded event from individual escrow contract."""
        args = event["args"]
        return {
            "contract_address": event["address"].lower(),  # Escrow contract that emitted the event
            "payer": args["payer"].lower(),
            "amount": str(args["amount"]),
            "transaction_hash": event["transactionHash"].hex(),
            "block_number": event["blockNumber"],
            "chain_id": self.w3.eth.chain_id,
        }

    def _publish_event(self, event_type: str, event_data: Dict[str, Any]):
        """Publish event to Pub/Sub."""
        try:
            # Encode event data as JSON
            message_data = json.dumps(event_data).encode("utf-8")

            # Log attributes being sent for debugging
            logger.info(f"🔍 Publishing with attributes: event_type='{event_type}'")

            # Publish with event_type attribute (critical for Settlement service routing)
            future = self.publisher.publish(
                self.topic_path,
                message_data,
                event_type=event_type,  # Settlement service checks this attribute
            )

            message_id = future.result(timeout=10)
            logger.info(
                f"📤 Published {event_type} to Pub/Sub "
                f"(message_id: {message_id}, escrow: {event_data.get('escrow', 'N/A')})"
            )
            return message_id

        except Exception as e:
            logger.error(f"❌ Failed to publish {event_type} to Pub/Sub: {e}")
            raise

    async def _scan_blocks(self, from_block: int, to_block: int):
        """Scan blocks for events in batches for optimal performance."""
        if from_block > to_block:
            return

        block_range = to_block - from_block + 1

        # If range is large, process in batches
        if block_range > self.batch_size:
            logger.info(
                f"🔍 Scanning {block_range} blocks in batches of {self.batch_size} (from {from_block} to {to_block})"
            )
            current_from = from_block
            while current_from <= to_block:
                current_to = min(current_from + self.batch_size - 1, to_block)
                await self._scan_block_range(current_from, current_to)
                current_from = current_to + 1
        else:
            await self._scan_block_range(from_block, to_block)

    async def _scan_block_range(self, from_block: int, to_block: int):
        """Scan a specific block range for events."""
        # Scan Factory contract events
        for event_name, processor in self.event_processors.items():
            try:
                event_filter = getattr(self.factory_contract.events, event_name)
                events = event_filter.get_logs(from_block=from_block, to_block=to_block)

                for event in events:
                    try:
                        # Process event
                        event_data = processor(event)

                        # Publish to Pub/Sub
                        self._publish_event(event_name, event_data)

                        # Increment counter
                        self.events_processed += 1

                        logger.info(
                            f"✅ Processed {event_name} at block {event['blockNumber']} "
                            f"(tx: {event['transactionHash'].hex()[:10]}...)"
                        )

                    except Exception as e:
                        logger.error(f"❌ Error processing {event_name} event: {e}")

            except Exception as e:
                error_str = str(e).lower()
                is_rate_limit = any(
                    indicator in error_str
                    for indicator in [
                        "rate limit",
                        "too many requests",
                        "429",
                        "throttle",
                        "quota exceeded",
                    ]
                )
                if is_rate_limit:
                    logger.warning(f"⚠️  Rate limit while fetching {event_name} events: {e}")
                else:
                    logger.error(f"❌ Error fetching {event_name} events: {e}")

        # Scan individual Escrow contract events
        if self.escrow_abi and self.tracked_escrows:
            await self._scan_escrow_events(from_block, to_block)

    async def _scan_escrow_events(self, from_block: int, to_block: int):
        """Scan tracked escrow contracts for lifecycle events (optimized with concurrent processing)."""
        escrow_list = list(
            self.tracked_escrows
        )  # Use list() to avoid modification during iteration

        if not escrow_list:
            return

        # Process escrows concurrently for better performance
        tasks = []
        for escrow_address in escrow_list:
            task = self._scan_single_escrow_events(escrow_address, from_block, to_block)
            tasks.append(task)

        # Run all escrow scans concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _scan_single_escrow_events(self, escrow_address: str, from_block: int, to_block: int):
        """Scan a single escrow contract for lifecycle events."""
        try:
            escrow_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(escrow_address), abi=self.escrow_abi
            )

            # Scan each event type for this escrow
            for event_name, processor in self.escrow_event_processors.items():
                try:
                    event_filter = getattr(escrow_contract.events, event_name)
                    events = event_filter.get_logs(from_block=from_block, to_block=to_block)

                    if events:
                        logger.debug(
                            f"🔍 Found {len(events)} {event_name} event(s) for escrow {escrow_address[:10]}... "
                            f"in blocks {from_block}-{to_block}"
                        )

                    for event in events:
                        try:
                            # Process event
                            event_data = processor(event)

                            # Publish to Pub/Sub
                            self._publish_event(event_name, event_data)

                            # Increment counter
                            self.events_processed += 1

                            logger.info(
                                f"✅ Processed {event_name} from escrow {escrow_address[:10]}... "
                                f"at block {event['blockNumber']} (tx: {event['transactionHash'].hex()[:10]}...)"
                            )

                        except Exception as e:
                            logger.error(
                                f"❌ Error processing {event_name} event from {escrow_address}: {e}",
                                exc_info=True,  # Include full traceback
                            )

                except Exception as e:
                    error_str = str(e).lower()
                    is_rate_limit = any(
                        indicator in error_str
                        for indicator in [
                            "rate limit",
                            "too many requests",
                            "429",
                            "throttle",
                            "quota exceeded",
                        ]
                    )
                    if is_rate_limit:
                        logger.warning(
                            f"⚠️  Rate limit while fetching {event_name} from {escrow_address}: {e}"
                        )
                    else:
                        logger.error(
                            f"❌ Error fetching {event_name} events from {escrow_address}: {e}",
                            exc_info=True,  # Include full traceback
                        )

        except Exception as e:
            logger.error(f"❌ Error scanning escrow {escrow_address}: {e}", exc_info=True)

    async def run(self):
        """Run the relayer continuously with optimized catch-up logic."""
        logger.info("🚀 Starting Blockchain Event Relayer")
        logger.info(f"   Factory: {self.factory_address}")
        logger.info(f"   Chain ID: {self.w3.eth.chain_id}")
        logger.info(f"   Pub/Sub Topic: {self.pubsub_topic}")
        logger.info(f"   Poll Interval: {self.poll_interval}s")
        logger.info(f"   Batch Size: {self.batch_size} blocks")
        logger.info("")

        self.is_running = True

        while self.is_running:
            try:
                # Get current block
                current_block = self.w3.eth.block_number
                blocks_behind = current_block - self.last_processed_block

                # Auto fast-forward if extremely far behind (e.g., after restart or long downtime)
                # Only check periodically (every 10 iterations) to avoid constant resets
                if blocks_behind > self.auto_fast_forward_threshold:
                    # Only fast-forward if we haven't checked recently (every 10 cycles)
                    # This prevents constant fast-forwarding if we're still catching up
                    if (
                        self.events_processed - self.last_fast_forward_check
                    ) > 10 or self.last_fast_forward_check == 0:
                        logger.warning(
                            f"⚠️  Relayer is extremely far behind ({blocks_behind} blocks) - auto fast-forwarding to catch up..."
                        )
                        # Fast-forward to current_block - 100 to skip historical blocks but keep some buffer
                        target_block = max(current_block - 100, self.last_processed_block)
                        old_block = self.last_processed_block
                        self.last_processed_block = target_block
                        blocks_skipped = target_block - old_block
                        logger.info(
                            f"⚡ Auto fast-forwarded: {old_block} → {target_block} "
                            f"(skipped {blocks_skipped} historical blocks, now {current_block - target_block} blocks behind)"
                        )
                        # Update blocks_behind after fast-forward
                        blocks_behind = current_block - self.last_processed_block
                        self.last_fast_forward_check = self.events_processed

                # Scan new blocks
                if current_block > self.last_processed_block:
                    if blocks_behind > 0:
                        logger.info(
                            f"📊 Processing {blocks_behind} block(s) behind (last: {self.last_processed_block}, current: {current_block})"
                        )

                    await self._scan_blocks(self.last_processed_block + 1, current_block)
                    self.last_processed_block = current_block

                    # Log catch-up status
                    new_blocks_behind = self.w3.eth.block_number - self.last_processed_block
                    if new_blocks_behind == 0:
                        logger.debug(f"✅ Caught up - no lag")
                    elif new_blocks_behind < blocks_behind:
                        logger.debug(
                            f"⚡ Catching up - now {new_blocks_behind} blocks behind (was {blocks_behind})"
                        )

                # Adaptive sleep based on lag, but respect rate limits
                if blocks_behind > 50:
                    # Very behind: faster catch-up but still respect rate limits (min 0.5s)
                    await asyncio.sleep(max(0.5, self.poll_interval / 3))
                elif blocks_behind > 20:
                    # Moderately behind: reduced sleep but not too aggressive
                    await asyncio.sleep(max(1.0, self.poll_interval / 2))
                elif blocks_behind > 5:
                    # Slightly behind: moderate sleep reduction
                    await asyncio.sleep(max(1.5, self.poll_interval * 0.75))
                else:
                    # Caught up or minimal lag: use normal poll interval to avoid rate limiting
                    await asyncio.sleep(self.poll_interval)

            except KeyboardInterrupt:
                logger.info("⏹️  Relayer stopped by user")
                self.is_running = False
                break
            except Exception as e:
                error_str = str(e).lower()
                # Check for rate limiting indicators
                is_rate_limit = any(
                    indicator in error_str
                    for indicator in [
                        "rate limit",
                        "too many requests",
                        "429",
                        "throttle",
                        "quota exceeded",
                    ]
                )

                if is_rate_limit:
                    logger.warning(
                        f"⚠️  Rate limit detected: {e}. Increasing poll interval temporarily."
                    )
                    # Exponential backoff on rate limiting
                    await asyncio.sleep(self.poll_interval * 2)
                else:
                    logger.error(f"❌ Error in relayer loop: {e}", exc_info=True)
                    # Normal error: use poll interval
                    await asyncio.sleep(self.poll_interval)

    def get_status(self) -> Dict[str, Any]:
        """Get relayer status for health checks."""
        try:
            current_block = self.w3.eth.block_number
            return {
                "status": "healthy" if self.is_running else "stopped",
                "is_running": self.is_running,
                "last_processed_block": self.last_processed_block,
                "current_block": current_block,
                "blocks_behind": current_block - self.last_processed_block,
                "events_processed": self.events_processed,
                "factory_address": self.factory_address,
                "chain_id": self.w3.eth.chain_id,
                "pubsub_topic": self.pubsub_topic,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "is_running": self.is_running,
            }


# Flask routes for Cloud Run Service
@app.route("/", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "blockchain-event-relayer"}), 200


@app.route("/health", methods=["GET"])
def health_check():
    """Detailed health check with relayer status."""
    global relayer_instance
    if relayer_instance:
        status = relayer_instance.get_status()
        return jsonify(status), 200
    return jsonify({"status": "starting", "message": "Relayer not yet initialized"}), 200


@app.route("/status", methods=["GET"])
def status():
    """Detailed status endpoint."""
    global relayer_instance
    if relayer_instance:
        status = relayer_instance.get_status()
        return jsonify(status), 200
    return jsonify({"status": "not_initialized"}), 503


@app.route("/admin/set-start-block", methods=["POST"])
def set_start_block():
    """
    Admin endpoint to set the start block for the relayer.

    This allows resetting the relayer to start from a specific block without redeployment.
    Useful for:
    - Skipping old blocks during testing
    - Fast-forwarding to recent blocks
    - Resetting after fixing issues

    Request Body:
        {
            "start_block": <block_number>,
            "admin_secret": "<optional_secret>"  # If ADMIN_SECRET env var is set
        }

    Returns:
        Updated relayer status with new start block
    """
    global relayer_instance

    if not relayer_instance:
        return jsonify({"error": "Relayer not initialized"}), 503

    # Get request data
    data = request.get_json()
    if not data or "start_block" not in data:
        return jsonify({"error": "Missing 'start_block' in request body"}), 400

    # Check admin secret if configured
    admin_secret = os.getenv("ADMIN_SECRET")
    if admin_secret:
        provided_secret = data.get("admin_secret")
        if provided_secret != admin_secret:
            logger.warning("⚠️ Unauthorized admin endpoint access attempt")
            return jsonify({"error": "Unauthorized"}), 403

    # Validate block number
    try:
        new_start_block = int(data["start_block"])
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid block number"}), 400

    # Validate block is not in the future
    try:
        current_block = relayer_instance.w3.eth.block_number
        if new_start_block > current_block:
            return (
                jsonify(
                    {
                        "error": f"Block number {new_start_block} is in the future (current: {current_block})"
                    }
                ),
                400,
            )
    except Exception as e:
        logger.error(f"Error fetching current block: {e}")
        return jsonify({"error": "Failed to validate block number"}), 500

    # Store old value for logging
    old_start_block = relayer_instance.last_processed_block

    # Update the last processed block (atomic operation)
    relayer_instance.last_processed_block = new_start_block

    logger.info(
        f"🔄 Start block updated via admin endpoint: "
        f"{old_start_block} → {new_start_block} "
        f"(skipped {new_start_block - old_start_block} blocks)"
    )

    # Return updated status
    status = relayer_instance.get_status()
    status["admin_action"] = {
        "action": "set_start_block",
        "old_block": old_start_block,
        "new_block": new_start_block,
        "blocks_skipped": new_start_block - old_start_block,
    }

    return jsonify(status), 200


def run_relayer_loop(relayer: BlockchainEventRelayer):
    """Run the relayer event loop in a separate thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(relayer.run())


async def initialize_relayer():
    """Initialize and start the relayer in background thread."""
    global relayer_instance

    # Load configuration from environment
    rpc_url = os.getenv("RPC_URL") or os.getenv("ETH_RPC_URL")  # Support both names
    gcp_project = os.getenv("PUBSUB_PROJECT_ID") or os.getenv("GCP_PROJECT", "fusion-prime")
    pubsub_topic = os.getenv("PUBSUB_TOPIC_ID") or os.getenv("PUBSUB_TOPIC", "settlement.events.v1")
    poll_interval = int(
        os.getenv("RELAYER_POLL_INTERVAL") or os.getenv("POLL_INTERVAL", "3")
    )  # Default 3s to avoid rate limiting
    batch_size = int(os.getenv("RELAYER_BATCH_SIZE") or "100")  # Default batch size
    start_block = os.getenv("START_BLOCK")

    # Validate configuration
    if not rpc_url:
        logger.error("❌ RPC_URL or ETH_RPC_URL environment variable is required")
        sys.exit(1)

    # Load contract resources using Contract Registry or fallback
    factory_address = None
    factory_abi = None

    if CONTRACT_REGISTRY_AVAILABLE:
        try:
            logger.info("Using Contract Registry for contract resources")
            registry = ContractRegistry()
            factory_address = registry.get_contract_address("EscrowFactory")
            factory_abi = registry.get_contract_abi("EscrowFactory")
            logger.info("✅ Loaded contract resources from Contract Registry")
        except Exception as e:
            logger.warning(f"Contract Registry failed: {e}")
            logger.info("Falling back to environment variables")

    # Fallback to environment variables if Contract Registry not available or failed
    if not factory_address or not factory_abi:
        factory_address = os.getenv("ESCROW_FACTORY_ADDRESS") or os.getenv("CONTRACT_ADDRESS")
        factory_abi_path = (
            os.getenv("ESCROW_FACTORY_ABI_PATH") or "/app/contracts/EscrowFactory.json"
        )

        if not factory_address:
            logger.error(
                "❌ ESCROW_FACTORY_ADDRESS or CONTRACT_ADDRESS environment variable is required"
            )
            sys.exit(1)

        # Load ABI from file (default to local path if env var not set)
        logger.info(f"Loading ABI from file: {factory_abi_path}")
        try:
            with open(factory_abi_path, "r") as f:
                contract_json = json.load(f)
                # Handle both {"abi": [...]} and [...] formats
                if isinstance(contract_json, list):
                    factory_abi = contract_json
                else:
                    factory_abi = contract_json.get("abi", contract_json)
        except FileNotFoundError:
            logger.error(f"❌ ABI file not found: {factory_abi_path}")
            sys.exit(1)

    # Load Escrow ABI for monitoring individual escrow contracts
    escrow_abi = None
    if CONTRACT_REGISTRY_AVAILABLE:
        try:
            escrow_abi = registry.get_contract_abi("Escrow")
            logger.info("✅ Loaded Escrow ABI from Contract Registry")
        except Exception as e:
            logger.warning(f"Failed to load Escrow ABI from Contract Registry: {e}")

    # Fallback to file if Contract Registry not available or failed
    if not escrow_abi:
        escrow_abi_path = os.getenv("ESCROW_ABI_PATH") or "/app/contracts/Escrow.json"
        logger.info(f"Loading Escrow ABI from file: {escrow_abi_path}")
        try:
            with open(escrow_abi_path, "r") as f:
                escrow_json = json.load(f)
                # Handle both {"abi": [...]} and [...] formats
                if isinstance(escrow_json, list):
                    escrow_abi = escrow_json
                else:
                    escrow_abi = escrow_json.get("abi", escrow_json)
            logger.info("✅ Loaded Escrow ABI from file")
        except FileNotFoundError as e:
            logger.error(f"❌ CRITICAL: Escrow ABI file not found: {escrow_abi_path}")
            logger.error(
                "❌ Escrow lifecycle events (Approved, Released, Refunded) will NOT be monitored!"
            )
            logger.error("❌ Escrows will be registered but monitoring will be disabled!")
        except Exception as e:
            logger.error(f"❌ CRITICAL: Failed to load Escrow ABI: {e}")
            logger.error("❌ Escrow lifecycle events will NOT be monitored!")

    # Initialize relayer
    relayer_instance = BlockchainEventRelayer(
        rpc_url=rpc_url,
        factory_address=factory_address,
        factory_abi=factory_abi,
        gcp_project=gcp_project,
        pubsub_topic=pubsub_topic,
        poll_interval=poll_interval,
        start_block=int(start_block) if start_block else None,
        escrow_abi=escrow_abi,
        batch_size=batch_size,
    )

    # Start relayer in background thread
    relayer_thread = threading.Thread(
        target=run_relayer_loop, args=(relayer_instance,), daemon=True
    )
    relayer_thread.start()
    logger.info("✅ Relayer thread started")

    return relayer_instance


if __name__ == "__main__":
    # Initialize relayer asynchronously
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(initialize_relayer())

    # Get port from environment (Cloud Run sets PORT)
    port = int(os.getenv("PORT", "8080"))

    # Start Flask server (blocking)
    logger.info(f"🚀 Starting Flask server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
