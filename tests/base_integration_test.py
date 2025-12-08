"""
Base Integration Test Class for Fusion Prime

Provides common setup and utilities for all integration tests.
Works with both LOCAL (Docker Compose) and REMOTE (Cloud Run) environments.

Automatically loads environment-specific configuration from tests/config/environments.yaml
"""

import os

import pytest
from web3 import Web3
from web3.providers import LegacyWebSocketProvider

from tests.common.environment_loader import auto_load_environment


class BaseIntegrationTest:
    """Base class for integration tests with automatic environment configuration."""

    def setup_method(self):
        """Setup test environment with automatic configuration loading."""
        # Automatically load environment configuration
        self.env_loader = auto_load_environment()
        self.environment = self.env_loader.environment

        # Get configuration from loaded environment
        blockchain_config = self.env_loader.get_blockchain_config()
        contract_config = self.env_loader.get_contract_addresses()
        service_config = self.env_loader.get_service_urls()
        pubsub_config = self.env_loader.get_pubsub_config()
        account_config = self.env_loader.get_test_accounts()

        # Set up test configuration
        self.rpc_url = os.getenv("ETH_RPC_URL")
        self.chain_id = int(os.getenv("CHAIN_ID", "31337"))
        self.factory_address = os.getenv("ESCROW_FACTORY_ADDRESS")
        self.factory_abi_path = os.getenv("ESCROW_FACTORY_ABI_PATH")

        # Service URLs
        self.settlement_url = os.getenv("SETTLEMENT_SERVICE_URL")
        self.risk_engine_url = os.getenv("RISK_ENGINE_SERVICE_URL")
        self.compliance_url = os.getenv("COMPLIANCE_SERVICE_URL")
        self.relayer_url = os.getenv("RELAYER_SERVICE_URL")

        # Test accounts
        self.payer_private_key = os.getenv("PAYER_PRIVATE_KEY")
        self.payee_address = os.getenv("PAYEE_ADDRESS")

        # Pub/Sub configuration
        self.gcp_project = os.getenv("GCP_PROJECT")
        self.pubsub_topic = os.getenv("PUBSUB_TOPIC")
        self.settlement_subscription = os.getenv("SETTLEMENT_SUBSCRIPTION")

        # Setup Web3 connection
        if self.rpc_url and self.rpc_url.startswith("wss://"):
            self.web3 = Web3(LegacyWebSocketProvider(self.rpc_url))
        elif self.rpc_url:
            self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        else:
            pytest.skip(f"ETH_RPC_URL not set for {self.environment} environment")

        if not self.web3.is_connected():
            pytest.skip(f"Web3 not connected to {self.environment} blockchain at {self.rpc_url}")

        # Load factory contract ABI from file (if address is set)
        self.factory_contract = None
        if self.factory_address:
            try:
                from tests.common.abi_loader import load_escrow_factory_abi

                factory_abi = load_escrow_factory_abi()

                self.factory_contract = self.web3.eth.contract(
                    address=self.factory_address, abi=factory_abi
                )
            except FileNotFoundError as e:
                print(f"⚠️  Factory ABI not found: {e}")
                print("   Contract verification tests will be skipped")

        print(f"\n🔧 Test Configuration ({self.environment.upper()}):")
        print(f"  RPC URL: {self.rpc_url}")
        print(f"  Chain ID: {self.chain_id}")
        print(f"  Settlement Service: {self.settlement_url}")
        print(f"  Risk Engine: {self.risk_engine_url}")
        print(f"  Compliance Service: {self.compliance_url}")
        print(f"  Relayer Service: {self.relayer_url}")
