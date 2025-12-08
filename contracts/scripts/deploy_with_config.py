#!/usr/bin/env python3
"""
Deploy contracts using environment-based configuration.

This script loads chain configuration from chains.env and deploys
contracts with the appropriate settings for each environment.
"""

import os
import subprocess
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from contracts.scripts.load_chain_config import get_chain_config, get_supported_chains


def load_chains_env():
    """Load chains.env configuration."""
    chains_env_path = project_root / "contracts" / "config" / "chains.env"

    if not chains_env_path.exists():
        print(f"❌ Chains configuration not found: {chains_env_path}")
        return {}

    env_vars = {}
    with open(chains_env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

    return env_vars


def deploy_to_chain(chain_name: str, rpc_url: str = None):
    """Deploy contracts to a specific chain."""
    print(f"🚀 Deploying to {chain_name}...")

    # Get chain configuration
    chain_config = get_chain_config(chain_name)

    if not chain_config.get("chain_id"):
        print(f"❌ No configuration found for chain: {chain_name}")
        return False

    # Use provided RPC URL or get from config
    if not rpc_url:
        rpc_url = chain_config.get("rpc_url", "")
        if rpc_url.startswith("${") and rpc_url.endswith("}"):
            env_var = rpc_url[2:-1]
            rpc_url = os.getenv(env_var, "")

    if not rpc_url:
        print(f"❌ No RPC URL configured for {chain_name}")
        return False

    # Set up environment
    env = os.environ.copy()
    env["CHAIN_NAME"] = chain_name
    env["CHAIN_ID"] = chain_config["chain_id"]

    # Get private key
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        print("❌ PRIVATE_KEY environment variable not set")
        return False

    # Build deployment command
    cmd = [
        "forge",
        "script",
        "script/DeployMultichain.s.sol:DeployMultichain",
        "--rpc-url",
        rpc_url,
        "--private-key",
        private_key,
        "--broadcast",
        "--legacy",
        "-vvvv",
    ]

    # Add verification for non-local chains
    if chain_name != "local":
        cmd.extend(["--verify"])

    print(f"📋 Command: {' '.join(cmd)}")
    print(f"🌐 RPC: {rpc_url}")
    print(f"⛓️  Chain ID: {chain_config['chain_id']}")

    # Run deployment
    try:
        result = subprocess.run(
            cmd, cwd=project_root / "contracts", env=env, check=True, capture_output=True, text=True
        )

        print("✅ Deployment successful!")
        print(result.stdout)
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Deployment failed: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python deploy_with_config.py <chain_name> [rpc_url]")
        print("Available chains:", ", ".join(get_supported_chains()))
        sys.exit(1)

    chain_name = sys.argv[1]
    rpc_url = sys.argv[2] if len(sys.argv) > 2 else None

    success = deploy_to_chain(chain_name, rpc_url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
