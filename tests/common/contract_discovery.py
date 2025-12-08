"""
Contract Discovery System

Automatically discovers deployed contract addresses and ABIs from deployment artifacts.
This follows professional development practices where contract information is retrieved
from deployment artifacts rather than hardcoded values.

For local environments: Reads from Foundry broadcast artifacts
For remote environments: Reads from GCP bucket or deployment registry
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ContractInfo:
    """Information about a deployed contract."""

    name: str
    address: str
    abi: List[Dict[str, Any]]
    deployment_tx: str
    block_number: int
    chain_id: int


class ContractDiscovery:
    """Discovers deployed contracts from deployment artifacts."""

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root or os.getcwd())
        self.contracts_dir = self.project_root / "contracts"
        self.broadcast_dir = self.contracts_dir / "broadcast"
        self.out_dir = self.contracts_dir / "out"

    def discover_contracts(self, environment: str = "local") -> Dict[str, ContractInfo]:
        """
        Discover all deployed contracts for the given environment.

        Args:
            environment: Environment name (local, dev, staging, production)

        Returns:
            Dictionary mapping contract names to ContractInfo objects
        """
        if environment == "local":
            return self._discover_local_contracts()
        else:
            return self._discover_remote_contracts(environment)

    def _discover_local_contracts(self) -> Dict[str, ContractInfo]:
        """Discover contracts from local Foundry deployment artifacts."""
        contracts = {}

        # Find the latest deployment run
        deployment_runs = self._find_latest_deployment_run()
        if not deployment_runs:
            print("⚠️  No deployment artifacts found")
            return contracts

        # Load deployment artifacts and verify contracts exist on blockchain
        for run_path in deployment_runs:
            try:
                with open(run_path, "r") as f:
                    deployment_data = json.load(f)

                # Extract contract information
                for tx in deployment_data.get("transactions", []):
                    if tx.get("transactionType") == "CREATE":
                        contract_name = tx.get("contractName")
                        contract_address = tx.get("contractAddress")
                        deployment_tx = tx.get("hash")

                        if contract_name and contract_address:
                            # Verify contract actually exists on blockchain
                            if self._verify_contract_deployed(contract_address):
                                # Convert to checksum address
                                checksum_address = self._get_checksum_address(contract_address)

                                # Load ABI from out directory
                                abi = self._load_contract_abi(contract_name)

                                # Extract chain ID and block number
                                chain_id = int(tx.get("transaction", {}).get("chainId", "0x0"), 16)
                                block_number = self._get_block_number_from_receipt(
                                    deployment_data, deployment_tx
                                )

                                contracts[contract_name] = ContractInfo(
                                    name=contract_name,
                                    address=checksum_address,
                                    abi=abi,
                                    deployment_tx=deployment_tx,
                                    block_number=block_number,
                                    chain_id=chain_id,
                                )

                                print(f"✅ Discovered {contract_name} at {checksum_address}")
                            else:
                                print(
                                    f"⚠️  Contract {contract_name} at {contract_address} not found on blockchain"
                                )

            except Exception as e:
                print(f"⚠️  Error loading deployment artifacts from {run_path}: {e}")

        return contracts

    def _discover_remote_contracts(self, environment: str) -> Dict[str, ContractInfo]:
        """Discover contracts from remote deployment registry (GCP bucket, etc.)."""
        # TODO: Implement remote contract discovery
        # This would read from GCP bucket or deployment registry
        print(f"⚠️  Remote contract discovery not yet implemented for {environment}")
        return {}

    def _find_latest_deployment_run(self) -> List[Path]:
        """Find the latest deployment run artifacts."""
        deployment_runs = []

        # Look for deployment runs in broadcast directory
        if self.broadcast_dir.exists():
            for script_dir in self.broadcast_dir.iterdir():
                if script_dir.is_dir():
                    for chain_dir in script_dir.iterdir():
                        if chain_dir.is_dir():
                            run_latest = chain_dir / "run-latest.json"
                            if run_latest.exists():
                                deployment_runs.append(run_latest)

        return sorted(deployment_runs, key=lambda p: p.stat().st_mtime, reverse=True)

    def _load_contract_abi(self, contract_name: str) -> List[Dict[str, Any]]:
        """Load contract ABI from the out directory."""
        abi_path = self.out_dir / f"{contract_name}.sol" / f"{contract_name}.json"

        if not abi_path.exists():
            print(f"⚠️  ABI not found for {contract_name} at {abi_path}")
            return []

        try:
            with open(abi_path, "r") as f:
                abi_data = json.load(f)

            # Extract ABI from the compiled artifact
            if isinstance(abi_data, dict) and "abi" in abi_data:
                return abi_data["abi"]
            elif isinstance(abi_data, list):
                return abi_data
            else:
                print(f"⚠️  Invalid ABI format for {contract_name}")
                return []

        except Exception as e:
            print(f"⚠️  Error loading ABI for {contract_name}: {e}")
            return []

    def _get_block_number_from_receipt(self, deployment_data: Dict, tx_hash: str) -> int:
        """Extract block number from deployment receipt."""
        for receipt in deployment_data.get("receipts", []):
            if receipt.get("transactionHash") == tx_hash:
                return int(receipt.get("blockNumber", "0x0"), 16)
        return 0

    def _verify_contract_deployed(self, contract_address: str) -> bool:
        """Verify that a contract is actually deployed on the blockchain."""
        try:
            from web3 import Web3

            w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
            checksum_address = w3.to_checksum_address(contract_address)
            code = w3.eth.get_code(checksum_address)
            return len(code) > 0
        except Exception as e:
            print(f"⚠️  Error verifying contract {contract_address}: {e}")
            return False

    def _get_checksum_address(self, address: str) -> str:
        """Convert address to checksum format."""
        try:
            from web3 import Web3

            w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
            return w3.to_checksum_address(address)
        except Exception as e:
            print(f"⚠️  Error checksumming address {address}: {e}")
            return address

    def get_contract_info(
        self, contract_name: str, environment: str = "local"
    ) -> Optional[ContractInfo]:
        """Get information for a specific contract."""
        contracts = self.discover_contracts(environment)
        return contracts.get(contract_name)

    def get_contract_address(self, contract_name: str, environment: str = "local") -> Optional[str]:
        """Get the deployed address for a specific contract."""
        contract_info = self.get_contract_info(contract_name, environment)
        return contract_info.address if contract_info else None

    def get_contract_abi(
        self, contract_name: str, environment: str = "local"
    ) -> List[Dict[str, Any]]:
        """Get the ABI for a specific contract."""
        contract_info = self.get_contract_info(contract_name, environment)
        return contract_info.abi if contract_info else []


def discover_contracts(
    environment: str = "local", project_root: Optional[str] = None
) -> Dict[str, ContractInfo]:
    """
    Convenience function to discover all contracts.

    Args:
        environment: Environment name (local, dev, staging, production)
        project_root: Optional project root path

    Returns:
        Dictionary mapping contract names to ContractInfo objects
    """
    discovery = ContractDiscovery(project_root)
    return discovery.discover_contracts(environment)


def get_contract_address(
    contract_name: str, environment: str = "local", project_root: Optional[str] = None
) -> Optional[str]:
    """
    Convenience function to get a contract address.

    Args:
        contract_name: Name of the contract (e.g., "EscrowFactory")
        environment: Environment name
        project_root: Optional project root path

    Returns:
        Contract address or None if not found
    """
    discovery = ContractDiscovery(project_root)
    return discovery.get_contract_address(contract_name, environment)


def get_contract_abi(
    contract_name: str, environment: str = "local", project_root: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to get a contract ABI.

    Args:
        contract_name: Name of the contract (e.g., "EscrowFactory")
        environment: Environment name
        project_root: Optional project root path

    Returns:
        Contract ABI or empty list if not found
    """
    discovery = ContractDiscovery(project_root)
    return discovery.get_contract_abi(contract_name, environment)
