"""Chainlink CCIP API client for monitoring cross-chain messages."""

import logging
import os
from typing import Dict, Optional

import httpx
from web3 import Web3

logger = logging.getLogger(__name__)

# CCIP Router ABI for querying message status
CCIP_ROUTER_ABI = [
    {
        "inputs": [{"internalType": "bytes32", "name": "messageId", "type": "bytes32"}],
        "name": "getMessageStatus",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "messageId", "type": "bytes32"}],
        "name": "getCommitment",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# CCIP Router addresses (testnet)
CCIP_ROUTER_ADDRESSES = {
    "ethereum": os.getenv("CCIP_ROUTER_ETH", "0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59"),
    "sepolia": os.getenv("CCIP_ROUTER_ETH", "0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59"),
    "polygon": os.getenv("CCIP_ROUTER_POLYGON", "0x1035CabC275068e0F4b745A29CEDf38E13aF41b1"),
    "amoy": os.getenv("CCIP_ROUTER_POLYGON", "0x1035CabC275068e0F4b745A29CEDf38E13aF41b1"),
    "arbitrum": os.getenv("CCIP_ROUTER_ARBITRUM", "0x88e492127709447a5AB4dA4a0d1861BAb2Be98e5"),
    "arbitrum-sepolia": os.getenv(
        "CCIP_ROUTER_ARBITRUM", "0x88e492127709447a5AB4dA4a0d1861BAb2Be98e5"
    ),
}

# CCIP Message Status enum (from Chainlink CCIP)
CCIP_MESSAGE_STATUS = {
    0: "Uninitialized",
    1: "InProgress",
    2: "Success",
    3: "Failure",
}


class CCIPClient:
    """Client for interacting with Chainlink CCIP APIs."""

    def __init__(self):
        # CCIP doesn't have a centralized API like AxelarScan
        # We'll need to query contracts directly or use Chainlink Functions
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_message_status(
        self, message_id: str, source_chain: str, destination_chain: str
    ) -> Optional[Dict]:
        """
        Get status of a CCIP message by querying the CCIP Router contract.

        CCIP doesn't provide a centralized API, so we query the Router contract
        directly on the destination chain to check message status.

        Args:
            message_id: CCIP message ID (bytes32)
            source_chain: Source chain name
            destination_chain: Destination chain name

        Returns:
            Message status information or None if not found
        """
        try:
            # Get RPC URL for destination chain (where message should be delivered)
            rpc_url_env = f"{destination_chain.upper()}_RPC_URL"
            if destination_chain == "ethereum" or destination_chain == "sepolia":
                rpc_url_env = "ETH_RPC_URL"
            elif destination_chain == "polygon" or destination_chain == "amoy":
                rpc_url_env = "POLYGON_RPC_URL"

            rpc_url = os.getenv(rpc_url_env) or os.getenv("RPC_URL")
            if not rpc_url:
                logger.warning(f"RPC URL not found for chain: {destination_chain}")
                return None

            # Connect to destination chain
            web3 = Web3(Web3.HTTPProvider(rpc_url))
            if not web3.is_connected():
                logger.warning(f"Failed to connect to {destination_chain} RPC")
                return None

            # Get CCIP Router address for destination chain
            router_address = CCIP_ROUTER_ADDRESSES.get(destination_chain.lower())
            if not router_address:
                logger.warning(f"CCIP Router address not configured for {destination_chain}")
                return None

            # Create contract instance
            router_contract = web3.eth.contract(
                address=Web3.to_checksum_address(router_address),
                abi=CCIP_ROUTER_ABI,
            )

            # Convert message_id string to bytes32 if needed
            if isinstance(message_id, str):
                if message_id.startswith("0x"):
                    message_id_bytes = bytes.fromhex(message_id[2:])
                else:
                    # Pad to 32 bytes
                    message_id_bytes = message_id.encode().ljust(32, b"\x00")[:32]
            else:
                message_id_bytes = message_id

            # Query message status from Router contract
            try:
                status_code = router_contract.functions.getMessageStatus(message_id_bytes).call()
                status_name = CCIP_MESSAGE_STATUS.get(status_code, f"Unknown({status_code})")

                # Get commitment (if available)
                try:
                    commitment = router_contract.functions.getCommitment(message_id_bytes).call()
                    commitment_hex = (
                        commitment.hex() if hasattr(commitment, "hex") else str(commitment)
                    )
                except Exception:
                    commitment_hex = None

                return {
                    "message_id": message_id,
                    "status": status_name,
                    "status_code": status_code,
                    "source_chain": source_chain,
                    "destination_chain": destination_chain,
                    "commitment": commitment_hex,
                    "is_delivered": status_code == 2,  # Success status
                    "is_failed": status_code == 3,  # Failure status
                }
            except Exception as contract_error:
                logger.debug(
                    f"Failed to query CCIP Router for message {message_id}: {contract_error}"
                )
                # Message might not exist yet or Router might not have this method
                # Return None to indicate status unknown
                return None

        except Exception as e:
            logger.error(f"Failed to get CCIP message status: {e}", exc_info=True)
            return None

    async def get_ccip_chain_selector(self, chain_name: str) -> Optional[int]:
        """Get CCIP chain selector for a chain."""
        # Chainlink CCIP uses numeric chain selectors
        # Mapping: https://docs.chain.link/ccip/supported-networks
        chain_selectors = {
            "ethereum": 5009297550715157269,
            "sepolia": 16015286601757825753,
            "polygon": 4051577828743386545,
            "amoy": 16281711391670634445,
            "arbitrum": 4949039107694359620,
            "arbitrum-sepolia": 3478487238524512106,
            "base": 15971525489660198786,
            "base-sepolia": 10344971235874465080,
            "optimism": 3734403246176062136,
            "optimism-sepolia": 5224473277236331295,
        }

        return chain_selectors.get(chain_name.lower())

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
