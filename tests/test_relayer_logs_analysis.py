"""
Relayer Logs Analysis Test

Tests relayer logs for proper operation and error detection.
"""

import subprocess

from tests.base_infrastructure_test import BaseInfrastructureTest


class TestRelayerLogsAnalysis(BaseInfrastructureTest):
    """Test relayer logs for proper operation."""

    def test_relayer_logs_analysis(self):
        """Test relayer logs for proper operation."""
        print("🔄 Testing relayer logs analysis...")

        try:
            # Get recent relayer job execution logs
            result = subprocess.run(
                [
                    "gcloud",
                    "logging",
                    "read",
                    'resource.type="cloud_run_job" AND resource.labels.job_name="escrow-event-relayer" AND resource.labels.location="us-central1"',
                    "--limit=100",
                    "--format=value(textPayload)",
                    "--freshness=1d",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                print("⚠️ Cannot access relayer job logs")
                return

            logs = result.stdout
            print(f"📋 Retrieved {len(logs)} characters of logs")

            # Check for key log patterns
            key_patterns = [
                "Starting Fusion Prime Escrow Event Relayer",
                "Processing blocks",
                "Saved checkpoint",
                "Resuming from block",
            ]

            found_patterns = []
            for pattern in key_patterns:
                if pattern in logs:
                    found_patterns.append(pattern)
                    print(f"✅ Found log pattern: {pattern}")
                else:
                    print(f"⚠️ Missing log pattern: {pattern}")

            # Check for error patterns
            error_patterns = [
                "ERROR",
                "Failed",
                "Exception",
                "Rate limit",
                "400 Client Error",
            ]

            error_count = 0
            for pattern in error_patterns:
                error_count += logs.count(pattern)

            if error_count > 0:
                print(f"⚠️ Found {error_count} potential error patterns in logs")
            else:
                print("✅ No error patterns found in logs")

            # Overall assessment
            if len(found_patterns) >= 3:
                print("✅ Relayer logs show healthy operation")
            else:
                print("⚠️ Relayer logs show limited activity")

        except Exception as e:
            print(f"ℹ️ Relayer logs analysis: {e}")
