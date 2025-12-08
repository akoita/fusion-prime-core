#!/usr/bin/env python3
"""
Remote test runner.

This script runs remote tests (dev, staging, production) with proper
environment setup and configuration.

Updated: 2025-10-25 - Standardized environment naming
Environments: dev, staging, production
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Load environment variables from .env files
try:
    from dotenv import load_dotenv

    # Load environment-specific .env files
    load_dotenv(".env.dev")
    load_dotenv(".env.staging")
    load_dotenv(".env.production")
except ImportError:
    # dotenv not available, continue without it
    pass

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.common.config import test_config


def display_environment_variables(environment: str):
    """Display essential environment variables for the current test environment."""
    print("\n" + "=" * 60)
    print(f"🌍 ENVIRONMENT CONFIGURATION - {environment.upper()}")
    print("=" * 60)

    # Define essential environment variables by environment
    essential_vars = {
        "dev": [
            "ETH_RPC_URL",
            "CHAIN_ID",
            "DATABASE_URL",
            "SETTLEMENT_SERVICE_URL",
            "ESCROW_FACTORY_ADDRESS",
            "GCP_PROJECT",
        ],
        "staging": [
            "ETH_RPC_URL",
            "CHAIN_ID",
            "DATABASE_URL",
            "SETTLEMENT_SERVICE_URL",
            "ESCROW_FACTORY_ADDRESS",
            "GCP_PROJECT",
        ],
        "production": [
            "ETH_RPC_URL",
            "CHAIN_ID",
            "DATABASE_URL",
            "SETTLEMENT_SERVICE_URL",
            "ESCROW_FACTORY_ADDRESS",
            "GCP_PROJECT",
        ],
    }

    vars_to_show = essential_vars.get(environment, [])

    print("📋 Essential Environment Variables:")
    print("-" * 40)

    for var in vars_to_show:
        value = os.getenv(var)
        if value:
            # Mask sensitive parts of URLs and keys
            if "URL" in var or "KEY" in var or "SECRET" in var:
                if "://" in value:
                    # For URLs, show protocol and domain but mask credentials
                    parts = value.split("://")
                    if len(parts) == 2:
                        protocol = parts[0]
                        rest = parts[1]
                        if "@" in rest:
                            # Has credentials, mask them
                            user_pass, host_path = rest.split("@", 1)
                            masked_value = f"{protocol}://***:***@{host_path}"
                        else:
                            masked_value = value
                    else:
                        masked_value = "***masked***"
                else:
                    # For other sensitive values, show first/last few chars
                    if len(value) > 10:
                        masked_value = f"{value[:4]}...{value[-4:]}"
                    else:
                        masked_value = "***masked***"
            else:
                masked_value = value
            print(f"  ✅ {var:<25} = {masked_value}")
        else:
            print(f"  ❌ {var:<25} = <NOT SET>")

    # Show additional environment info
    print("\n🔧 Additional Environment Info:")
    print("-" * 40)
    print(f"  Python Version: {sys.version.split()[0]}")
    print(f"  Working Directory: {os.getcwd()}")
    print(f"  Environment: {environment}")

    # Show chain-specific info if available
    chain_id = os.getenv("CHAIN_ID")
    rpc_url = os.getenv("ETH_RPC_URL")
    if chain_id and rpc_url:
        print(f"  Target Chain ID: {chain_id}")
        if "sepolia" in rpc_url.lower():
            print(f"  Network: Sepolia Testnet")
        elif "mainnet" in rpc_url.lower() or chain_id == "1":
            print(f"  Network: Ethereum Mainnet")
        elif "base" in rpc_url.lower():
            print(f"  Network: Base")
        elif "polygon" in rpc_url.lower():
            print(f"  Network: Polygon")

    print("=" * 60)
    print()


def run_remote_tests(environment: str, category: str = None, verbose: bool = False):
    """Run remote tests for specified environment."""

    # Validate environment
    valid_environments = ["dev", "staging", "production"]
    if environment not in valid_environments:
        print(f"❌ Invalid environment: {environment}")
        print(f"Valid environments: {', '.join(valid_environments)}")
        return 1

    # Display environment variables at the start
    display_environment_variables(environment)

    # Flush output to ensure it's displayed before subprocess
    import sys

    sys.stdout.flush()

    # Build pytest command
    cmd = ["python", "-m", "pytest"]

    # Add test directory (all remote tests in same directory now)
    test_dir = project_root / "tests" / "remote"
    cmd.append(str(test_dir))

    # Add environment marker
    cmd.extend(["-m", f"remote_{environment}"])

    # Add category filter if specified
    if category:
        cmd.extend(["-m", f"remote_{environment} and {category}"])

    # Add verbose flag
    if verbose:
        cmd.append("-v")

    # Add other useful flags
    cmd.extend(["--tb=short", "--strict-markers", "--disable-warnings"])

    print(f"Running {environment} tests: {' '.join(cmd)}")

    # Check environment variables
    if not check_environment_variables(environment):
        print("❌ Missing required environment variables")
        return 1

    # Run tests
    try:
        result = subprocess.run(cmd, cwd=project_root, check=True)
        print(f"✅ {environment} tests completed successfully")
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"❌ {environment} tests failed with exit code {e.returncode}")
        return e.returncode


def check_environment_variables(environment: str) -> bool:
    """Check if required environment variables are set."""

    required_vars = {
        "dev": ["ETH_RPC_URL", "SETTLEMENT_SERVICE_URL", "GCP_PROJECT"],
        "staging": ["ETH_RPC_URL", "SETTLEMENT_SERVICE_URL", "GCP_PROJECT"],
        "production": ["ETH_RPC_URL", "SETTLEMENT_SERVICE_URL", "GCP_PROJECT"],
    }

    missing_vars = []
    for var in required_vars.get(environment, []):
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing required environment variables for {environment}:")
        for var in missing_vars:
            print(f"  - {var}")
        print(f"\nPlease set these variables or create .env.{environment} file")
        print(f"\nExample:")
        print(f"  export $(cat .env.{environment} | xargs)")
        print(f"  export TEST_ENVIRONMENT={environment}")
        return False

    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run remote tests",
        epilog="""
Examples:
  python tests/scripts/run_remote_tests.py dev
  python tests/scripts/run_remote_tests.py staging --verbose
  python tests/scripts/run_remote_tests.py production --category health
        """,
    )
    parser.add_argument(
        "environment",
        choices=["dev", "staging", "production"],
        help="Environment to test (dev=GCP+Sepolia, staging=GCP+Sepolia, production=GCP+Mainnet)",
    )
    parser.add_argument("--category", help="Test category to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    exit_code = run_remote_tests(
        environment=args.environment, category=args.category, verbose=args.verbose
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
