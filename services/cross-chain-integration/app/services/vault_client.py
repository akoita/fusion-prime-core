"""Client for querying CrossChainVault contracts across multiple chains."""

import logging
import os
from typing import Dict, Optional

from web3 import Web3

logger = logging.getLogger(__name__)

# CrossChainVault contract addresses (from deployment)
CROSS_CHAIN_VAULT_ADDRESSES = {
    "ethereum": os.getenv(
        "CROSS_CHAIN_VAULT_ETH_ADDRESS", "0x0C95a78b0D72F882fae14CD7C842a5f000E0c4e2"
    ),
    "polygon": os.getenv(
        "CROSS_CHAIN_VAULT_POLYGON_ADDRESS", "0x7843C2eD8930210142DC51dbDf8419C74FD27529"
    ),
    # Add more chains as they're deployed
    # "arbitrum": os.getenv("CROSS_CHAIN_VAULT_ARBITRUM_ADDRESS", ""),
}

# Minimal ABI for CrossChainVault queries
CROSS_CHAIN_VAULT_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "getTotalCollateral",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "string", "name": "chainName", "type": "string"},
        ],
        "name": "getCollateralOnChain",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "getTotalBorrowed",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "getCreditLine",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


class VaultClient:
    """Client for querying CrossChainVault contracts."""

    def __init__(self):
        """Initialize vault client with RPC connections."""
        self.vaults: Dict[str, tuple] = {}  # chain_name -> (web3, contract)
        self._initialize_connections()

    def _initialize_connections(self):
        """Initialize Web3 connections for each chain."""
        # Ethereum Sepolia
        eth_rpc = os.getenv("ETH_RPC_URL") or os.getenv("RPC_URL")
        if eth_rpc and "ethereum" in CROSS_CHAIN_VAULT_ADDRESSES:
            try:
                web3_eth = Web3(Web3.HTTPProvider(eth_rpc))
                if web3_eth.is_connected():
                    vault_eth = web3_eth.eth.contract(
                        address=Web3.to_checksum_address(CROSS_CHAIN_VAULT_ADDRESSES["ethereum"]),
                        abi=CROSS_CHAIN_VAULT_ABI,
                    )
                    self.vaults["ethereum"] = (web3_eth, vault_eth)
                    logger.info(
                        f"Connected to Ethereum vault: {CROSS_CHAIN_VAULT_ADDRESSES['ethereum']}"
                    )
            except Exception as e:
                logger.warning(f"Failed to connect to Ethereum vault: {e}")

        # Polygon Amoy
        polygon_rpc = os.getenv("POLYGON_RPC_URL")
        if polygon_rpc and "polygon" in CROSS_CHAIN_VAULT_ADDRESSES:
            try:
                web3_polygon = Web3(Web3.HTTPProvider(polygon_rpc))
                if web3_polygon.is_connected():
                    vault_polygon = web3_polygon.eth.contract(
                        address=Web3.to_checksum_address(CROSS_CHAIN_VAULT_ADDRESSES["polygon"]),
                        abi=CROSS_CHAIN_VAULT_ABI,
                    )
                    self.vaults["polygon"] = (web3_polygon, vault_polygon)
                    logger.info(
                        f"Connected to Polygon vault: {CROSS_CHAIN_VAULT_ADDRESSES['polygon']}"
                    )
            except Exception as e:
                logger.warning(f"Failed to connect to Polygon vault: {e}")

    def get_collateral_on_chain(self, user_address: str, chain_name: str) -> int:
        """
        Get user's collateral on a specific chain.

        Args:
            user_address: User's Ethereum address
            chain_name: Chain name (ethereum, polygon, etc.)

        Returns:
            Collateral amount in wei (0 if chain not available or user has no collateral)
        """
        if chain_name not in self.vaults:
            logger.warning(f"Vault not available for chain: {chain_name}")
            return 0

        try:
            web3, vault = self.vaults[chain_name]
            user_address_checksum = Web3.to_checksum_address(user_address)
            collateral = vault.functions.getCollateralOnChain(
                user_address_checksum, chain_name
            ).call()
            return collateral
        except Exception as e:
            logger.error(f"Failed to query collateral on {chain_name}: {e}")
            return 0

    def get_total_collateral(self, user_address: str, chain_name: str) -> int:
        """
        Get user's total collateral (across all chains) from a specific vault.

        Note: Each vault maintains its own view of total collateral across chains.
        This queries the vault on the specified chain.

        Args:
            user_address: User's Ethereum address
            chain_name: Chain name to query from

        Returns:
            Total collateral amount in wei (0 if chain not available)
        """
        if chain_name not in self.vaults:
            logger.warning(f"Vault not available for chain: {chain_name}")
            return 0

        try:
            web3, vault = self.vaults[chain_name]
            user_address_checksum = Web3.to_checksum_address(user_address)
            total_collateral = vault.functions.getTotalCollateral(user_address_checksum).call()
            return total_collateral
        except Exception as e:
            logger.error(f"Failed to query total collateral from {chain_name}: {e}")
            return 0

    def get_collateral_all_chains(self, user_address: str) -> Dict[str, int]:
        """
        Get user's collateral across all available chains.

        Args:
            user_address: User's Ethereum address

        Returns:
            Dictionary mapping chain names to collateral amounts (in wei)
        """
        collateral_by_chain = {}
        for chain_name in self.vaults.keys():
            collateral = self.get_collateral_on_chain(user_address, chain_name)
            collateral_by_chain[chain_name] = collateral
        return collateral_by_chain
