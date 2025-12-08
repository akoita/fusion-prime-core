"""
Web3 Test Utilities

This module provides Web3.py-based utilities for testing smart contracts
instead of using subprocess calls to cast commands.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from web3 import Web3
from web3.contract import Contract
from web3.types import BlockData, TxReceipt


class Web3TestUtils:
    """Utilities for Web3-based contract testing."""

    def __init__(self, rpc_url: str = "http://localhost:8545"):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Cannot connect to blockchain at {rpc_url}")

    def get_contract(self, address: str, abi: List[Dict[str, Any]]) -> Contract:
        """Get a contract instance."""
        # Ensure address is checksummed
        checksum_address = self.w3.to_checksum_address(address)
        return self.w3.eth.contract(address=checksum_address, abi=abi)

    def load_abi_from_file(self, abi_path: str) -> List[Dict[str, Any]]:
        """Load ABI from JSON file."""
        with open(abi_path, "r") as f:
            abi_data = json.load(f)
            return abi_data.get("abi", abi_data)

    def call_contract_function(self, contract: Contract, function_name: str, *args) -> Any:
        """Call a contract function and return the result."""
        try:
            function = getattr(contract.functions, function_name)
            return function(*args).call()
        except Exception as e:
            raise RuntimeError(f"Failed to call {function_name}: {e}")

    def send_contract_transaction(
        self,
        contract: Contract,
        function_name: str,
        from_account: str,
        value: int = 0,
        *args,
    ) -> TxReceipt:
        """Send a contract transaction and return the receipt."""
        try:
            function = getattr(contract.functions, function_name)
            tx_hash = function(*args).transact({"from": from_account, "value": value})
            return self.w3.eth.wait_for_transaction_receipt(tx_hash)
        except Exception as e:
            raise RuntimeError(f"Failed to send transaction {function_name}: {e}")

    def get_contract_events(
        self,
        contract: Contract,
        event_name: str,
        from_block: int = 0,
        to_block: str = "latest",
    ) -> List[Dict[str, Any]]:
        """Get contract events."""
        try:
            event_filter = getattr(contract.events, event_name)
            return event_filter.get_logs(from_block=from_block, to_block=to_block)
        except Exception as e:
            raise RuntimeError(f"Failed to get events {event_name}: {e}")

    def get_accounts(self) -> List[str]:
        """Get available accounts."""
        return self.w3.eth.accounts

    def get_balance(self, address: str) -> int:
        """Get account balance in wei."""
        checksum_address = self.w3.to_checksum_address(address)
        return self.w3.eth.get_balance(checksum_address)

    def get_block_number(self) -> int:
        """Get latest block number."""
        return self.w3.eth.block_number

    def get_transaction_receipt(self, tx_hash: str) -> TxReceipt:
        """Get transaction receipt."""
        return self.w3.eth.get_transaction_receipt(tx_hash)

    def get_code(self, address: str) -> bytes:
        """Get contract code."""
        checksum_address = self.w3.to_checksum_address(address)
        return self.w3.eth.get_code(checksum_address)

    def is_contract_deployed(self, address: str) -> bool:
        """Check if contract is deployed."""
        code = self.get_code(address)
        return len(code) > 0


class EscrowFactoryTester:
    """Specialized tester for EscrowFactory contract."""

    def __init__(self, web3_utils: Web3TestUtils, factory_address: str, abi: List[Dict[str, Any]]):
        self.web3_utils = web3_utils
        self.factory_contract = web3_utils.get_contract(factory_address, abi)

    def get_escrow_count(self) -> int:
        """Get the number of deployed escrows."""
        return self.web3_utils.call_contract_function(self.factory_contract, "getEscrowCount")

    def create_escrow(
        self,
        payee: str,
        release_delay: int,
        approvals_required: int,
        arbiter: str,
        from_account: str,
        value: int,
    ) -> TxReceipt:
        """Create a new escrow and return the transaction receipt."""
        return self.web3_utils.send_contract_transaction(
            self.factory_contract,
            "createEscrow",
            from_account,
            value,
            payee,
            release_delay,
            approvals_required,
            arbiter,
        )

    def get_escrow_deployed_events(
        self, from_block: int = 0, to_block: str = "latest"
    ) -> List[Dict[str, Any]]:
        """Get EscrowDeployed events."""
        return self.web3_utils.get_contract_events(
            self.factory_contract, "EscrowDeployed", from_block, to_block
        )

    def get_escrow_address_from_receipt(self, receipt: TxReceipt) -> Optional[str]:
        """Extract escrow address from transaction receipt."""
        events = self.get_escrow_deployed_events(
            from_block=receipt.blockNumber, to_block=receipt.blockNumber
        )

        if events:
            return events[0]["args"]["escrow"]
        return None


class BlockchainHealthChecker:
    """Check blockchain and contract health."""

    def __init__(self, web3_utils: Web3TestUtils):
        self.web3_utils = web3_utils

    def check_connection(self) -> bool:
        """Check if blockchain is accessible."""
        try:
            return self.web3_utils.w3.is_connected()
        except Exception:
            return False

    def check_contract_deployment(self, address: str) -> bool:
        """Check if contract is deployed."""
        return self.web3_utils.is_contract_deployed(address)

    def check_contract_functionality(self, factory_tester: EscrowFactoryTester) -> bool:
        """Check if contract functions work."""
        try:
            # Try to call a view function
            count = factory_tester.get_escrow_count()
            return isinstance(count, int)
        except Exception:
            return False

    def get_system_info(self) -> Dict[str, Any]:
        """Get blockchain system information."""
        try:
            return {
                "connected": self.web3_utils.w3.is_connected(),
                "block_number": self.web3_utils.get_block_number(),
                "accounts_count": len(self.web3_utils.get_accounts()),
                "chain_id": self.web3_utils.w3.eth.chain_id,
                "gas_price": self.web3_utils.w3.eth.gas_price,
            }
        except Exception as e:
            return {"error": str(e)}


# Predefined ABIs for common contracts
ESCROW_ABI = [
    {
        "inputs": [],
        "name": "approve",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "approver", "type": "address"}],
        "name": "approvals",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "release",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "refund",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [{"indexed": True, "name": "approver", "type": "address"}],
        "name": "Approval",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "payer", "type": "address"},
            {"indexed": True, "name": "payee", "type": "address"},
            {"indexed": False, "name": "amount", "type": "uint256"},
        ],
        "name": "EscrowReleased",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "payer", "type": "address"},
            {"indexed": True, "name": "payee", "type": "address"},
            {"indexed": False, "name": "amount", "type": "uint256"},
        ],
        "name": "EscrowRefunded",
        "type": "event",
    },
]
