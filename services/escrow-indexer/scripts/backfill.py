"""
Backfill Script for Escrow Indexer

Scans the blockchain for historical EscrowDeployed events and indexes them.
This is useful for:
- Initial setup when the indexer wasn't running
- Re-indexing after database loss
- Catching up on missed events

Usage:
    python scripts/backfill.py [--from-block BLOCK] [--to-block BLOCK] [--batch-size SIZE]
"""

import argparse
import logging
import os
import sys
from typing import List

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.event_processor import EscrowEventProcessor
from infrastructure.db import Escrow, EscrowEvent, get_db_session
from web3 import Web3

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_factory_contract(w3: Web3, factory_address: str):
    """Get EscrowFactory contract instance."""
    # EscrowDeployed event ABI
    event_abi = {
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

    # Minimal ABI just for event
    factory_abi = [event_abi]

    return w3.eth.contract(address=Web3.to_checksum_address(factory_address), abi=factory_abi)


def get_arbiter_from_escrow(w3: Web3, escrow_address: str) -> str:
    """Fetch arbiter address from deployed escrow contract."""
    try:
        # Minimal ABI to read arbiter() public getter
        escrow_abi = [
            {
                "inputs": [],
                "name": "arbiter",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function",
            }
        ]

        escrow = w3.eth.contract(address=Web3.to_checksum_address(escrow_address), abi=escrow_abi)
        arbiter = escrow.functions.arbiter().call()
        return arbiter.lower()
    except Exception as e:
        logger.warning(f"Failed to fetch arbiter for {escrow_address}: {e}")
        return "0x" + "0" * 40


def backfill_escrows(
    rpc_url: str,
    factory_address: str,
    from_block: int,
    to_block: int,
    batch_size: int = 1000,
    dry_run: bool = False,
):
    """
    Backfill escrows from blockchain events.

    Args:
        rpc_url: Blockchain RPC URL
        factory_address: EscrowFactory contract address
        from_block: Starting block number
        to_block: Ending block number (or 'latest')
        batch_size: Number of blocks to process per batch
        dry_run: If True, don't write to database
    """
    # Connect to blockchain
    logger.info(f"Connecting to blockchain: {rpc_url}")
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        logger.error("Failed to connect to blockchain")
        return False

    chain_id = w3.eth.chain_id
    logger.info(f"✅ Connected to blockchain (Chain ID: {chain_id})")

    # Get current block if to_block is 'latest'
    if to_block == "latest":
        to_block = w3.eth.block_number
        logger.info(f"Latest block: {to_block}")

    # Get contract
    factory = get_factory_contract(w3, factory_address)
    logger.info(f"EscrowFactory contract: {factory_address}")

    # Calculate total blocks
    total_blocks = to_block - from_block + 1
    logger.info(f"Scanning {total_blocks} blocks ({from_block} to {to_block})")

    # Process in batches
    events_found = 0
    events_processed = 0
    events_skipped = 0

    for batch_start in range(from_block, to_block + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, to_block)

        logger.info(f"Processing blocks {batch_start} to {batch_end}...")

        try:
            # Get EscrowDeployed events
            events = factory.events.EscrowDeployed.get_logs(
                fromBlock=batch_start, toBlock=batch_end
            )

            if events:
                logger.info(f"  Found {len(events)} EscrowDeployed events")
                events_found += len(events)

                # Process each event
                with get_db_session() as db:
                    processor = EscrowEventProcessor(db)

                    for event in events:
                        # Check if already indexed
                        escrow_address = event["args"]["escrow"].lower()
                        existing = (
                            db.query(Escrow).filter(Escrow.escrow_address == escrow_address).first()
                        )

                        if existing:
                            logger.debug(f"  ⏭️  Skipping {escrow_address} (already indexed)")
                            events_skipped += 1
                            continue

                        # Fetch arbiter from the deployed escrow contract
                        escrow_address = event["args"]["escrow"].lower()
                        arbiter = get_arbiter_from_escrow(w3, escrow_address)

                        # Convert event to format expected by processor
                        event_data = {
                            "escrow": escrow_address,
                            "payer": event["args"]["payer"].lower(),
                            "payee": event["args"]["payee"].lower(),
                            "arbiter": arbiter,
                            "amount": str(event["args"]["amount"]),
                            "releaseDelay": int(event["args"]["releaseDelay"]),
                            "approvalsRequired": int(event["args"]["approvalsRequired"]),
                            "transaction_hash": event["transactionHash"].hex(),
                            "block_number": event["blockNumber"],
                            "chain_id": chain_id,
                        }

                        if dry_run:
                            logger.info(f"  [DRY RUN] Would index: {escrow_address}")
                            events_processed += 1
                        else:
                            # Process event
                            success = processor.process_event("EscrowDeployed", event_data)
                            if success:
                                logger.info(f"  ✅ Indexed: {escrow_address}")
                                events_processed += 1
                            else:
                                logger.error(f"  ❌ Failed to index: {escrow_address}")

        except Exception as e:
            logger.error(f"Error processing batch {batch_start}-{batch_end}: {e}")
            continue

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("Backfill Summary:")
    logger.info(f"  Blocks scanned: {total_blocks}")
    logger.info(f"  Events found: {events_found}")
    logger.info(f"  Events indexed: {events_processed}")
    logger.info(f"  Events skipped (already indexed): {events_skipped}")
    logger.info("=" * 60)

    return True


def main():
    parser = argparse.ArgumentParser(description="Backfill escrow events from blockchain")

    parser.add_argument(
        "--rpc-url",
        default=os.getenv("RPC_URL", "https://sepolia.infura.io/v3/YOUR_KEY"),
        help="Blockchain RPC URL",
    )

    parser.add_argument(
        "--factory-address",
        default=os.getenv("ESCROW_FACTORY_ADDRESS", "0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914"),
        help="EscrowFactory contract address",
    )

    parser.add_argument(
        "--from-block", type=int, default=0, help="Starting block number (default: 0)"
    )

    parser.add_argument(
        "--to-block", default="latest", help="Ending block number or 'latest' (default: latest)"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Number of blocks to process per batch (default: 1000)",
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Perform a dry run without writing to database"
    )

    args = parser.parse_args()

    # Validate DATABASE_URL is set
    if not os.getenv("DATABASE_URL"):
        logger.error("DATABASE_URL environment variable is required")
        logger.error("Example: export DATABASE_URL=postgresql://user:pass@host:5432/escrow_indexer")
        return 1

    # Convert to_block to int if not 'latest'
    to_block = args.to_block
    if to_block != "latest":
        to_block = int(to_block)

    # Run backfill
    logger.info("🚀 Starting escrow backfill...")
    logger.info(f"RPC URL: {args.rpc_url}")
    logger.info(f"Factory: {args.factory_address}")
    logger.info(f"Blocks: {args.from_block} to {to_block}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("")

    success = backfill_escrows(
        rpc_url=args.rpc_url,
        factory_address=args.factory_address,
        from_block=args.from_block,
        to_block=to_block,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )

    if success:
        logger.info("✅ Backfill completed successfully")
        return 0
    else:
        logger.error("❌ Backfill failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
