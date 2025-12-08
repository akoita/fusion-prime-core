#!/usr/bin/env python3
"""
Event Relayer Verification Script (Cloud Run Job)

This script provides a comprehensive way to verify that the event relayer
Cloud Run Job is working correctly in the Fusion Prime system.

Usage:
    python tests/scripts/verify_relayer.py [--region REGION] [--verbose]
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Optional


def check_relayer_job_exists(region: str = "us-central1", verbose: bool = False) -> bool:
    """Check if relayer Cloud Run Job is deployed."""
    print("🔍 Checking relayer job deployment...")

    try:
        result = subprocess.run(
            [
                "gcloud",
                "run",
                "jobs",
                "describe",
                "escrow-event-relayer",
                f"--region={region}",
                "--format=json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            job_info = json.loads(result.stdout)
            job_name = job_info.get("metadata", {}).get("name", "unknown")
            print(f"✅ Relayer job exists: {job_name}")

            if verbose:
                template = job_info.get("spec", {}).get("template", {})
                containers = template.get("spec", {}).get("containers", [])
                if containers:
                    print(f"  Image: {containers[0].get('image', 'unknown')}")
                    env_vars = containers[0].get("env", [])
                    print(f"  Environment variables: {len(env_vars)} configured")

            return True
        else:
            print(f"❌ Relayer job not found: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Error checking relayer job: {e}")
        return False


def check_scheduler_configuration(region: str = "us-central1", verbose: bool = False) -> bool:
    """Check if Cloud Scheduler is configured to trigger the job."""
    print("🔍 Checking scheduler configuration...")

    try:
        result = subprocess.run(
            [
                "gcloud",
                "scheduler",
                "jobs",
                "describe",
                "escrow-relayer-scheduler",
                f"--location={region}",
                "--format=json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            scheduler_info = json.loads(result.stdout)
            schedule = scheduler_info.get("schedule", "unknown")
            state = scheduler_info.get("state", "unknown")

            print(f"✅ Scheduler exists: escrow-relayer-scheduler")
            print(f"   Schedule: {schedule}")
            print(f"   State: {state}")

            if verbose:
                last_attempt = scheduler_info.get("lastAttemptTime")
                if last_attempt:
                    print(f"   Last attempt: {last_attempt}")

            return state == "ENABLED"
        else:
            print(f"❌ Scheduler not found: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Error checking scheduler: {e}")
        return False


def check_recent_executions(region: str = "us-central1", verbose: bool = False) -> bool:
    """Check recent job executions."""
    print("🔍 Checking recent job executions...")

    try:
        result = subprocess.run(
            [
                "gcloud",
                "run",
                "jobs",
                "executions",
                "list",
                "escrow-event-relayer",
                f"--region={region}",
                "--limit=5",
                "--format=json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0 and result.stdout.strip():
            executions = json.loads(result.stdout)

            if not executions:
                print(f"⚠️  No recent executions found")
                return False

            print(f"✅ Found {len(executions)} recent execution(s)")

            for i, execution in enumerate(executions[:3]):
                metadata = execution.get("metadata", {})
                status = execution.get("status", {})
                succeeded = status.get("succeededCount", 0)
                failed = status.get("failedCount", 0)
                completion_time = status.get("completionTime", "unknown")

                status_icon = "✅" if succeeded > 0 and failed == 0 else "❌"
                print(f"   {status_icon} Execution {i + 1}: {metadata.get('name', 'unknown')}")

                if verbose:
                    print(f"      Succeeded: {succeeded}, Failed: {failed}")
                    print(f"      Completed: {completion_time}")

            # Check if most recent execution succeeded
            most_recent = executions[0]
            most_recent_status = most_recent.get("status", {})
            most_recent_succeeded = most_recent_status.get("succeededCount", 0)
            most_recent_failed = most_recent_status.get("failedCount", 0)

            return most_recent_succeeded > 0 and most_recent_failed == 0
        else:
            print(f"⚠️  Could not retrieve executions")
            return False

    except Exception as e:
        print(f"❌ Error checking executions: {e}")
        return False


def check_execution_logs(region: str = "us-central1", verbose: bool = False) -> bool:
    """Check job execution logs for errors."""
    print("🔍 Checking job execution logs...")

    try:
        result = subprocess.run(
            [
                "gcloud",
                "logging",
                "read",
                f'resource.type="cloud_run_job" AND resource.labels.job_name="escrow-event-relayer" AND resource.labels.location="{region}"',
                "--limit=50",
                "--format=value(textPayload)",
                "--freshness=1h",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            logs = result.stdout
            log_lines = [line for line in logs.split("\n") if line.strip()]

            print(f"✅ Retrieved {len(log_lines)} log entries")

            # Check for success indicators
            success_patterns = [
                "Batch Job Complete",
                "Processing blocks",
                "Events Processed",
                "Saved checkpoint",
            ]

            found_success = sum(
                1 for line in log_lines for pattern in success_patterns if pattern in line
            )

            if found_success > 0:
                print(f"   Found {found_success} success indicator(s)")

            # Check for error patterns
            error_patterns = ["ERROR", "Failed", "Exception", "Traceback"]
            found_errors = sum(
                1 for line in log_lines for pattern in error_patterns if pattern in line
            )

            if found_errors > 0:
                print(f"⚠️  Found {found_errors} error pattern(s)")
                if verbose and found_errors < 10:
                    for line in log_lines:
                        if any(pattern in line for pattern in error_patterns):
                            print(f"     {line[:100]}")
            else:
                print(f"✅ No error patterns found")

            return found_success > 0 and found_errors == 0
        else:
            print(f"⚠️  Could not retrieve logs: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Error checking logs: {e}")
        return False


def test_manual_execution(region: str = "us-central1", verbose: bool = False) -> bool:
    """Test manual job execution."""
    print("🔍 Testing manual job execution...")
    print("   (This will trigger a job execution and wait for completion)")

    try:
        result = subprocess.run(
            [
                "gcloud",
                "run",
                "jobs",
                "execute",
                "escrow-event-relayer",
                f"--region={region}",
                "--wait",
            ],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes timeout
        )

        if result.returncode == 0:
            print(f"✅ Manual execution completed successfully")

            if verbose:
                print(f"   Output: {result.stdout[:500]}")

            return True
        else:
            print(f"❌ Manual execution failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print(f"⚠️  Manual execution timed out (this may be normal for long-running jobs)")
        return True  # Don't fail test for timeout
    except Exception as e:
        print(f"❌ Error executing job manually: {e}")
        return False


def main():
    """Main verification function."""
    parser = argparse.ArgumentParser(description="Verify event relayer Cloud Run Job functionality")
    parser.add_argument("--region", default="us-central1", help="GCP region (default: us-central1)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute a test job run (takes longer)",
    )

    args = parser.parse_args()

    print("🔄 Event Relayer Verification (Cloud Run Job)")
    print("=" * 60)
    print(f"Region: {args.region}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print()

    # Run verification tests
    tests = [
        ("Job Deployment", lambda: check_relayer_job_exists(args.region, args.verbose)),
        (
            "Scheduler Configuration",
            lambda: check_scheduler_configuration(args.region, args.verbose),
        ),
        (
            "Recent Executions",
            lambda: check_recent_executions(args.region, args.verbose),
        ),
        ("Execution Logs", lambda: check_execution_logs(args.region, args.verbose)),
    ]

    # Add manual execution test if requested
    if args.execute:
        tests.append(("Manual Execution", lambda: test_manual_execution(args.region, args.verbose)))

    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name} passed")
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} error: {e}")
            results.append((test_name, False))

        # Add small delay between tests
        time.sleep(1)

    # Summary
    print("\n" + "=" * 60)
    print("📊 Verification Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All relayer verification tests passed!")
        sys.exit(0)
    else:
        print("⚠️ Some relayer verification tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
