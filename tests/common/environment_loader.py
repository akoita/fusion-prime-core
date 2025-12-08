"""
Automatic environment configuration loader.

This module automatically loads the correct configuration for the current
TEST_ENVIRONMENT without requiring manual variable setting.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from .config import test_config
from .contract_discovery import ContractDiscovery


class EnvironmentLoader:
    """Automatically loads environment-specific configuration."""

    def __init__(self):
        self.environment = os.getenv("TEST_ENVIRONMENT", "local").lower()
        self._config = None
        self._load_configuration()

    def _load_configuration(self):
        """Load configuration for the current environment."""
        try:
            self._config = test_config.get_environment_config(self.environment)
        except Exception as e:
            print(f"⚠️  Warning: Could not load config for environment '{self.environment}': {e}")
            self._config = {}

    def get_blockchain_config(self) -> Dict[str, Any]:
        """Get blockchain configuration for current environment."""
        blockchain = self._config.get("blockchain", {})

        # Set environment variables if not already set
        if not os.getenv("ETH_RPC_URL"):
            os.environ["ETH_RPC_URL"] = str(blockchain.get("rpc_url", ""))
        if not os.getenv("CHAIN_ID"):
            os.environ["CHAIN_ID"] = str(blockchain.get("chain_id", ""))

        return blockchain

    def get_contract_addresses(self) -> Dict[str, str]:
        """Get contract addresses for current environment using contract discovery."""
        contracts = {}

        # For local environment, use contract discovery as primary source
        if self.environment == "local":
            try:
                discovery = ContractDiscovery()
                discovered_contracts = discovery.discover_contracts("local")

                # Use discovered contract addresses as primary source
                for contract_name, contract_info in discovered_contracts.items():
                    contracts[f"{contract_name.lower()}_address"] = contract_info.address
                    contracts[f"{contract_name.lower()}_abi"] = (
                        f"contracts/abi/{contract_name}.json"
                    )
                    print(f"🔍 Discovered {contract_name} at {contract_info.address}")

                # Set environment variables from discovered contracts
                if discovered_contracts:
                    escrow_factory = discovered_contracts.get("EscrowFactory")
                    if escrow_factory:
                        os.environ["ESCROW_FACTORY_ADDRESS"] = escrow_factory.address
                        os.environ["ESCROW_FACTORY_ABI_PATH"] = "contracts/abi/EscrowFactory.json"
                        print(f"✅ Set ESCROW_FACTORY_ADDRESS={escrow_factory.address}")

            except Exception as e:
                print(f"⚠️  Contract discovery failed: {e}")
                # For local environment, contract discovery is required
                if self.environment == "local":
                    print(
                        "❌ Local environment requires contract discovery - no fallback available"
                    )
                    return {}
        else:
            # For remote environments, use configuration
            contracts = self._config.get("contracts", {})

            # Set environment variables if not already set
            if not os.getenv("ESCROW_FACTORY_ADDRESS"):
                os.environ["ESCROW_FACTORY_ADDRESS"] = str(contracts.get("escrow_factory", ""))
            if not os.getenv("ESCROW_FACTORY_ABI_PATH"):
                os.environ["ESCROW_FACTORY_ABI_PATH"] = str(contracts.get("escrow_factory_abi", ""))

        return contracts

    def get_service_urls(self) -> Dict[str, str]:
        """Get service URLs for current environment."""
        services = self._config.get("services", {})

        # Set environment variables if not already set
        for service_name, url in services.items():
            env_var = f"{service_name.upper()}_SERVICE_URL"
            if not os.getenv(env_var):
                os.environ[env_var] = str(url)  # Ensure string conversion

        return services

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration for current environment."""
        database = self._config.get("database", {})

        # Set environment variables if not already set
        if not os.getenv("DATABASE_URL"):
            os.environ["DATABASE_URL"] = str(database.get("url", ""))

        return database

    def get_pubsub_config(self) -> Dict[str, Any]:
        """Get Pub/Sub configuration for current environment."""
        pubsub = self._config.get("pubsub", {})

        # Set environment variables if not already set
        if not os.getenv("GCP_PROJECT"):
            os.environ["GCP_PROJECT"] = str(pubsub.get("project_id", ""))
        if not os.getenv("PUBSUB_TOPIC"):
            os.environ["PUBSUB_TOPIC"] = str(pubsub.get("topic", ""))
        if not os.getenv("PUBSUB_EMULATOR_HOST"):
            os.environ["PUBSUB_EMULATOR_HOST"] = str(pubsub.get("emulator_host", ""))

        return pubsub

    def get_test_accounts(self) -> Dict[str, str]:
        """Get test accounts for current environment."""
        accounts = self._config.get("test_accounts", {})

        # Set environment variables if not already set
        if not os.getenv("PAYER_PRIVATE_KEY"):
            os.environ["PAYER_PRIVATE_KEY"] = str(accounts.get("payer_private_key", ""))
        if not os.getenv("PAYEE_ADDRESS"):
            os.environ["PAYEE_ADDRESS"] = str(accounts.get("payee_address", ""))

        return accounts

    def load_all_configuration(self):
        """Load all configuration for the current environment."""
        print(f"🔧 Loading configuration for environment: {self.environment}")

        # Load all configuration sections
        self.get_blockchain_config()
        self.get_contract_addresses()
        self.get_service_urls()
        self.get_database_config()
        self.get_pubsub_config()
        self.get_test_accounts()

        print(f"✅ Configuration loaded for {self.environment}")

    def get_environment_info(self) -> Dict[str, Any]:
        """Get current environment information."""
        return {
            "environment": self.environment,
            "blockchain": self.get_blockchain_config(),
            "contracts": self.get_contract_addresses(),
            "services": self.get_service_urls(),
            "database": self.get_database_config(),
            "pubsub": self.get_pubsub_config(),
            "accounts": self.get_test_accounts(),
        }


# Global environment loader instance
env_loader = EnvironmentLoader()


def auto_load_environment():
    """Automatically load environment configuration."""
    env_loader.load_all_configuration()
    return env_loader


def get_environment_info() -> Dict[str, Any]:
    """Get current environment information."""
    return env_loader.get_environment_info()
