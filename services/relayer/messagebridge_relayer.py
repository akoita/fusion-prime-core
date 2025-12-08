"""
MessageBridge Relayer Service

Monitors MessageSent events on both chains and executes messages on destination chains.
Simple, focused relayer for cross-chain vault synchronization.
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Set

from dotenv import load_dotenv
from web3 import Web3
from web3.contract import Contract
from web3.exceptions import ContractLogicError

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# MessageBridge ABI (just the functions we need)
MESSAGE_BRIDGE_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "messageId", "type": "bytes32"},
            {"indexed": True, "internalType": "uint64", "name": "sourceChainId", "type": "uint64"},
            {"indexed": True, "internalType": "uint64", "name": "destChainId", "type": "uint64"},
            {"indexed": False, "internalType": "address", "name": "sender", "type": "address"},
            {"indexed": False, "internalType": "address", "name": "recipient", "type": "address"},
            {"indexed": False, "internalType": "bytes", "name": "payload", "type": "bytes"},
        ],
        "name": "MessageSent",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "messageId", "type": "bytes32"},
            {"indexed": True, "internalType": "uint64", "name": "sourceChainId", "type": "uint64"},
            {"indexed": True, "internalType": "uint64", "name": "destChainId", "type": "uint64"},
            {"indexed": False, "internalType": "address", "name": "recipient", "type": "address"},
            {"indexed": False, "internalType": "bytes", "name": "payload", "type": "bytes"},
        ],
        "name": "MessageExecuted",
        "type": "event",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "messageId", "type": "bytes32"},
            {"internalType": "uint64", "name": "sourceChainId", "type": "uint64"},
            {"internalType": "address", "name": "sender", "type": "address"},
            {"internalType": "address", "name": "recipient", "type": "address"},
            {"internalType": "bytes", "name": "payload", "type": "bytes"},
        ],
        "name": "executeMessage",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


class MessageBridgeRelayer:
    """Relays cross-chain messages between MessageBridge contracts."""

    def __init__(self):
        """Initialize the relayer with configuration from environment."""
        # Load configuration
        self.sepolia_rpc = os.getenv("SEPOLIA_RPC_URL")
        self.amoy_rpc = os.getenv("AMOY_RPC_URL")
        self.sepolia_bridge = os.getenv("SEPOLIA_MESSAGE_BRIDGE")
        self.amoy_bridge = os.getenv("AMOY_MESSAGE_BRIDGE")
        self.relayer_key = os.getenv("RELAYER_PRIVATE_KEY")

        # Optional: Start from specific blocks (for backfilling historical messages)
        self.sepolia_start_block = os.getenv("SEPOLIA_START_BLOCK")
        self.amoy_start_block = os.getenv("AMOY_START_BLOCK")

        if not all(
            [
                self.sepolia_rpc,
                self.amoy_rpc,
                self.sepolia_bridge,
                self.amoy_bridge,
                self.relayer_key,
            ]
        ):
            raise ValueError("Missing required environment variables. Check .env file.")

        # Initialize Web3 connections
        logger.info("Initializing Web3 connections...")
        self.sepolia_w3 = Web3(Web3.HTTPProvider(self.sepolia_rpc))
        self.amoy_w3 = Web3(Web3.HTTPProvider(self.amoy_rpc))

        if not self.sepolia_w3.is_connected():
            raise ConnectionError(f"Failed to connect to Sepolia: {self.sepolia_rpc}")
        if not self.amoy_w3.is_connected():
            raise ConnectionError(f"Failed to connect to Amoy: {self.amoy_rpc}")

        logger.info(f"✅ Connected to Sepolia (Chain ID: {self.sepolia_w3.eth.chain_id})")
        logger.info(f"✅ Connected to Amoy (Chain ID: {self.amoy_w3.eth.chain_id})")

        # Set up relayer account
        self.relayer_account = self.sepolia_w3.eth.account.from_key(self.relayer_key)
        logger.info(f"🔑 Relayer address: {self.relayer_account.address}")

        # Check balances
        sepolia_balance = self.sepolia_w3.eth.get_balance(self.relayer_account.address)
        amoy_balance = self.amoy_w3.eth.get_balance(self.relayer_account.address)
        logger.info(f"💰 Sepolia balance: {self.sepolia_w3.from_wei(sepolia_balance, 'ether')} ETH")
        logger.info(f"💰 Amoy balance: {self.amoy_w3.from_wei(amoy_balance, 'ether')} POL")

        # Initialize contracts
        self.sepolia_bridge_contract = self.sepolia_w3.eth.contract(
            address=Web3.to_checksum_address(self.sepolia_bridge), abi=MESSAGE_BRIDGE_ABI
        )
        self.amoy_bridge_contract = self.amoy_w3.eth.contract(
            address=Web3.to_checksum_address(self.amoy_bridge), abi=MESSAGE_BRIDGE_ABI
        )

        logger.info(f"📝 Sepolia MessageBridge: {self.sepolia_bridge}")
        logger.info(f"📝 Amoy MessageBridge: {self.amoy_bridge}")

        # Track processed messages
        self.processed_messages = set()

        # Polling configuration
        self.poll_interval = int(os.getenv("POLL_INTERVAL", "5"))  # 5 seconds default
        self.sepolia_last_block = None
        self.amoy_last_block = None

        self.is_running = False
        self.messages_relayed = 0

        # Persistent state file
        self.state_file = Path(__file__).parent / "relayer_state.json"
        self.load_state()

    def load_state(self):
        """Load persisted state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    state = json.load(f)
                    if self.sepolia_last_block is None:
                        self.sepolia_last_block = state.get("sepolia_block")
                    if self.amoy_last_block is None:
                        self.amoy_last_block = state.get("amoy_block")
                    self.processed_messages = set(state.get("processed_messages", []))
                    logger.info(
                        f"📂 Loaded state: Sepolia={self.sepolia_last_block}, Amoy={self.amoy_last_block}, Messages={len(self.processed_messages)}"
                    )
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
                # Initialize empty state if load fails
                if self.sepolia_last_block is None:
                    self.sepolia_last_block = self.sepolia_w3.eth.block_number
                if self.amoy_last_block is None:
                    self.amoy_last_block = self.amoy_w3.eth.block_number
        else:
            logger.info("No previous state found, starting fresh")

    def save_state(self):
        """Save current state to disk."""
        try:
            state = {
                "sepolia_block": self.sepolia_last_block,
                "amoy_block": self.amoy_last_block,
                "processed_messages": list(self.processed_messages),
            }
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
            logger.debug(f"💾 State saved to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def execute_message_on_chain(
        self,
        w3: Web3,
        bridge_contract: Contract,
        message_id: bytes,
        source_chain_id: int,
        sender: str,
        recipient: str,
        payload: bytes,
        chain_name: str,
    ) -> bool:
        """Execute a message on the destination chain."""
        try:
            # Build transaction
            tx = bridge_contract.functions.executeMessage(
                message_id,
                source_chain_id,
                Web3.to_checksum_address(sender),
                Web3.to_checksum_address(recipient),
                payload,
            ).build_transaction(
                {
                    "from": self.relayer_account.address,
                    "nonce": w3.eth.get_transaction_count(self.relayer_account.address),
                    "gas": 500000,  # Fixed gas limit
                    "gasPrice": w3.eth.gas_price,
                }
            )

            # Sign and send
            signed_tx = w3.eth.account.sign_transaction(tx, self.relayer_key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

            logger.info(f"⏳ Executing message {message_id.hex()} on {chain_name}...")
            logger.info(f"   TX: {tx_hash.hex()}")

            # Wait for receipt
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt["status"] == 1:
                logger.info(f"✅ Message {message_id.hex()} executed on {chain_name}")
                logger.info(f"   Block: {receipt['blockNumber']}, Gas used: {receipt['gasUsed']}")
                return True
            else:
                logger.error(f"❌ Message execution failed on {chain_name}")
                return False

        except ContractLogicError as e:
            # Message might already be executed
            if "MessageAlreadyExecuted" in str(e):
                logger.warning(f"⚠️  Message {message_id.hex()} already executed on {chain_name}")
                return True
            else:
                logger.error(f"❌ Contract error executing message on {chain_name}: {e}")
                return False
        except Exception as e:
            logger.error(f"❌ Error executing message on {chain_name}: {e}")
            return False

    def process_sepolia_events(self, from_block: int, to_block: int):
        """Process MessageSent events from Sepolia."""
        try:
            event_filter = self.sepolia_bridge_contract.events.MessageSent.create_filter(
                from_block=from_block, to_block=to_block
            )

            events = event_filter.get_all_entries()

            for event in events:
                message_id = event["args"]["messageId"]

                # Skip if already processed
                if message_id in self.processed_messages:
                    continue

                dest_chain_id = event["args"]["destChainId"]

                # Only process messages destined for Amoy
                if dest_chain_id != 80002:  # Amoy chain ID
                    continue

                logger.info(f"\n{'='*60}")
                logger.info(f"📬 New message from Sepolia")
                logger.info(f"   Message ID: {message_id.hex()}")
                logger.info(f"   Sender: {event['args']['sender']}")
                logger.info(f"   Recipient: {event['args']['recipient']}")
                logger.info(f"   Destination: Amoy")
                logger.info(f"{'='*60}\n")

                # Execute on Amoy
                success = self.execute_message_on_chain(
                    self.amoy_w3,
                    self.amoy_bridge_contract,
                    message_id,
                    event["args"]["sourceChainId"],
                    event["args"]["sender"],
                    event["args"]["recipient"],
                    event["args"]["payload"],
                    "Amoy",
                )

                if success:
                    self.processed_messages.add(message_id)
                    self.messages_relayed += 1

                    # Save state every 10 messages
                    if self.messages_relayed % 10 == 0:
                        self.save_state()

        except Exception as e:
            logger.error(f"Error processing Sepolia events: {e}")

    def process_amoy_events(self, from_block: int, to_block: int):
        """Process MessageSent events from Amoy."""
        try:
            event_filter = self.amoy_bridge_contract.events.MessageSent.create_filter(
                from_block=from_block, to_block=to_block
            )

            events = event_filter.get_all_entries()

            for event in events:
                message_id = event["args"]["messageId"]

                # Skip if already processed
                if message_id in self.processed_messages:
                    continue

                dest_chain_id = event["args"]["destChainId"]

                # Only process messages destined for Sepolia
                if dest_chain_id != 11155111:  # Sepolia chain ID
                    continue

                logger.info(f"\n{'='*60}")
                logger.info(f"📬 New message from Amoy")
                logger.info(f"   Message ID: {message_id.hex()}")
                logger.info(f"   Sender: {event['args']['sender']}")
                logger.info(f"   Recipient: {event['args']['recipient']}")
                logger.info(f"   Destination: Sepolia")
                logger.info(f"{'='*60}\n")

                # Execute on Sepolia
                success = self.execute_message_on_chain(
                    self.sepolia_w3,
                    self.sepolia_bridge_contract,
                    message_id,
                    event["args"]["sourceChainId"],
                    event["args"]["sender"],
                    event["args"]["recipient"],
                    event["args"]["payload"],
                    "Sepolia",
                )

                if success:
                    self.processed_messages.add(message_id)
                    self.messages_relayed += 1

                    # Save state every 10 messages
                    if self.messages_relayed % 10 == 0:
                        self.save_state()

        except Exception as e:
            logger.error(f"Error processing Amoy events: {e}")

    def run(self):
        """Main relayer loop."""
        logger.info("\n" + "=" * 60)
        logger.info("🚀 MessageBridge Relayer Starting")
        logger.info("=" * 60 + "\n")

        self.is_running = True

        # Get current blocks (use environment variable if provided, otherwise use current)
        if self.sepolia_start_block:
            self.sepolia_last_block = int(self.sepolia_start_block)
            logger.info(f"📍 Starting from Sepolia block: {self.sepolia_last_block} (from env)")
        else:
            self.sepolia_last_block = self.sepolia_w3.eth.block_number
            logger.info(f"📍 Starting from Sepolia block: {self.sepolia_last_block} (current)")

        if self.amoy_start_block:
            self.amoy_last_block = int(self.amoy_start_block)
            logger.info(f"📍 Starting from Amoy block: {self.amoy_last_block} (from env)")
        else:
            self.amoy_last_block = self.amoy_w3.eth.block_number
            logger.info(f"📍 Starting from Amoy block: {self.amoy_last_block} (current)")
        logger.info(f"⏱️  Poll interval: {self.poll_interval} seconds\n")

        try:
            while self.is_running:
                # Get current blocks
                sepolia_current = self.sepolia_w3.eth.block_number
                amoy_current = self.amoy_w3.eth.block_number

                # Process Sepolia events
                if sepolia_current > self.sepolia_last_block:
                    logger.debug(
                        f"Checking Sepolia blocks {self.sepolia_last_block + 1} to {sepolia_current}"
                    )
                    self.process_sepolia_events(self.sepolia_last_block + 1, sepolia_current)
                    self.sepolia_last_block = sepolia_current

                # Process Amoy events
                if amoy_current > self.amoy_last_block:
                    logger.debug(
                        f"Checking Amoy blocks {self.amoy_last_block + 1} to {amoy_current}"
                    )
                    self.process_amoy_events(self.amoy_last_block + 1, amoy_current)
                    self.amoy_last_block = amoy_current

                # Log status every 10 polls
                if int(time.time()) % 60 == 0:
                    logger.info(
                        f"📊 Status: {self.messages_relayed} messages relayed | "
                        f"Sepolia block: {sepolia_current} | Amoy block: {amoy_current}"
                    )

                # Wait before next poll
                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            logger.info("\n⏹️  Shutting down gracefully...")
            self.is_running = False
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")
            raise
        finally:
            # Save state before exiting
            self.save_state()
            logger.info("💾 Final state saved to disk")


def main():
    """Entry point for the relayer service."""
    try:
        relayer = MessageBridgeRelayer()
        relayer.run()
    except Exception as e:
        logger.error(f"❌ Failed to start relayer: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
