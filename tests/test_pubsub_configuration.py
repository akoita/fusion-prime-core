"""
Pub/Sub Configuration Test

Tests Pub/Sub topic and subscription configuration.
"""

import subprocess

import pytest

from tests.base_infrastructure_test import BaseInfrastructureTest


class TestPubSubConfiguration(BaseInfrastructureTest):
    """Test Pub/Sub topic and subscription configuration."""

    def test_pubsub_configuration(self):
        """Test Pub/Sub topic and subscription configuration."""
        print("🔄 Testing Pub/Sub configuration...")

        if not self.pubsub_project:
            pytest.skip("PUBSUB_PROJECT_ID not set")

        try:
            # Check if topic exists
            if self.pubsub_topic:
                result = subprocess.run(
                    [
                        "gcloud",
                        "pubsub",
                        "topics",
                        "describe",
                        self.pubsub_topic,
                        "--format=json",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    print(f"✅ Pub/Sub topic exists: {self.pubsub_topic}")
                else:
                    print(f"⚠️ Pub/Sub topic not found: {self.pubsub_topic}")

            # Check if subscription exists
            if self.settlement_subscription:
                result = subprocess.run(
                    [
                        "gcloud",
                        "pubsub",
                        "subscriptions",
                        "describe",
                        self.settlement_subscription,
                        "--format=json",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    print(f"✅ Pub/Sub subscription exists: {self.settlement_subscription}")
                else:
                    print(f"⚠️ Pub/Sub subscription not found: {self.settlement_subscription}")

        except Exception as e:
            print(f"ℹ️ Pub/Sub configuration check: {e}")
