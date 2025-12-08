"""Bridge monitor for watching events and relaying messages."""

import asyncio
import logging
from typing import Dict, Optional

from web3 import Web3
from web3.middleware import geth_poa_middleware

logger = logging.getLogger(__name__)


class BridgeMonitor:
    """Monitors bridge events and relays messages between chains."""

    def __init__(self):
        """Initialize bridge monitor."""
        self.running = False
        self.tasks = []
        self.config = self._load_config()
        self.web3_clients: Dict[int, Web3] = {}
        self._init_web3_clients()

    def _load_config(self) -> Dict:
        """Load bridge configuration."""
        import os

        return {
            "sepolia": {
                "chain_id": 11155111,
                "rpc_url": os.getenv("SEPOLIA_RPC_URL", "https://rpc.sepolia.org"),
                "message_bridge": os.getenv("SEPOLIA_MESSAGE_BRIDGE_ADDRESS"),
                "native_bridge": os.getenv("SEPOLIA_NATIVE_BRIDGE_ADDRESS"),
                "erc20_bridge": os.getenv("SEPOLIA_ERC20_BRIDGE_ADDRESS"),
            },
            "amoy": {
                "chain_id": 80002,
                "rpc_url": os.getenv("AMOY_RPC_URL", "https://rpc-amoy.polygon.technology"),
                "message_bridge": os.getenv("AMOY_MESSAGE_BRIDGE_ADDRESS"),
                "native_bridge": os.getenv("AMOY_NATIVE_BRIDGE_ADDRESS"),
                "erc20_bridge": os.getenv("AMOY_ERC20_BRIDGE_ADDRESS"),
            },
        }

    def _init_web3_clients(self):
        """Initialize Web3 clients for each chain."""
        for chain_name, chain_config in self.config.items():
            w3 = Web3(Web3.HTTPProvider(chain_config["rpc_url"]))
            # Add POA middleware for some chains
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            self.web3_clients[chain_config["chain_id"]] = w3
            logger.info(f"Initialized Web3 client for {chain_name}")

    async def start(self):
        """Start monitoring bridge events."""
        if self.running:
            logger.warning("Bridge monitor already running")
            return

        self.running = True
        logger.info("Starting bridge monitor...")

        # Start monitoring tasks for each chain
        for chain_name, chain_config in self.config.items():
            task = asyncio.create_task(self._monitor_chain(chain_config["chain_id"], chain_name))
            self.tasks.append(task)

        logger.info("Bridge monitor started")

    async def stop(self):
        """Stop monitoring bridge events."""
        if not self.running:
            return

        self.running = False
        logger.info("Stopping bridge monitor...")

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)

        logger.info("Bridge monitor stopped")

    async def _monitor_chain(self, chain_id: int, chain_name: str):
        """Monitor events on a specific chain."""
        w3 = self.web3_clients[chain_id]
        chain_config = self.config[chain_name.lower()]

        logger.info(f"Starting event monitoring for {chain_name} (chain ID: {chain_id})")

        # Get latest block
        latest_block = w3.eth.block_number
        from_block = latest_block

        while self.running:
            try:
                # Get current block
                current_block = w3.eth.block_number

                if current_block > from_block:
                    # Process new blocks
                    logger.info(
                        f"Processing blocks {from_block} to {current_block} on {chain_name}"
                    )

                    # Monitor MessageSent events
                    await self._process_message_events(
                        w3, chain_id, chain_config["message_bridge"], from_block, current_block
                    )

                    # Monitor NativeLocked events
                    await self._process_native_events(
                        w3, chain_id, chain_config["native_bridge"], from_block, current_block
                    )

                    # Monitor TokenLocked events
                    await self._process_erc20_events(
                        w3, chain_id, chain_config["erc20_bridge"], from_block, current_block
                    )

                    from_block = current_block + 1

                # Wait before next check
                await asyncio.sleep(5)  # Check every 5 seconds

            except Exception as e:
                logger.error(f"Error monitoring {chain_name}: {e}")
                await asyncio.sleep(10)  # Wait longer on error

    async def _process_message_events(
        self, w3: Web3, chain_id: int, bridge_address: str, from_block: int, to_block: int
    ):
        """Process MessageSent events."""
        # In production, parse events and relay to destination chain
        logger.debug(f"Processing message events on chain {chain_id}")

    async def _process_native_events(
        self, w3: Web3, chain_id: int, bridge_address: str, from_block: int, to_block: int
    ):
        """Process NativeLocked events."""
        logger.debug(f"Processing native events on chain {chain_id}")

    async def _process_erc20_events(
        self, w3: Web3, chain_id: int, bridge_address: str, from_block: int, to_block: int
    ):
        """Process TokenLocked events."""
        logger.debug(f"Processing ERC20 events on chain {chain_id}")
