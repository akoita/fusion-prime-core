"""
Update Arbiter Addresses for Existing Escrows

Fetches arbiter addresses from deployed escrow contracts and updates the database.
"""

import argparse
import logging
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from infrastructure.db import Escrow, get_db_session
from web3 import Web3

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


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


def update_arbiters(rpc_url: str, batch_size: int = 100):
    """Update arbiter addresses for all escrows in database."""
    # Connect to blockchain
    logger.info(f"Connecting to blockchain: {rpc_url}")
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        logger.error("Failed to connect to blockchain")
        return False

    logger.info(f"✅ Connected to blockchain (Chain ID: {w3.eth.chain_id})")

    # Get all escrows
    with get_db_session() as session:
        escrows = session.query(Escrow).all()
        total = len(escrows)
        logger.info(f"Found {total} escrows to update")

        updated = 0
        skipped = 0

        for i, escrow in enumerate(escrows, 1):
            # Skip if already has non-zero arbiter
            if escrow.arbiter_address != "0x" + "0" * 40:
                skipped += 1
                continue

            # Fetch arbiter from contract
            logger.info(f"[{i}/{total}] Fetching arbiter for {escrow.escrow_address}")
            arbiter = get_arbiter_from_escrow(w3, escrow.escrow_address)

            if arbiter != "0x" + "0" * 40:
                escrow.arbiter_address = arbiter
                updated += 1
                logger.info(f"  ✅ Updated arbiter to {arbiter}")
            else:
                logger.info(f"  ℹ️  No arbiter (remains 0x000...)")

            # Commit in batches
            if i % batch_size == 0:
                session.commit()
                logger.info(f"  💾 Committed batch at {i}/{total}")

        # Final commit
        session.commit()

        logger.info(f"\n✅ Update completed:")
        logger.info(f"   Total escrows: {total}")
        logger.info(f"   Updated: {updated}")
        logger.info(f"   Skipped (already set): {skipped}")
        logger.info(f"   No arbiter: {total - updated - skipped}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Update arbiter addresses for existing escrows")
    parser.add_argument(
        "--rpc-url",
        default="https://spectrum-01.simplystaking.xyz/Y2J1emtmcWQtMDEtMjJjN2I0YTE/6CuZK_q3OlibSg/ethereum/testnet/",
        help="Blockchain RPC URL",
    )
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for commits")

    args = parser.parse_args()

    logger.info("🚀 Starting arbiter update...")
    logger.info(f"RPC URL: {args.rpc_url}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info("")

    success = update_arbiters(args.rpc_url, args.batch_size)

    if success:
        logger.info("✅ Arbiter update completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Arbiter update failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
