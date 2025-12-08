#!/usr/bin/env python3
"""
Test automatic configuration loading.

This script demonstrates how the automatic configuration system works
without requiring manual environment variable setting.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.common.environment_loader import auto_load_environment


def test_auto_config():
    """Test automatic configuration loading."""
    print("🧪 Testing Automatic Configuration Loading")
    print("=" * 50)

    # Set environment (this is the ONLY thing you need to set!)
    os.environ["TEST_ENVIRONMENT"] = "local"

    # Load configuration automatically
    env_loader = auto_load_environment()

    # Get environment info
    info = env_loader.get_environment_info()

    print(f"🌍 Environment: {info['environment']}")
    print(
        f"⛓️  Blockchain: {info['blockchain']['rpc_url']} (Chain ID: {info['blockchain']['chain_id']})"
    )
    print(f"🏭 Factory: {info['contracts'].get('escrow_factory', 'Not set')}")
    print(f"🏥 Settlement: {info['services'].get('settlement', 'Not set')}")
    print(f"☁️  GCP Project: {info['pubsub']['project_id']}")
    print(f"👤 Payer: {info['accounts'].get('payer_private_key', 'Not set')[:10]}...")

    print("\n✅ Configuration loaded automatically!")
    print("🎯 No manual environment variable setting required!")


if __name__ == "__main__":
    test_auto_config()
