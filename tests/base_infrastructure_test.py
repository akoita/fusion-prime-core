"""
Base Infrastructure Test Class for Fusion Prime

Provides common setup and utilities for infrastructure health tests.
Works with both LOCAL (Docker Compose) and TESTNET (Cloud Run) environments.
"""

import os


class BaseInfrastructureTest:
    """Base class for infrastructure health tests with environment auto-detection."""

    def setup_method(self):
        """Setup test environment with auto-detection for local/testnet."""
        # Detect environment
        self.environment = os.getenv("TEST_ENVIRONMENT", "local").lower()

        if self.environment == "local":
            # Docker Compose defaults
            self.settlement_url = os.getenv("SETTLEMENT_SERVICE_URL", "http://localhost:8000")
            self.database_url = os.getenv(
                "DATABASE_URL",
                "postgresql://fusion_prime:fusion_prime_dev_pass@localhost:5432/fusion_prime",
            )
            self.pubsub_project = os.getenv("GCP_PROJECT", "fusion-prime-local")
            self.pubsub_topic = os.getenv("PUBSUB_TOPIC", "settlement.events.v1")
            self.settlement_subscription = os.getenv(
                "SETTLEMENT_SUBSCRIPTION", "settlement-events-consumer"
            )
            self.gcp_region = "local"

            # Set Pub/Sub emulator
            os.environ.setdefault("PUBSUB_EMULATOR_HOST", "localhost:8085")

        else:  # testnet or production
            # Cloud Run configuration (requires env vars)
            self.settlement_url = os.getenv("SETTLEMENT_SERVICE_URL")
            self.database_url = os.getenv("DATABASE_URL")
            self.pubsub_project = os.getenv("GCP_PROJECT", "fusion-prime")
            self.pubsub_topic = os.getenv("PUBSUB_TOPIC")
            self.settlement_subscription = os.getenv("SETTLEMENT_SUBSCRIPTION")
            self.gcp_region = os.getenv("GCP_REGION", "us-central1")

        print(f"\n🔧 Infrastructure Test Configuration ({self.environment.upper()}):")
        print(f"  Settlement Service: {self.settlement_url}")
        print(
            f"  Database: {self.database_url.split('@')[0] if self.database_url else 'Not set'}@***"
        )
        print(f"  Pub/Sub Project: {self.pubsub_project}")
        print(f"  Pub/Sub Topic: {self.pubsub_topic}")
        print(f"  Settlement Subscription: {self.settlement_subscription}")
        print(f"  GCP Region: {self.gcp_region}")
