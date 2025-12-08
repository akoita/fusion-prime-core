"""Bridge executor for executing cross-chain transactions via testnet bridges."""

import logging
import os
from typing import Optional

from eth_account import Account
from infrastructure.db.models import BridgeProtocol
from web3 import Web3
from web3.types import TxParams

logger = logging.getLogger(__name__)

# Axelar Testnet Contract Addresses
# Source: https://docs.axelar.dev/dev/reference/testnet-contract-addresses
AXELAR_GATEWAY_TESTNET = {
    "ethereum": "0xe432150cce91c13a887f7D836923d5597adD8E31",  # Sepolia
    "polygon": "0xBF62ef1486468a6bd26Dd669C06db43dE641d239",  # Amoy
    "arbitrum": "0xe432150cce91c13a887f7D836923d5597adD8E31",  # Arbitrum Sepolia
}

AXELAR_GAS_SERVICE_TESTNET = {
    "ethereum": "0xbE406F0189A0B4cf3A05C286473D23791Dd44Cc6",  # Sepolia
    "polygon": "0xbE406F0189A0B4cf3A05C286473D23791Dd44Cc6",  # Amoy
    "arbitrum": "0xbE406F0189A0B4cf3A05C286473D23791Dd44Cc6",  # Arbitrum Sepolia
}

# Chainlink CCIP Testnet Router Addresses
# Source: https://docs.chain.link/ccip/supported-networks
CCIP_ROUTER_TESTNET = {
    "ethereum": "0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59",  # Sepolia
    "polygon": "0x1035CabC275068e0F4b745A29CEDf38E13aF41b1",  # Amoy
    "arbitrum": "0x88E492127709447A5AB4da4A0D1861Bab2bE98e5",  # Arbitrum Sepolia
}

# Chain name mappings
CHAIN_NAME_MAP = {
    "ethereum": "ethereum",
    "sepolia": "ethereum",
    "polygon": "polygon",
    "amoy": "polygon",
    "arbitrum": "arbitrum",
    "arbitrum-sepolia": "arbitrum",
}


class BridgeExecutor:
    """Executes cross-chain transactions via bridge protocols."""

    def __init__(self, source_chain: str, private_key: Optional[str] = None):
        """
        Initialize bridge executor.

        Args:
            source_chain: Source chain name (ethereum, polygon, arbitrum)
            private_key: Private key for signing transactions (defaults to DEPLOYER_PRIVATE_KEY)
        """
        self.source_chain = source_chain.lower()
        self.chain_key = CHAIN_NAME_MAP.get(self.source_chain, self.source_chain)

        # Get RPC URL
        rpc_url_env = f"{self.source_chain.upper()}_RPC_URL"
        if self.source_chain == "ethereum":
            rpc_url_env = "ETH_RPC_URL"
        elif self.source_chain == "polygon":
            rpc_url_env = "POLYGON_RPC_URL"

        rpc_url = os.getenv(rpc_url_env) or os.getenv("RPC_URL")
        if not rpc_url:
            raise ValueError(f"RPC URL not found for chain: {source_chain}")

        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.web3.is_connected():
            raise ConnectionError(f"Failed to connect to {source_chain} RPC: {rpc_url}")

        # Get private key
        private_key = private_key or os.getenv("DEPLOYER_PRIVATE_KEY")
        if not private_key:
            raise ValueError("Private key not provided and DEPLOYER_PRIVATE_KEY not set")

        # Remove 0x prefix if present
        if private_key.startswith("0x"):
            private_key = private_key[2:]

        self.account = Account.from_key(private_key)
        logger.info(
            f"Bridge executor initialized for {source_chain} (address: {self.account.address})"
        )

    async def execute_settlement(
        self,
        protocol: BridgeProtocol,
        destination_chain: str,
        destination_address: str,
        payload: bytes,
        gas_value: int = 0,
    ) -> str:
        """
        Execute settlement via bridge protocol.

        Args:
            protocol: Bridge protocol (AXELAR or CCIP)
            destination_chain: Destination chain name
            destination_address: Destination contract address
            payload: Encoded message payload
            gas_value: Gas value to send (in wei)

        Returns:
            Transaction hash
        """
        if protocol == BridgeProtocol.AXELAR:
            return await self._execute_axelar(
                destination_chain, destination_address, payload, gas_value
            )
        elif protocol == BridgeProtocol.CCIP:
            return await self._execute_ccip(
                destination_chain, destination_address, payload, gas_value
            )
        else:
            raise ValueError(f"Unsupported protocol: {protocol}")

    async def _execute_axelar(
        self, destination_chain: str, destination_address: str, payload: bytes, gas_value: int
    ) -> str:
        """Execute settlement via Axelar Gateway."""
        gateway_address = AXELAR_GATEWAY_TESTNET.get(self.chain_key)
        gas_service_address = AXELAR_GAS_SERVICE_TESTNET.get(self.chain_key)

        if not gateway_address or not gas_service_address:
            raise ValueError(f"Axelar contracts not configured for chain: {self.source_chain}")

        logger.info(f"Executing Axelar transaction: {self.source_chain} -> {destination_chain}")

        # Axelar Gateway ABI (minimal - just callContract)
        gateway_abi = [
            {
                "inputs": [
                    {"internalType": "string", "name": "destinationChain", "type": "string"},
                    {"internalType": "string", "name": "destinationAddress", "type": "string"},
                    {"internalType": "bytes", "name": "payload", "type": "bytes"},
                ],
                "name": "callContract",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            }
        ]

        # Axelar Gas Service ABI (minimal - just payNativeGasForContractCall)
        gas_service_abi = [
            {
                "inputs": [
                    {"internalType": "address", "name": "sender", "type": "address"},
                    {"internalType": "string", "name": "destinationChain", "type": "string"},
                    {"internalType": "string", "name": "destinationAddress", "type": "string"},
                    {"internalType": "bytes", "name": "payload", "type": "bytes"},
                    {"internalType": "address", "name": "refundAddress", "type": "address"},
                ],
                "name": "payNativeGasForContractCall",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function",
            }
        ]

        gateway_contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(gateway_address), abi=gateway_abi
        )
        gas_service_contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(gas_service_address), abi=gas_service_abi
        )

        # Convert destination address to string format (Axelar uses string addresses)
        if not destination_address.startswith("0x"):
            destination_address = f"0x{destination_address}"

        # Map destination chain name
        dest_chain_key = CHAIN_NAME_MAP.get(destination_chain.lower(), destination_chain.lower())

        # Pay for gas first (if gas_value > 0)
        # Get base nonce (including pending transactions)
        base_nonce = self.web3.eth.get_transaction_count(self.account.address, "pending")

        if gas_value > 0:
            gas_tx = gas_service_contract.functions.payNativeGasForContractCall(
                self.account.address,  # sender
                dest_chain_key,  # destinationChain
                destination_address,  # destinationAddress
                payload,  # payload
                self.account.address,  # refundAddress
            ).build_transaction(
                {
                    "from": self.account.address,
                    "nonce": base_nonce,
                    "gas": 200000,
                    "gasPrice": self.web3.eth.gas_price,
                    "value": gas_value,
                }
            )

            signed_gas_tx = self.account.sign_transaction(gas_tx)
            gas_tx_hash = self.web3.eth.send_raw_transaction(signed_gas_tx.raw_transaction)
            logger.info(f"Gas payment transaction sent: {gas_tx_hash.hex()}")
            # Don't wait for confirmation - let the transaction be processed asynchronously
            # The message monitor will track the transaction status
            # Increment nonce for next transaction
            base_nonce += 1

        # Call gateway.callContract
        gateway_tx = gateway_contract.functions.callContract(
            dest_chain_key,  # destinationChain
            destination_address,  # destinationAddress
            payload,  # payload
        ).build_transaction(
            {
                "from": self.account.address,
                "nonce": base_nonce,
                "gas": 500000,
                "gasPrice": self.web3.eth.gas_price,
            }
        )

        signed_tx = self.account.sign_transaction(gateway_tx)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash_hex = tx_hash.hex()

        logger.info(f"Axelar transaction sent: {tx_hash_hex}")
        return tx_hash_hex

    async def _execute_ccip(
        self, destination_chain: str, destination_address: str, payload: bytes, gas_value: int
    ) -> str:
        """Execute settlement via Chainlink CCIP Router."""
        router_address = CCIP_ROUTER_TESTNET.get(self.chain_key)

        if not router_address:
            raise ValueError(f"CCIP router not configured for chain: {self.source_chain}")

        logger.info(f"Executing CCIP transaction: {self.source_chain} -> {destination_chain}")

        # Get destination chain selector
        from app.integrations.ccip_client import CCIPClient

        ccip_client = CCIPClient()
        dest_chain_selector = await ccip_client.get_ccip_chain_selector(destination_chain)
        if not dest_chain_selector:
            raise ValueError(f"CCIP chain selector not found for: {destination_chain}")

        # CCIP Router ABI (minimal - just ccipSend)
        router_abi = [
            {
                "inputs": [
                    {
                        "components": [
                            {
                                "internalType": "uint64",
                                "name": "destinationChainSelector",
                                "type": "uint64",
                            },
                            {"internalType": "address", "name": "receiver", "type": "address"},
                            {"internalType": "bytes", "name": "data", "type": "bytes"},
                            {
                                "components": [
                                    {"internalType": "address", "name": "token", "type": "address"},
                                    {
                                        "internalType": "uint256",
                                        "name": "amount",
                                        "type": "uint256",
                                    },
                                ],
                                "internalType": "struct Client.EVMTokenAmount[]",
                                "name": "tokenAmounts",
                                "type": "tuple[]",
                            },
                            {"internalType": "address", "name": "feeToken", "type": "address"},
                            {"internalType": "bytes32", "name": "extraArgs", "type": "bytes32"},
                        ],
                        "internalType": "struct Client.EVM2AnyMessage",
                        "name": "message",
                        "type": "tuple",
                    }
                ],
                "name": "ccipSend",
                "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
                "stateMutability": "payable",
                "type": "function",
            }
        ]

        router_contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(router_address), abi=router_abi
        )

        # Convert destination address
        receiver_address = Web3.to_checksum_address(destination_address)

        # Build CCIP message
        ccip_message = {
            "destinationChainSelector": dest_chain_selector,
            "receiver": receiver_address,
            "data": payload,
            "tokenAmounts": [],  # No tokens for now
            "feeToken": "0x0000000000000000000000000000000000000000",  # Native token
            "extraArgs": b"",  # Empty extra args
        }

        # Estimate gas first
        try:
            gas_estimate = router_contract.functions.ccipSend(ccip_message).estimate_gas(
                {"from": self.account.address, "value": gas_value}
            )
            gas_limit = int(gas_estimate * 1.2)  # Add 20% buffer
        except Exception as e:
            logger.warning(f"Gas estimation failed: {e}, using default")
            gas_limit = 500000

        # Build and send transaction
        router_tx = router_contract.functions.ccipSend(ccip_message).build_transaction(
            {
                "from": self.account.address,
                "nonce": self.web3.eth.get_transaction_count(self.account.address),
                "gas": gas_limit,
                "gasPrice": self.web3.eth.gas_price,
                "value": gas_value,
            }
        )

        signed_tx = self.account.sign_transaction(router_tx)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash_hex = tx_hash.hex()

        logger.info(f"CCIP transaction sent: {tx_hash_hex}")
        return tx_hash_hex
