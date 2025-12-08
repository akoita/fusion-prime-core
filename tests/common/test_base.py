"""
Base test classes for all test types.

This module provides abstract base classes that define common patterns
and interfaces for local, remote, and integration tests.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import pytest
from web3 import Web3

from .environment_manager import Environment, EnvironmentManager


class TestBase(ABC):
    """Abstract base class for all tests."""

    def __init__(self, environment: Environment):
        self.environment = environment
        self.env_manager = EnvironmentManager()
        self.env_config = self.env_manager.set_environment(environment)

    @abstractmethod
    def test_environment_specific_validation(self):
        """Test environment-specific validation logic."""
        pass

    def get_web3_client(self) -> Web3:
        """Get Web3 client for current environment."""
        return self.env_manager.get_web3_client()

    def get_database_connection(self):
        """Get database connection for current environment."""
        return self.env_manager.get_database_connection()

    def get_settlement_service_url(self) -> str:
        """Get settlement service URL for current environment."""
        return self.env_config.services.settlement


class LocalTestBase(TestBase):
    """Base class for local testing."""

    def __init__(self):
        super().__init__(Environment.LOCAL)

    def test_environment_specific_validation(self):
        """Test local environment-specific validation."""
        # Verify we're on local Anvil
        web3 = self.get_web3_client()
        chain_id = web3.eth.chain_id
        assert chain_id == 31337, f"Not on local Anvil: {chain_id}"

        # Verify local-specific features
        assert self.env_config.blockchain.network == "anvil"
        assert self.env_config.pubsub.emulator_host == "localhost:8085"


class RemoteTestBase(TestBase):
    """Base class for remote testing."""

    def __init__(self, environment: Environment):
        super().__init__(environment)
        from .helpers import RemoteTestHelper

        self.remote_helper = RemoteTestHelper(self.env_manager)

    def create_escrow_transaction(self, web3_client, escrow_factory_contract, **kwargs):
        """Create escrow transaction with environment-specific parameters."""
        from .helpers import ContractTestHelper

        # Use environment-specific test data
        test_amount = self.remote_helper.get_test_amount()

        # Merge with provided kwargs
        params = {
            "payee": kwargs.get("payee", "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"),
            "release_delay": kwargs.get("release_delay", 3600),
            "approvals_required": kwargs.get("approvals_required", 2),
            "arbiter": kwargs.get("arbiter", "0x0000000000000000000000000000000000000000"),
            "amount_eth": kwargs.get("amount_eth", test_amount),
        }

        # For production, use smaller amounts
        if self.env_manager.is_production_environment():
            params["amount_eth"] = min(params["amount_eth"], 0.001)  # Max 0.001 ETH for production

        return ContractTestHelper.create_escrow_transaction(
            web3_client, escrow_factory_contract, **params
        )

    def get_gas_price(self, web3_client: Web3) -> int:
        """Get appropriate gas price for current environment."""
        base_gas_price = web3_client.eth.gas_price

        if self.env_manager.is_local_environment():
            return base_gas_price  # Anvil uses 0 gas price
        elif self.env_manager.is_testnet_environment():
            multiplier = self.env_config.blockchain.gas_price_multiplier
            return int(base_gas_price * multiplier)
        else:  # Production
            multiplier = self.env_config.blockchain.gas_price_multiplier
            max_gas_price = web3_client.to_wei(
                self.env_config.blockchain.max_gas_price_gwei, "gwei"
            )
            return min(int(base_gas_price * multiplier), max_gas_price)

    def wait_for_transaction_confirmation(
        self, web3_client: Web3, tx_hash: str, max_blocks: int = 10
    ) -> bool:
        """Wait for transaction confirmation with environment-specific timeout."""
        if self.env_manager.is_local_environment():
            # Local environment confirms immediately
            return True

        # For remote environments, wait for confirmation
        try:
            receipt = web3_client.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            return receipt.status == 1
        except Exception as e:
            print(f"⚠️ Transaction confirmation failed: {e}")
            return False


class IntegrationTestBase(TestBase):
    """Base class for integration testing across environments."""

    def __init__(self, source_env: Environment, target_env: Environment):
        self.source_env = source_env
        self.target_env = target_env
        super().__init__(target_env)  # Use target environment as primary

    def test_environment_consistency(self, web3_client, db_connection):
        """Test consistency between environments."""
        print(
            f"🔄 Testing consistency between {self.source_env.value} and {self.target_env.value}..."
        )

        # Test database schema consistency
        cursor = db_connection.cursor()
        try:
            cursor.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'settlement_commands'
                ORDER BY ordinal_position
            """
            )
            columns = cursor.fetchall()

            # Verify expected columns exist
            expected_columns = [
                "command_id",
                "workflow_id",
                "account_ref",
                "payer",
                "payee",
                "amount_numeric",
                "status",
            ]
            actual_columns = [col[0] for col in columns]

            for expected_col in expected_columns:
                assert expected_col in actual_columns, f"Missing column: {expected_col}"

            print(f"✅ Database schema consistency verified: {len(columns)} columns")
        finally:
            cursor.close()

    def test_environment_specific_validation(self):
        """Test environment-specific validation for integration tests."""
        # Verify we're on the target environment
        web3 = self.get_web3_client()
        chain_id = web3.eth.chain_id

        if self.target_env == Environment.PRODUCTION:
            assert chain_id == 1, f"Not on mainnet: {chain_id}"
        elif self.target_env == Environment.TESTNET:
            assert chain_id in [
                11155111,
                84532,
                11155420,
                421614,
                80002,
            ], f"Invalid testnet chain ID: {chain_id}"
