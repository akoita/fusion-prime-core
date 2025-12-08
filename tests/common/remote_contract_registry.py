"""
Remote Contract Registry

Handles contract discovery for remote environments (dev, staging, production).
In professional environments, deployed contract information is typically stored
in a centralized registry (GCP bucket, deployment database, etc.) that can be
accessed by all services and applications.

This module provides the interface for remote contract discovery.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class RemoteContractInfo:
    """Information about a remotely deployed contract."""

    name: str
    address: str
    abi: List[Dict[str, Any]]
    deployment_tx: str
    block_number: int
    chain_id: int
    environment: str
    deployed_at: str
    version: str


class RemoteContractRegistry:
    """Manages contract information for remote environments."""

    def __init__(self, project_id: str, bucket_name: Optional[str] = None):
        self.project_id = project_id
        self.bucket_name = bucket_name or f"{project_id}-contract-registry"
        self.registry_path = f"gs://{self.bucket_name}/contracts"

    def get_contract_info(
        self, contract_name: str, environment: str
    ) -> Optional[RemoteContractInfo]:
        """
        Get contract information from remote registry.

        Args:
            contract_name: Name of the contract (e.g., "EscrowFactory")
            environment: Environment name (dev, staging, production)

        Returns:
            RemoteContractInfo or None if not found
        """
        # TODO: Implement GCP bucket access
        # This would read from: gs://bucket/contracts/{environment}/{contract_name}.json
        print(
            f"⚠️  Remote contract registry not yet implemented for {contract_name} in {environment}"
        )
        return None

    def list_contracts(self, environment: str) -> List[str]:
        """
        List all deployed contracts for an environment.

        Args:
            environment: Environment name

        Returns:
            List of contract names
        """
        # TODO: Implement GCP bucket listing
        print(f"⚠️  Remote contract listing not yet implemented for {environment}")
        return []

    def get_latest_deployment(self, environment: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest deployment information for an environment.

        Args:
            environment: Environment name

        Returns:
            Latest deployment info or None
        """
        # TODO: Implement latest deployment retrieval
        print(f"⚠️  Latest deployment retrieval not yet implemented for {environment}")
        return None


class LocalContractRegistry:
    """Manages contract information for local development."""

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root or os.getcwd())
        self.contracts_dir = self.project_root / "contracts"
        self.deployments_dir = self.contracts_dir / "deployments"

    def get_contract_info(
        self, contract_name: str, environment: str = "local"
    ) -> Optional[RemoteContractInfo]:
        """
        Get contract information from local deployment artifacts.

        Args:
            contract_name: Name of the contract
            environment: Environment name (always "local" for this registry)

        Returns:
            RemoteContractInfo or None if not found
        """
        # Read from deployments directory
        chain_id = self._get_chain_id_for_environment(environment)
        deployment_file = self.deployments_dir / f"{chain_id}-{environment}.json"

        if not deployment_file.exists():
            return None

        try:
            with open(deployment_file, "r") as f:
                deployment_data = json.load(f)

            # Extract contract information
            contracts = deployment_data.get("contracts", {})
            if contract_name not in contracts:
                return None

            contract_data = contracts[contract_name]

            return RemoteContractInfo(
                name=contract_name,
                address=contract_data.get("address", ""),
                abi=contract_data.get("abi", []),
                deployment_tx=contract_data.get("transactionHash", ""),
                block_number=contract_data.get("blockNumber", 0),
                chain_id=chain_id,
                environment=environment,
                deployed_at=contract_data.get("deployedAt", ""),
                version=contract_data.get("version", "1.0.0"),
            )

        except Exception as e:
            print(f"⚠️  Error reading deployment file {deployment_file}: {e}")
            return None

    def _get_chain_id_for_environment(self, environment: str) -> int:
        """Get chain ID for environment."""
        chain_ids = {
            "local": 31337,
            "dev": 11155111,  # Sepolia
            "staging": 11155111,  # Sepolia
            "production": 1,  # Mainnet
        }
        return chain_ids.get(environment, 31337)


def get_contract_registry(
    environment: str, project_id: Optional[str] = None
) -> RemoteContractRegistry:
    """
    Get the appropriate contract registry for the environment.

    Args:
        environment: Environment name
        project_id: GCP project ID for remote environments

    Returns:
        Contract registry instance
    """
    if environment == "local":
        return LocalContractRegistry()
    else:
        if not project_id:
            project_id = os.getenv("GCP_PROJECT", "fusion-prime")
        return RemoteContractRegistry(project_id)


def get_contract_address(
    contract_name: str, environment: str, project_id: Optional[str] = None
) -> Optional[str]:
    """
    Get contract address for any environment.

    Args:
        contract_name: Name of the contract
        environment: Environment name
        project_id: GCP project ID for remote environments

    Returns:
        Contract address or None if not found
    """
    registry = get_contract_registry(environment, project_id)
    contract_info = registry.get_contract_info(contract_name, environment)
    return contract_info.address if contract_info else None


def get_contract_abi(
    contract_name: str, environment: str, project_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get contract ABI for any environment.

    Args:
        contract_name: Name of the contract
        environment: Environment name
        project_id: GCP project ID for remote environments

    Returns:
        Contract ABI or empty list if not found
    """
    registry = get_contract_registry(environment, project_id)
    contract_info = registry.get_contract_info(contract_name, environment)
    return contract_info.abi if contract_info else []
