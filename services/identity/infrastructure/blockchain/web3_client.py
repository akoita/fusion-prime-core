"""
Web3 client for blockchain interactions.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3

# Web3.py v6+ compatibility
try:
    from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
except ImportError:
    from web3.middleware import geth_poa_middleware

logger = logging.getLogger(__name__)


class Web3Client:
    """Client for interacting with Ethereum blockchain."""

    def __init__(
        self,
        rpc_url: str,
        private_key: str,
        chain_id: int,
        identity_factory_address: str,
        claim_issuer_registry_address: str,
    ):
        """
        Initialize Web3 client.

        Args:
            rpc_url: Ethereum RPC endpoint
            private_key: Private key for signing transactions
            chain_id: Chain ID (1=mainnet, 11155111=sepolia)
            identity_factory_address: IdentityFactory contract address
            claim_issuer_registry_address: ClaimIssuerRegistry contract address
        """
        self.rpc_url = rpc_url
        self.chain_id = chain_id

        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

        # Add PoA middleware for testnets
        if chain_id in [11155111, 80001]:  # Sepolia, Mumbai
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)

        # Setup account
        self.account: LocalAccount = Account.from_key(private_key)
        self.address = self.account.address

        logger.info(f"Web3 client initialized: chain_id={chain_id}, address={self.address}")

        # Load contract ABIs
        self.identity_factory_abi = self._load_abi("IdentityFactory")
        self.claim_issuer_registry_abi = self._load_abi("ClaimIssuerRegistry")
        self.identity_abi = self._load_abi("Identity")

        # Initialize contracts
        self.identity_factory = self.w3.eth.contract(
            address=Web3.to_checksum_address(identity_factory_address),
            abi=self.identity_factory_abi,
        )

        self.claim_issuer_registry = self.w3.eth.contract(
            address=Web3.to_checksum_address(claim_issuer_registry_address),
            abi=self.claim_issuer_registry_abi,
        )

        logger.info(
            f"Contracts loaded: factory={identity_factory_address}, "
            f"registry={claim_issuer_registry_address}"
        )

    def _load_abi(self, contract_name: str) -> list:
        """
        Load contract ABI from file.

        Args:
            contract_name: Name of the contract

        Returns:
            Contract ABI as list
        """
        # Try multiple paths
        paths = [
            Path(f"../../contracts/out/{contract_name}.sol/{contract_name}.json"),
            Path(f"../contracts/identity/out/{contract_name}.sol/{contract_name}.json"),
            Path(f"./abis/{contract_name}.json"),
        ]

        for path in paths:
            if path.exists():
                with open(path, "r") as f:
                    contract_json = json.load(f)
                    return contract_json.get("abi", [])

        # Fallback: return minimal ABI for testing
        logger.warning(f"ABI file not found for {contract_name}, using minimal ABI")
        return self._get_minimal_abi(contract_name)

    def _get_minimal_abi(self, contract_name: str) -> list:
        """Get minimal ABI for testing."""
        if contract_name == "IdentityFactory":
            return [
                {
                    "inputs": [{"internalType": "address", "name": "_owner", "type": "address"}],
                    "name": "createIdentityFor",
                    "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                    "stateMutability": "nonpayable",
                    "type": "function",
                },
                {
                    "inputs": [{"internalType": "address", "name": "_owner", "type": "address"}],
                    "name": "getIdentity",
                    "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                    "stateMutability": "view",
                    "type": "function",
                },
            ]
        elif contract_name == "ClaimIssuerRegistry":
            return [
                {
                    "inputs": [
                        {"internalType": "address", "name": "_identity", "type": "address"},
                        {"internalType": "uint256", "name": "_topic", "type": "uint256"},
                        {"internalType": "uint256", "name": "_scheme", "type": "uint256"},
                        {"internalType": "bytes", "name": "_data", "type": "bytes"},
                        {"internalType": "string", "name": "_uri", "type": "string"},
                    ],
                    "name": "issueClaim",
                    "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
                    "stateMutability": "nonpayable",
                    "type": "function",
                }
            ]
        return []

    async def create_identity(self, owner_address: str) -> Dict[str, Any]:
        """
        Create a new identity for a user.

        Args:
            owner_address: Address of the identity owner

        Returns:
            Dict with identity_address and tx_hash
        """
        try:
            owner_address = Web3.to_checksum_address(owner_address)

            # Check if identity already exists
            existing_identity = self.identity_factory.functions.getIdentity(owner_address).call()
            if existing_identity != "0x0000000000000000000000000000000000000000":
                logger.info(f"Identity already exists for {owner_address}: {existing_identity}")
                return {
                    "identity_address": existing_identity,
                    "tx_hash": None,
                    "already_exists": True,
                }

            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.address)

            tx = self.identity_factory.functions.createIdentityFor(owner_address).build_transaction(
                {
                    "chainId": self.chain_id,
                    "gas": 500000,
                    "gasPrice": self.w3.eth.gas_price,
                    "nonce": nonce,
                }
            )

            # Sign transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)

            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_hex = tx_hash.hex()

            logger.info(f"Identity creation transaction sent: {tx_hash_hex}")

            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt["status"] == 1:
                # Get identity address from factory
                identity_address = self.identity_factory.functions.getIdentity(owner_address).call()

                logger.info(
                    f"Identity created successfully: owner={owner_address}, "
                    f"identity={identity_address}, tx={tx_hash_hex}"
                )

                return {
                    "identity_address": identity_address,
                    "tx_hash": tx_hash_hex,
                    "block_number": receipt["blockNumber"],
                    "gas_used": receipt["gasUsed"],
                    "already_exists": False,
                }
            else:
                raise Exception(f"Transaction failed: {receipt}")

        except Exception as e:
            logger.error(f"Error creating identity for {owner_address}: {e}")
            raise

    async def issue_claim(
        self, identity_address: str, topic: int, data: bytes, uri: str = ""
    ) -> Dict[str, Any]:
        """
        Issue a claim to an identity.

        Args:
            identity_address: Address of the identity contract
            topic: Claim topic (1=KYC, 2=AML, etc.)
            data: Claim data
            uri: Optional URI for additional data

        Returns:
            Dict with claim_id and tx_hash
        """
        try:
            identity_address = Web3.to_checksum_address(identity_address)

            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.address)

            scheme = 1  # ECDSA scheme

            tx = self.claim_issuer_registry.functions.issueClaim(
                identity_address, topic, scheme, data, uri
            ).build_transaction(
                {
                    "chainId": self.chain_id,
                    "gas": 300000,
                    "gasPrice": self.w3.eth.gas_price,
                    "nonce": nonce,
                }
            )

            # Sign transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)

            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_hex = tx_hash.hex()

            logger.info(f"Claim issuance transaction sent: {tx_hash_hex}")

            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt["status"] == 1:
                # Parse logs to get claim ID
                claim_id = None
                for log in receipt["logs"]:
                    if len(log["topics"]) > 0:
                        # ClaimIssued event
                        claim_id = log["topics"][1].hex() if len(log["topics"]) > 1 else None

                logger.info(
                    f"Claim issued successfully: identity={identity_address}, "
                    f"topic={topic}, claim_id={claim_id}, tx={tx_hash_hex}"
                )

                return {
                    "claim_id": claim_id,
                    "tx_hash": tx_hash_hex,
                    "block_number": receipt["blockNumber"],
                    "gas_used": receipt["gasUsed"],
                }
            else:
                raise Exception(f"Transaction failed: {receipt}")

        except Exception as e:
            logger.error(f"Error issuing claim to {identity_address}: {e}")
            raise

    def get_identity(self, owner_address: str) -> Optional[str]:
        """
        Get identity address for an owner.

        Args:
            owner_address: Owner address

        Returns:
            Identity contract address or None
        """
        try:
            owner_address = Web3.to_checksum_address(owner_address)
            identity_address = self.identity_factory.functions.getIdentity(owner_address).call()

            if identity_address == "0x0000000000000000000000000000000000000000":
                return None

            return identity_address

        except Exception as e:
            logger.error(f"Error getting identity for {owner_address}: {e}")
            return None

    def is_connected(self) -> bool:
        """Check if Web3 is connected."""
        return self.w3.is_connected()

    def get_balance(self, address: str) -> int:
        """Get ETH balance for an address."""
        return self.w3.eth.get_balance(Web3.to_checksum_address(address))
