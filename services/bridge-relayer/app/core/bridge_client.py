"""Bridge client for interacting with bridge contracts."""

import logging
import os
from typing import Dict, Optional

from eth_account import Account
from web3 import Web3

logger = logging.getLogger(__name__)


class BridgeClient:
    """Client for interacting with bridge contracts."""

    def __init__(self):
        """Initialize bridge client with configuration."""
        self.config = self._load_config()
        self.web3_clients: Dict[int, Web3] = {}
        self._init_web3_clients()

    def _load_config(self) -> Dict:
        """Load bridge configuration."""
        return {
            "sepolia": {
                "chain_id": 11155111,
                "rpc_url": os.getenv("SEPOLIA_RPC_URL", "https://rpc.sepolia.org"),
                "registry": os.getenv("SEPOLIA_REGISTRY_ADDRESS"),
                "message_bridge": os.getenv("SEPOLIA_MESSAGE_BRIDGE_ADDRESS"),
                "native_bridge": os.getenv("SEPOLIA_NATIVE_BRIDGE_ADDRESS"),
                "erc20_bridge": os.getenv("SEPOLIA_ERC20_BRIDGE_ADDRESS"),
            },
            "amoy": {
                "chain_id": 80002,
                "rpc_url": os.getenv("AMOY_RPC_URL", "https://rpc-amoy.polygon.technology"),
                "registry": os.getenv("AMOY_REGISTRY_ADDRESS"),
                "message_bridge": os.getenv("AMOY_MESSAGE_BRIDGE_ADDRESS"),
                "native_bridge": os.getenv("AMOY_NATIVE_BRIDGE_ADDRESS"),
                "erc20_bridge": os.getenv("AMOY_ERC20_BRIDGE_ADDRESS"),
            },
        }

    def _init_web3_clients(self):
        """Initialize Web3 clients for each chain."""
        for chain_name, chain_config in self.config.items():
            w3 = Web3(Web3.HTTPProvider(chain_config["rpc_url"]))
            self.web3_clients[chain_config["chain_id"]] = w3
            logger.info(f"Initialized Web3 client for {chain_name}")

    def get_web3(self, chain_id: int) -> Web3:
        """Get Web3 client for chain."""
        if chain_id not in self.web3_clients:
            raise ValueError(f"Chain ID {chain_id} not configured")
        return self.web3_clients[chain_id]

    async def send_message(
        self,
        source_chain_id: int,
        dest_chain_id: int,
        sender: str,
        recipient: str,
        payload: bytes,
    ) -> str:
        """Send a cross-chain message."""
        w3 = self.get_web3(source_chain_id)
        chain_config = self._get_chain_config(source_chain_id)
        bridge_address = chain_config["message_bridge"]

        # Load contract ABI (simplified - in production, load from JSON)
        # For now, we'll use a basic interface
        contract = w3.eth.contract(address=bridge_address, abi=self._get_message_bridge_abi())

        # Build transaction
        tx = contract.functions.sendMessage(dest_chain_id, recipient, payload).build_transaction(
            {
                "from": sender,
                "nonce": w3.eth.get_transaction_count(sender),
                "gas": 200000,
                "gasPrice": w3.eth.gas_price,
            }
        )

        # Sign and send (in production, use relayer's private key)
        private_key = os.getenv("RELAYER_PRIVATE_KEY")
        if not private_key:
            raise ValueError("RELAYER_PRIVATE_KEY not set")

        account = Account.from_key(private_key)
        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        # Wait for receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        # Extract message ID from event
        # In production, parse MessageSent event
        message_id = receipt.transactionHash.hex()

        return message_id

    async def send_native_transfer(
        self,
        dest_chain_id: int,
        recipient: str,
        amount: int,
    ) -> str:
        """Send a native currency transfer."""
        # Implementation similar to send_message
        # Uses native_bridge contract
        raise NotImplementedError("Native transfer not yet implemented")

    async def send_erc20_transfer(
        self,
        dest_chain_id: int,
        token: str,
        recipient: str,
        amount: int,
    ) -> str:
        """Send an ERC20 token transfer."""
        # Implementation similar to send_message
        # Uses erc20_bridge contract
        raise NotImplementedError("ERC20 transfer not yet implemented")

    async def get_message(self, message_id: str) -> Dict:
        """Get message status."""
        # Query message from contract
        raise NotImplementedError("Get message not yet implemented")

    async def get_native_transfer(self, transfer_id: str) -> Dict:
        """Get native transfer status."""
        raise NotImplementedError("Get native transfer not yet implemented")

    async def get_erc20_transfer(self, transfer_id: str) -> Dict:
        """Get ERC20 transfer status."""
        raise NotImplementedError("Get ERC20 transfer not yet implemented")

    def _get_chain_config(self, chain_id: int) -> Dict:
        """Get chain configuration."""
        for chain_name, config in self.config.items():
            if config["chain_id"] == chain_id:
                return config
        raise ValueError(f"Chain ID {chain_id} not configured")

    def _get_message_bridge_abi(self) -> list:
        """Get MessageBridge ABI (simplified)."""
        # In production, load from JSON file
        return [
            {
                "inputs": [
                    {"name": "destChainId", "type": "uint64"},
                    {"name": "recipient", "type": "address"},
                    {"name": "payload", "type": "bytes"},
                ],
                "name": "sendMessage",
                "outputs": [{"name": "messageId", "type": "bytes32"}],
                "stateMutability": "nonpayable",
                "type": "function",
            }
        ]
