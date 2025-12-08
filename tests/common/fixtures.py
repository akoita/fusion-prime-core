"""
Shared pytest fixtures for all test types.

This module provides common fixtures that can be used across
local, remote, and integration tests.
"""

from typing import Any, Generator

import pytest
from web3 import Web3

from .config import test_config
from .environment_manager import Environment, EnvironmentManager


@pytest.fixture(scope="session")
def env_manager() -> EnvironmentManager:
    """Get environment manager instance."""
    return EnvironmentManager()


@pytest.fixture(scope="session")
def test_config_instance():
    """Get test configuration instance."""
    return test_config


@pytest.fixture
def web3_client_fixture(env_manager: EnvironmentManager) -> Generator[Web3, None, None]:
    """Get Web3 client for current environment."""
    web3 = env_manager.get_web3_client()
    yield web3


@pytest.fixture
def db_connection_fixture(
    env_manager: EnvironmentManager,
) -> Generator[Any, None, None]:
    """Get database connection for current environment."""
    conn = env_manager.get_database_connection()
    yield conn
    conn.close()


@pytest.fixture
def settlement_service_fixture(env_manager: EnvironmentManager) -> str:
    """Get settlement service URL for current environment."""
    return env_manager._env_config.services.settlement


@pytest.fixture
def escrow_factory_contract_fixture(web3_client_fixture: Web3, env_manager: EnvironmentManager):
    """Get deployed EscrowFactory contract."""
    from .helpers import get_escrow_factory_contract

    # For remote environments, get contract address from config
    if not env_manager.is_local_environment():
        factory_address = test_config.get_contract_address(
            env_manager._current_env.value, "escrow_factory"
        )
        if factory_address:
            abi = [
                {
                    "inputs": [
                        {"internalType": "address", "name": "payee", "type": "address"},
                        {
                            "internalType": "uint256",
                            "name": "releaseDelay",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint8",
                            "name": "approvalsRequired",
                            "type": "uint8",
                        },
                        {
                            "internalType": "address",
                            "name": "arbiter",
                            "type": "address",
                        },
                    ],
                    "name": "createEscrow",
                    "outputs": [{"internalType": "address", "name": "escrow", "type": "address"}],
                    "stateMutability": "payable",
                    "type": "function",
                },
                {
                    "anonymous": False,
                    "inputs": [
                        {"indexed": True, "name": "escrow", "type": "address"},
                        {"indexed": True, "name": "payer", "type": "address"},
                        {"indexed": True, "name": "payee", "type": "address"},
                        {"indexed": False, "name": "amount", "type": "uint256"},
                        {"indexed": False, "name": "releaseDelay", "type": "uint256"},
                        {
                            "indexed": False,
                            "name": "approvalsRequired",
                            "type": "uint8",
                        },
                    ],
                    "name": "EscrowDeployed",
                    "type": "event",
                },
            ]
            return web3_client_fixture.eth.contract(address=factory_address, abi=abi)

    # Fallback to local deployment logic
    return get_escrow_factory_contract(web3_client_fixture)


@pytest.fixture
def test_accounts_fixture(web3_client_fixture: Web3, env_manager: EnvironmentManager) -> list:
    """Get test accounts for current environment."""
    if env_manager.is_local_environment():
        # Use Anvil's pre-funded accounts
        return web3_client_fixture.eth.accounts[:5]
    else:
        # Use configured test accounts
        test_data = test_config.get_test_data(env_manager._current_env.value)
        return test_data.get("test_accounts", [])


@pytest.fixture
def test_amount_fixture(env_manager: EnvironmentManager) -> float:
    """Get test amount for current environment."""
    test_data = test_config.get_test_data(env_manager._current_env.value)
    return test_data.get("test_amount", 0.01)


@pytest.fixture
def pubsub_clients_fixture(env_manager: EnvironmentManager):
    """Get Pub/Sub clients for current environment."""
    return env_manager.get_pubsub_client()


# Environment-specific fixtures
@pytest.fixture
def local_environment_fixture(env_manager: EnvironmentManager):
    """Set up local environment."""
    env_manager.set_environment(Environment.LOCAL)
    yield env_manager._env_config


@pytest.fixture
def testnet_environment_fixture(env_manager: EnvironmentManager):
    """Set up testnet environment."""
    env_manager.set_environment(Environment.TESTNET)
    yield env_manager._env_config


@pytest.fixture
def production_environment_fixture(env_manager: EnvironmentManager):
    """Set up production environment."""
    env_manager.set_environment(Environment.PRODUCTION)
    yield env_manager._env_config


# Test data fixtures
@pytest.fixture
def escrow_test_data_fixture(test_config_instance):
    """Get escrow test data."""
    return test_config_instance.get_test_fixtures()["test_data"]["escrow_configs"]


@pytest.fixture
def command_test_data_fixture(test_config_instance):
    """Get command test data."""
    return test_config_instance.get_test_fixtures()["generators"]["command_data"]


# Performance testing fixtures
@pytest.fixture
def performance_config_fixture(test_config_instance):
    """Get performance testing configuration."""
    return test_config_instance.get_thresholds()


# Security testing fixtures
@pytest.fixture
def security_headers_fixture():
    """Get expected security headers."""
    return [
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "X-XSS-Protection",
    ]
