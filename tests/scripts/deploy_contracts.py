#!/usr/bin/env python3
"""
Local contract deployment script for Fusion Prime.

This script deploys smart contracts to the local Anvil instance for testing.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def check_anvil_running():
    """Check if Anvil is running and accessible."""
    try:
        import requests

        response = requests.post(
            "http://localhost:8545",
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


def deploy_contracts():
    """Deploy contracts to local Anvil instance."""
    print("🔄 Deploying smart contracts to local Anvil...")

    # Check if Anvil is running
    if not check_anvil_running():
        print("❌ Anvil is not running. Please start it with: docker compose up -d anvil")
        return False

    # Set up environment for local deployment
    env = os.environ.copy()
    env.update(
        {
            "PRIVATE_KEY": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",  # Anvil default
            "RPC_URL": "http://localhost:8545",
        }
    )

    # Change to contracts directory
    contracts_dir = project_root / "contracts"

    try:
        # Deploy using Foundry
        print("📦 Running Foundry deployment...")
        cmd = [
            "forge",
            "script",
            "script/DeployMultichain.s.sol:DeployMultichain",
            "--rpc-url",
            "http://localhost:8545",
            "--broadcast",
            "--private-key",
            "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
            "-vvvv",
        ]

        result = subprocess.run(
            cmd, cwd=contracts_dir, env=env, capture_output=True, text=True, timeout=120
        )

        if result.returncode != 0:
            print(f"❌ Deployment failed with return code {result.returncode}")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False

        print("✅ Contracts deployed successfully!")

        # Extract contract addresses from output
        extract_contract_addresses(result.stdout)

        return True

    except subprocess.TimeoutExpired:
        print("❌ Deployment timed out")
        return False
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        return False


def extract_contract_addresses(output):
    """Extract contract addresses from Foundry output."""
    print("\n📋 Contract Addresses:")

    # Look for deployment addresses in the output
    lines = output.split("\n")
    for line in lines:
        if "Factory deployed:" in line:
            address = line.split("Factory deployed:")[-1].strip()
            print(f"  EscrowFactory: {address}")

            # Save to a file for tests to use
            save_contract_addresses({"escrow_factory": address})
            break


def save_contract_addresses(addresses):
    """Save contract addresses to a file for tests to use."""
    addresses_file = project_root / "test-reports" / "contract-addresses.json"
    addresses_file.parent.mkdir(exist_ok=True)

    with open(addresses_file, "w") as f:
        json.dump(addresses, f, indent=2)

    print(f"💾 Contract addresses saved to: {addresses_file}")


def main():
    """Main entry point."""
    print("🚀 Fusion Prime Local Contract Deployment")
    print("=" * 50)

    success = deploy_contracts()

    if success:
        print("\n✅ Deployment completed successfully!")
        print("🎯 Contracts are ready for testing")
        sys.exit(0)
    else:
        print("\n❌ Deployment failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
