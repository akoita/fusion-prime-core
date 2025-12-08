"""
Test configuration management.

This module provides centralized configuration management for all test types,
handling environment-specific settings and test data.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class TestConfig:
    """Centralized test configuration management."""

    def __init__(self, config_dir: str = "tests/config"):
        self.config_dir = Path(config_dir)
        self._config_cache = {}

    def load_config(self, config_name: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if config_name in self._config_cache:
            return self._config_cache[config_name]

        config_file = self.config_dir / f"{config_name}.yaml"
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        # Substitute environment variables
        config = self._substitute_env_vars(config)

        self._config_cache[config_name] = config
        return config

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

    def get_environment_config(self, environment: str) -> Dict[str, Any]:
        """Get environment-specific configuration."""
        config = self.load_config("environments")
        return config.get("environment", {}).get(environment, {})

    def get_test_categories(self) -> Dict[str, Any]:
        """Get test category definitions."""
        return self.load_config("test_categories")

    def get_test_fixtures(self) -> Dict[str, Any]:
        """Get test data fixtures."""
        return self.load_config("fixtures")

    def get_contract_address(self, environment: str, contract_name: str) -> str:
        """Get contract address for specific environment."""
        env_config = self.get_environment_config(environment)
        contracts = env_config.get("contracts", {})
        return contracts.get(contract_name, "")

    def get_service_url(self, environment: str, service_name: str) -> str:
        """Get service URL for specific environment."""
        env_config = self.get_environment_config(environment)
        services = env_config.get("services", {})
        return services.get(service_name, "")

    def get_database_config(self, environment: str) -> Dict[str, Any]:
        """Get database configuration for specific environment."""
        env_config = self.get_environment_config(environment)
        return env_config.get("database", {})

    def get_blockchain_config(self, environment: str) -> Dict[str, Any]:
        """Get blockchain configuration for specific environment."""
        env_config = self.get_environment_config(environment)
        return env_config.get("blockchain", {})

    def get_pubsub_config(self, environment: str) -> Dict[str, Any]:
        """Get Pub/Sub configuration for specific environment."""
        env_config = self.get_environment_config(environment)
        return env_config.get("pubsub", {})

    def get_test_data(self, environment: str) -> Dict[str, Any]:
        """Get test data for specific environment."""
        env_config = self.get_environment_config(environment)
        return env_config.get("test_data", {})

    def get_thresholds(self) -> Dict[str, Any]:
        """Get test thresholds and limits."""
        config = self.load_config("environments")
        return config.get("thresholds", {})

    def is_local_environment(self, environment: str) -> bool:
        """Check if environment is local."""
        return environment == "local"

    def is_remote_environment(self, environment: str) -> bool:
        """Check if environment is remote."""
        return environment in ["testnet", "production"]

    def get_environment_type(self, environment: str) -> str:
        """Get environment type (local, testnet, production)."""
        if self.is_local_environment(environment):
            return "local"
        elif environment == "testnet":
            return "testnet"
        elif environment == "production":
            return "production"
        else:
            return "unknown"


# Global configuration instance
test_config = TestConfig()
