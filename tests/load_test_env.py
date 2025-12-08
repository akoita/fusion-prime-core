#!/usr/bin/env python3
"""
Load test environment variables from .env.dev file.
Handles special characters in passwords properly.
"""

import os
import sys
from pathlib import Path


def load_env_file(env_file_path: str) -> dict:
    """Load environment variables from .env file, handling special characters."""
    env_vars = {}

    with open(env_file_path, "r") as f:
        for line in f:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Parse KEY=VALUE
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                env_vars[key] = value

    return env_vars


def load_test_environment():
    """Load test environment from .env.dev file."""
    # Find .env.dev file
    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    env_file = project_root / ".env.dev"

    if not env_file.exists():
        print(f"⚠️  Warning: .env.dev not found at {env_file}")
        return

    # Load environment variables
    env_vars = load_env_file(str(env_file))

    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = value

    # Set TEST_ENVIRONMENT
    os.environ["TEST_ENVIRONMENT"] = "dev"

    print(f"✅ Loaded {len(env_vars)} environment variables from .env.dev")

    # Print key variables for verification
    key_vars = [
        "SETTLEMENT_SERVICE_URL",
        "RISK_ENGINE_SERVICE_URL",
        "COMPLIANCE_SERVICE_URL",
        "RPC_URL",
        "ESCROW_FACTORY_ADDRESS",
    ]

    print("\n🔧 Key Environment Variables:")
    for var in key_vars:
        value = os.environ.get(var, "NOT SET")
        # Truncate long values
        if len(value) > 60:
            value = value[:60] + "..."
        print(f"  {var}: {value}")


if __name__ == "__main__":
    load_test_environment()
