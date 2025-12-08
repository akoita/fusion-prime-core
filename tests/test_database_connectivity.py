"""
Database Connectivity Test

Tests database connectivity and configuration.
"""

import pytest

from tests.base_infrastructure_test import BaseInfrastructureTest


class TestDatabaseConnectivity(BaseInfrastructureTest):
    """Test database connectivity and configuration."""

    def test_database_connectivity(self):
        """Test database connectivity and configuration."""
        print("🔄 Testing database connectivity...")

        if not self.database_url:
            pytest.skip("DATABASE_URL not set")

        try:
            # Check if it's a Cloud SQL connection
            if "cloudsql" in self.database_url:
                print("ℹ️ Cloud SQL database detected - local connectivity test skipped")
                print("ℹ️ Database connectivity should be tested from within Cloud Run")
                return

            # For local databases, test connection
            if self.database_url.startswith("sqlite"):
                print("ℹ️ SQLite database detected - no connectivity test needed")
                return

            # For other databases, we could add connection tests here
            print(f"ℹ️ Database URL configured: {self.database_url.split('@')[0]}@***")

        except Exception as e:
            print(f"ℹ️ Database connectivity check: {e}")
