"""
Environment Manager for Fusion Prime Testing

This module provides environment abstraction for testing across local, testnet, and production environments.
It maximizes reuse of existing test components while handling environment-specific configurations.
"""

import asyncio
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import httpx
import psycopg2
import yaml
from google.cloud import pubsub_v1
from web3 import Web3


class Environment(Enum):
    """Supported testing environments."""

    LOCAL = "local"
    TESTNET = "testnet"
    PRODUCTION = "production"


@dataclass
class BlockchainConfig:
    """Blockchain configuration for an environment."""

    rpc_url: str
    chain_id: int
    network: str
    explorer: Optional[str] = None
    gas_price_multiplier: float = 1.0
    max_gas_price_gwei: float = 100.0


@dataclass
class DatabaseConfig:
    """Database configuration for an environment."""

    url: str
    host: str
    port: int
    database: str
    user: str
    password: str
    ssl_mode: str = "prefer"


@dataclass
class PubSubConfig:
    """Pub/Sub configuration for an environment."""

    project_id: str
    emulator_host: Optional[str] = None
    credentials_path: Optional[str] = None


@dataclass
class ServiceConfig:
    """Service configuration for an environment."""

    settlement: str
    relayer: Optional[str] = None
    timeout: int = 30


@dataclass
class EnvironmentConfig:
    """Complete environment configuration."""

    name: Environment
    blockchain: BlockchainConfig
    database: DatabaseConfig
    pubsub: PubSubConfig
    services: ServiceConfig
    test_data: Dict[str, Any]
    thresholds: Dict[str, Any]


class EnvironmentManager:
    """Manages environment configurations and provides environment-specific clients."""

    def __init__(self, config_path: str = "tests/test_config.yaml"):
        """Initialize environment manager with configuration."""
        self.config_path = config_path
        self.config = self._load_config()
        self._current_env: Optional[Environment] = None
        self._env_config: Optional[EnvironmentConfig] = None

    def _load_config(self) -> Dict[str, Any]:
        """Load test configuration from YAML file."""
        try:
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}")

    def set_environment(self, env: Environment) -> EnvironmentConfig:
        """Set the current environment and return its configuration."""
        self._current_env = env
        self._env_config = self._build_environment_config(env)
        return self._env_config

    def _build_environment_config(self, env: Environment) -> EnvironmentConfig:
        """Build environment configuration from loaded config."""
        env_data = self.config["environment"][env.value]

        # Handle environment variable substitution
        env_data = self._substitute_env_vars(env_data)

        # Build blockchain config
        if "blockchain" in env_data:
            blockchain = BlockchainConfig(**env_data["blockchain"])
        else:
            # Multi-chain testnet configuration
            chains = env_data.get("chains", {})
            if not chains:
                raise ValueError(f"No blockchain configuration found for {env.value}")

            # Use first available chain for now (can be extended for multi-chain testing)
            first_chain = list(chains.values())[0]
            blockchain = BlockchainConfig(**first_chain)

        # Build database config
        db_data = env_data["database"]
        database = DatabaseConfig(
            url=db_data["url"],
            host=db_data.get("host", "localhost"),
            port=db_data.get("port", 5432),
            database=db_data.get("database", "fusion_prime"),
            user=db_data.get("user", "fusion_prime"),
            password=db_data.get("password", ""),
            ssl_mode=db_data.get("ssl_mode", "prefer"),
        )

        # Build Pub/Sub config
        pubsub_data = env_data["pubsub"]
        pubsub = PubSubConfig(
            project_id=pubsub_data["project_id"],
            emulator_host=pubsub_data.get("emulator_host"),
            credentials_path=pubsub_data.get("credentials_path"),
        )

        # Build services config
        services_data = env_data["services"]
        services = ServiceConfig(
            settlement=services_data["settlement"],
            relayer=services_data.get("relayer"),
            timeout=services_data.get("timeout", 30),
        )

        return EnvironmentConfig(
            name=env,
            blockchain=blockchain,
            database=database,
            pubsub=pubsub,
            services=services,
            test_data=self.config.get("test_data", {}),
            thresholds=self.config.get("thresholds", {}),
        )

    def _substitute_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute environment variables in configuration."""
        if isinstance(config, dict):
            return {k: self._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
            env_var = config[2:-1]
            return os.getenv(env_var, config)
        else:
            return config

    def get_web3_client(self) -> Web3:
        """Get Web3 client for current environment."""
        if not self._env_config:
            raise ValueError("No environment set. Call set_environment() first.")

        return Web3(Web3.HTTPProvider(self._env_config.blockchain.rpc_url))

    def get_database_connection(self):
        """Get database connection for current environment."""
        if not self._env_config:
            raise ValueError("No environment set. Call set_environment() first.")

        return psycopg2.connect(
            host=self._env_config.database.host,
            port=self._env_config.database.port,
            database=self._env_config.database.database,
            user=self._env_config.database.user,
            password=self._env_config.database.password,
            sslmode=self._env_config.database.ssl_mode,
        )

    def get_pubsub_client(
        self,
    ) -> Tuple[pubsub_v1.PublisherClient, pubsub_v1.SubscriberClient]:
        """Get Pub/Sub clients for current environment."""
        if not self._env_config:
            raise ValueError("No environment set. Call set_environment() first.")

        # Set up credentials if needed
        if self._env_config.pubsub.credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self._env_config.pubsub.credentials_path

        # Set up emulator if needed
        if self._env_config.pubsub.emulator_host:
            os.environ["PUBSUB_EMULATOR_HOST"] = self._env_config.pubsub.emulator_host

        return pubsub_v1.PublisherClient(), pubsub_v1.SubscriberClient()

    async def check_service_health(self, service_name: str) -> bool:
        """Check if a service is healthy."""
        if not self._env_config:
            raise ValueError("No environment set. Call set_environment() first.")

        service_url = getattr(self._env_config.services, service_name, None)
        if not service_url:
            return False

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{service_url}/health")
                return response.status_code == 200
        except Exception:
            return False

    async def wait_for_services(
        self, services: List[str], max_retries: int = 30, retry_delay: int = 2
    ) -> bool:
        """Wait for services to become healthy."""
        for attempt in range(max_retries):
            all_healthy = True
            for service in services:
                if not await self.check_service_health(service):
                    all_healthy = False
                    break

            if all_healthy:
                return True

            await asyncio.sleep(retry_delay)

        return False

    def get_contract_address(self, contract_name: str) -> str:
        """Get contract address for current environment."""
        if not self._env_config:
            raise ValueError("No environment set. Call set_environment() first.")

        # For now, use the contract addresses from config
        # In a real implementation, you'd fetch from deployment registry
        contracts = self.config.get("contracts", {})
        return contracts.get(contract_name, "")

    def is_local_environment(self) -> bool:
        """Check if current environment is local."""
        return self._current_env == Environment.LOCAL

    def is_testnet_environment(self) -> bool:
        """Check if current environment is testnet."""
        return self._current_env == Environment.TESTNET

    def is_production_environment(self) -> bool:
        """Check if current environment is production."""
        return self._current_env == Environment.PRODUCTION

    def get_gas_price_strategy(self) -> str:
        """Get gas price strategy for current environment."""
        if self.is_local_environment():
            return "fast"  # Anvil can handle fast transactions
        elif self.is_testnet_environment():
            return "standard"  # Testnet should be reasonable
        else:
            return "slow"  # Production should be conservative


class RemoteTestHelper:
    """Helper class for remote testing operations."""

    def __init__(self, env_manager: EnvironmentManager):
        self.env_manager = env_manager
        self.config = env_manager._env_config

    async def deploy_contracts_if_needed(self) -> bool:
        """Deploy contracts if they don't exist in the current environment."""
        if self.env_manager.is_local_environment():
            # Use existing local deployment logic
            from tests.common.helpers import deploy_contracts

            deploy_contracts()
            return True

        # For remote environments, check if contracts are already deployed
        web3 = self.env_manager.get_web3_client()
        factory_address = self.env_manager.get_contract_address("escrow_factory")

        if not factory_address:
            raise ValueError("No contract address configured for current environment")

        # Check if contract exists
        code = web3.eth.get_code(factory_address)
        if len(code) <= 2:  # Empty contract
            raise ValueError(f"Contract not deployed at {factory_address}")

        return True

    async def fund_test_accounts(self, accounts: List[str], amount_eth: float = 1.0) -> bool:
        """Fund test accounts with ETH."""
        if self.env_manager.is_local_environment():
            # Local environment has pre-funded accounts
            return True

        # For remote environments, you'd need to implement funding logic
        # This could involve faucets, pre-funded accounts, or manual funding
        web3 = self.env_manager.get_web3_client()

        # Check if accounts have sufficient balance
        for account in accounts:
            balance = web3.eth.get_balance(account)
            required_balance = web3.to_wei(amount_eth, "ether")

            if balance < required_balance:
                print(f"⚠️ Account {account} needs funding: {web3.from_wei(balance, 'ether')} ETH")
                # In a real implementation, you'd fund the account here
                return False

        return True

    async def cleanup_test_data(self, test_id: str) -> bool:
        """Clean up test data after test completion."""
        if self.env_manager.is_local_environment():
            # Local environment can be reset easily
            return True

        # For remote environments, clean up specific test data
        try:
            conn = self.env_manager.get_database_connection()
            cursor = conn.cursor()

            # Clean up test-specific data
            cursor.execute(
                """
                DELETE FROM settlement_commands
                WHERE command_id LIKE %s
            """,
                (f"{test_id}%",),
            )

            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"⚠️ Failed to cleanup test data: {e}")
            return False

    def get_test_accounts(self) -> List[str]:
        """Get test accounts for current environment."""
        if self.env_manager.is_local_environment():
            # Use Anvil's pre-funded accounts
            web3 = self.env_manager.get_web3_client()
            return web3.eth.accounts[:5]  # First 5 accounts

        # For remote environments, use configured test accounts
        return self.config.test_data.get("test_accounts", [])

    def get_test_amount(self) -> float:
        """Get test amount for current environment."""
        base_amount = self.config.test_data.get("test_amount", 0.01)

        if self.env_manager.is_production_environment():
            # Use smaller amounts for production testing
            return base_amount * 0.1
        else:
            return base_amount
