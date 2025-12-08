#!/usr/bin/env python3
"""
Load chain configuration from environment variables.

This script reads chain configuration from .env files and provides
a clean interface for deployment scripts.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional


def load_env_file(env_path: Path) -> Dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}

    if not env_path.exists():
        return env_vars

    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

    return env_vars


def get_chain_config(chain_name: str) -> Dict[str, str]:
    """Get configuration for a specific chain."""
    # Load from chains.env
    chains_env_path = Path(__file__).parent.parent / "config" / "chains.env"
    chains_config = load_env_file(chains_env_path)

    # Build chain-specific config
    chain_config = {}
    chain_upper = chain_name.upper().replace("-", "_")

    # Map chain name to config keys
    key_mappings = {
        "chain_id": f"{chain_upper}_CHAIN_ID",
        "chain_name": f"{chain_upper}_CHAIN_NAME",
        "rpc_url": f"{chain_upper}_RPC_URL",
        "is_testnet": f"{chain_upper}_IS_TESTNET",
        "is_mainnet": f"{chain_upper}_IS_MAINNET",
        "is_local": f"{chain_upper}_IS_LOCAL",
    }

    for config_key, env_key in key_mappings.items():
        value = chains_config.get(env_key, "")
        # Resolve environment variable references
        if value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            value = os.getenv(env_var, value)
        chain_config[config_key] = value

    return chain_config


def get_supported_chains() -> List[str]:
    """Get list of supported chain names."""
    chains_env_path = Path(__file__).parent.parent / "config" / "chains.env"
    chains_config = load_env_file(chains_env_path)

    supported_names = chains_config.get("SUPPORTED_CHAIN_NAMES", "")
    return [name.strip() for name in supported_names.split(",") if name.strip()]


def get_chain_by_id(chain_id: int) -> Optional[Dict[str, str]]:
    """Get chain configuration by chain ID."""
    for chain_name in get_supported_chains():
        config = get_chain_config(chain_name)
        if config.get("chain_id") == str(chain_id):
            return config
    return None


def print_chain_info(chain_name: str):
    """Print chain information."""
    config = get_chain_config(chain_name)

    print(f"🌐 Chain: {chain_name}")
    print(f"   ID: {config.get('chain_id', 'N/A')}")
    print(f"   Name: {config.get('chain_name', 'N/A')}")
    print(f"   RPC: {config.get('rpc_url', 'N/A')}")
    print(f"   Testnet: {config.get('is_testnet', 'N/A')}")
    print(f"   Mainnet: {config.get('is_mainnet', 'N/A')}")
    print(f"   Local: {config.get('is_local', 'N/A')}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python load_chain_config.py <chain_name>")
        print("Available chains:", ", ".join(get_supported_chains()))
        sys.exit(1)

    chain_name = sys.argv[1]
    print_chain_info(chain_name)


if __name__ == "__main__":
    main()
