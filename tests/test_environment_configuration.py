"""
Environment Configuration Test

Tests environment configuration completeness for required and optional variables.
"""

import os

import pytest

from tests.base_infrastructure_test import BaseInfrastructureTest


class TestEnvironmentConfiguration(BaseInfrastructureTest):
    """Test environment configuration completeness."""

    def test_environment_configuration(self):
        """Test environment configuration completeness (environment-aware)."""
        print(f"🔄 Testing environment configuration for {self.environment.upper()} environment...")

        if self.environment == "local":
            # Local environment uses defaults from docker-compose
            # Just verify services are configured
            assert self.settlement_url, "Settlement URL should be configured"
            assert self.pubsub_project, "Pub/Sub project should be configured"
            assert self.pubsub_topic, "Pub/Sub topic should be configured"
            assert self.settlement_subscription, "Settlement subscription should be configured"

            print("✅ Local environment configuration valid")
            print(f"   Settlement: {self.settlement_url}")
            print(f"   Pub/Sub Project: {self.pubsub_project}")
            print(f"   Pub/Sub Topic: {self.pubsub_topic}")

            # Note about optional vars
            if not os.getenv("ESCROW_FACTORY_ADDRESS"):
                print("ℹ️  ESCROW_FACTORY_ADDRESS not set - deploy contracts first")

        else:
            # Testnet/production requires explicit env vars
            required_vars = [
                "ETH_RPC_URL",
                "SETTLEMENT_SERVICE_URL",
                "PUBSUB_PROJECT_ID",
                "PUBSUB_TOPIC",
                "SETTLEMENT_SUBSCRIPTION",
            ]

            missing_vars = []
            for var in required_vars:
                if not os.getenv(var):
                    missing_vars.append(var)

            if missing_vars:
                print(f"⚠️ Missing environment variables: {missing_vars}")
            else:
                print("✅ All required environment variables set")

            # Check optional variables
            optional_vars = [
                "ESCROW_FACTORY_ADDRESS",
                "DATABASE_URL",
                "WEBHOOK_URL",
                "PAYER_PRIVATE_KEY",
                "PAYEE_ADDRESS",
            ]

            optional_missing = []
            for var in optional_vars:
                if not os.getenv(var):
                    optional_missing.append(var)

            if optional_missing:
                print(f"ℹ️ Optional variables not set: {optional_missing}")
            else:
                print("✅ All optional environment variables set")

            # Don't fail for missing optional variables
            assert (
                len(missing_vars) == 0
            ), f"Missing required environment variables for {self.environment}: {missing_vars}"
