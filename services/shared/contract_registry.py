"""
GCP Contract Registry Integration

This module provides utilities for services to load smart contract resources
(addresses, ABIs, metadata) from the GCP contract registry.

Usage:
    from contract_registry import ContractRegistry

    registry = ContractRegistry()
    factory_address = registry.get_contract_address('EscrowFactory')
    factory_abi = registry.get_contract_abi('EscrowFactory')
"""

import json
import os
from typing import Any, Dict, List, Optional

from google.cloud import storage
from google.cloud.exceptions import NotFound


class ContractRegistry:
    """Manages smart contract resources from GCP contract registry."""

    def __init__(self, project_id: Optional[str] = None, bucket_name: Optional[str] = None):
        """
        Initialize contract registry.

        Args:
            project_id: GCP project ID (defaults to GCP_PROJECT env var)
            bucket_name: GCS bucket name (defaults to CONTRACT_REGISTRY_BUCKET env var)
        """
        self.project_id = project_id or os.getenv("GCP_PROJECT")
        self.bucket_name = bucket_name or os.getenv("CONTRACT_REGISTRY_BUCKET")
        # Environment is deduced from the deployment context, not a separate env var
        self.environment = os.getenv("CONTRACT_REGISTRY_ENV") or self._detect_environment()
        self.chain_id = os.getenv("CONTRACT_REGISTRY_CHAIN_ID", "11155111")

        if not self.bucket_name:
            raise ValueError("Contract registry bucket name not specified")

        self.client = storage.Client(project=self.project_id)
        self.bucket = self.client.bucket(self.bucket_name)

        # Cache for loaded ABIs
        self._abi_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._metadata_cache: Optional[Dict[str, Any]] = None

    def _detect_environment(self) -> str:
        """Detect environment from context or default to 'dev'."""
        # Try to detect from GCP project name patterns
        if self.project_id:
            if "prod" in self.project_id.lower():
                return "production"
            elif "staging" in self.project_id.lower():
                return "staging"
            elif "dev" in self.project_id.lower():
                return "dev"

        # Try to detect from ABI URLs
        factory_abi_url = os.getenv("ESCROW_FACTORY_ABI_URL", "")
        if "production" in factory_abi_url:
            return "production"
        elif "staging" in factory_abi_url:
            return "staging"
        elif "dev" in factory_abi_url:
            return "dev"

        # Default to dev
        return "dev"

    def get_contract_address(self, contract_name: str) -> str:
        """
        Get contract address from environment variables.

        Args:
            contract_name: Name of the contract (e.g., 'EscrowFactory')

        Returns:
            Contract address

        Raises:
            ValueError: If contract address not found
        """
        env_var = f"{contract_name.upper()}_ADDRESS"
        address = os.getenv(env_var)

        if not address:
            raise ValueError(
                f"Contract address not found for {contract_name}. "
                f"Set {env_var} environment variable."
            )

        return address

    def get_contract_abi(self, contract_name: str) -> List[Dict[str, Any]]:
        """
        Load contract ABI from GCS.

        Args:
            contract_name: Name of the contract (e.g., 'EscrowFactory')

        Returns:
            Contract ABI as list of dictionaries

        Raises:
            ValueError: If ABI not found or invalid
        """
        # Check cache first
        if contract_name in self._abi_cache:
            return self._abi_cache[contract_name]

        # Try to load from GCS URL first
        abi_url = os.getenv(f"{contract_name.upper()}_ABI_URL")
        if abi_url:
            abi = self._load_abi_from_gcs_url(abi_url)
            self._abi_cache[contract_name] = abi
            return abi

        # Fallback to local ABI path
        abi_path = os.getenv(f"{contract_name.upper()}_ABI_PATH")
        if abi_path:
            abi = self._load_abi_from_file(abi_path)
            self._abi_cache[contract_name] = abi
            return abi

        # Try to load from contract registry
        abi = self._load_abi_from_registry(contract_name)
        if abi:
            self._abi_cache[contract_name] = abi
            return abi

        raise ValueError(
            f"Contract ABI not found for {contract_name}. "
            f"Set {contract_name.upper()}_ABI_URL or {contract_name.upper()}_ABI_PATH "
            f"environment variable."
        )

    def get_contract_info(self, contract_name: str) -> Dict[str, Any]:
        """
        Get comprehensive contract information.

        Args:
            contract_name: Name of the contract

        Returns:
            Dictionary with contract address, ABI, and metadata
        """
        return {
            "name": contract_name,
            "address": self.get_contract_address(contract_name),
            "abi": self.get_contract_abi(contract_name),
            "environment": self.environment,
            "chain_id": self.chain_id,
        }

    def get_deployment_metadata(self) -> Dict[str, Any]:
        """
        Get deployment metadata from contract registry.

        Returns:
            Deployment metadata dictionary
        """
        if self._metadata_cache:
            return self._metadata_cache

        metadata_path = f"contracts/{self.environment}/{self.chain_id}/metadata.json"
        blob = self.bucket.blob(metadata_path)

        try:
            metadata_json = blob.download_as_text()
            self._metadata_cache = json.loads(metadata_json)
            return self._metadata_cache
        except NotFound:
            raise ValueError(f"Deployment metadata not found at {metadata_path}")
        except Exception as e:
            raise ValueError(f"Failed to load deployment metadata: {e}")

    def list_available_contracts(self) -> List[str]:
        """
        List all available contracts for current environment.

        Returns:
            List of contract names
        """
        try:
            metadata = self.get_deployment_metadata()
            return list(metadata.get("contracts", {}).keys())
        except ValueError:
            # Fallback to environment variables
            contracts = []
            for key, value in os.environ.items():
                if key.endswith("_ADDRESS") and value:
                    contract_name = key[:-8]  # Remove '_ADDRESS' suffix
                    contracts.append(contract_name)
            return contracts

    def _load_abi_from_gcs_url(self, gcs_url: str) -> List[Dict[str, Any]]:
        """Load ABI from GCS URL."""
        try:
            # Parse GCS URL: gs://bucket/path/to/file.json
            if not gcs_url.startswith("gs://"):
                raise ValueError(f"Invalid GCS URL: {gcs_url}")

            path_parts = gcs_url[5:].split("/", 1)  # Remove 'gs://' and split
            if len(path_parts) != 2:
                raise ValueError(f"Invalid GCS URL format: {gcs_url}")

            bucket_name, blob_name = path_parts
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(blob_name)

            abi_json = blob.download_as_text()
            abi_data = json.loads(abi_json)

            # Handle different ABI formats
            if isinstance(abi_data, list):
                return abi_data
            elif isinstance(abi_data, dict) and "abi" in abi_data:
                return abi_data["abi"]
            else:
                raise ValueError(f"Invalid ABI format in {gcs_url}")

        except Exception as e:
            raise ValueError(f"Failed to load ABI from {gcs_url}: {e}")

    def _load_abi_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Load ABI from local file."""
        try:
            with open(file_path, "r") as f:
                abi_data = json.load(f)

            # Handle different ABI formats
            if isinstance(abi_data, list):
                return abi_data
            elif isinstance(abi_data, dict) and "abi" in abi_data:
                return abi_data["abi"]
            else:
                raise ValueError(f"Invalid ABI format in {file_path}")

        except Exception as e:
            raise ValueError(f"Failed to load ABI from {file_path}: {e}")

    def _load_abi_from_registry(self, contract_name: str) -> Optional[List[Dict[str, Any]]]:
        """Load ABI from contract registry."""
        try:
            abi_path = f"contracts/{self.environment}/{self.chain_id}/{contract_name}.json"
            blob = self.bucket.blob(abi_path)
            abi_json = blob.download_as_text()
            abi_data = json.loads(abi_json)

            # Handle different ABI formats
            if isinstance(abi_data, list):
                return abi_data
            elif isinstance(abi_data, dict) and "abi" in abi_data:
                return abi_data["abi"]
            else:
                return None

        except (NotFound, Exception):
            return None

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on contract registry.

        Returns:
            Health check results
        """
        health = {"status": "healthy", "contracts": {}, "errors": []}

        try:
            # Check if we can access the bucket
            self.bucket.reload()

            # Check each available contract
            for contract_name in self.list_available_contracts():
                try:
                    address = self.get_contract_address(contract_name)
                    abi = self.get_contract_abi(contract_name)

                    health["contracts"][contract_name] = {
                        "address": address,
                        "abi_loaded": len(abi) > 0,
                        "status": "healthy",
                    }
                except Exception as e:
                    health["contracts"][contract_name] = {"status": "unhealthy", "error": str(e)}
                    health["errors"].append(f"{contract_name}: {e}")

            if health["errors"]:
                health["status"] = "unhealthy"

        except Exception as e:
            health["status"] = "unhealthy"
            health["errors"].append(f"Registry access failed: {e}")

        return health


# Convenience functions for common operations
def get_contract_address(contract_name: str) -> str:
    """Get contract address for a given contract name."""
    registry = ContractRegistry()
    return registry.get_contract_address(contract_name)


def get_contract_abi(contract_name: str) -> List[Dict[str, Any]]:
    """Get contract ABI for a given contract name."""
    registry = ContractRegistry()
    return registry.get_contract_abi(contract_name)


def get_contract_info(contract_name: str) -> Dict[str, Any]:
    """Get comprehensive contract information."""
    registry = ContractRegistry()
    return registry.get_contract_info(contract_name)


def health_check() -> Dict[str, Any]:
    """Perform contract registry health check."""
    registry = ContractRegistry()
    return registry.health_check()
