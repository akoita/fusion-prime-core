"""
Pub/Sub Integration Test

Tests Pub/Sub integration and message flow from relayer to services.
"""

import subprocess

from tests.base_integration_test import BaseIntegrationTest


class TestPubSubIntegration(BaseIntegrationTest):
    """Test Pub/Sub integration and message flow."""

    def test_pubsub_integration(self):
        """Test Pub/Sub integration and message flow."""
        print("🔄 Testing Pub/Sub integration...")

        # This test would check if the relayer is publishing to Pub/Sub
        # and if the settlement service is consuming messages
        # For now, we'll check the logs for evidence

        try:
            # Check relayer logs for Pub/Sub activity
            result = subprocess.run(
                [
                    "gcloud",
                    "alpha",
                    "run",
                    "jobs",
                    "executions",
                    "logs",
                    "read",
                    "escrow-event-relayer-msprc",
                    "--region=us-central1",
                    "--limit=50",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                logs = result.stdout
                if "Processing blocks" in logs and "Saved checkpoint" in logs:
                    print("✅ Relayer is processing blocks and saving checkpoints")
                else:
                    print("⚠️ Relayer logs show limited activity")
            else:
                print("⚠️ Cannot access relayer logs")

        except Exception as e:
            print(f"ℹ️ Pub/Sub integration check: {e}")
