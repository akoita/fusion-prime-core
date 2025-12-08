#!/usr/bin/env python3
"""
Local test runner.

This script runs local tests with proper environment setup and configuration.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.common.config import test_config


def run_local_tests(category: str = None, verbose: bool = False, coverage: bool = False):
    """Run local tests with specified options."""

    # Build pytest command
    cmd = ["python", "-m", "pytest"]

    # Add test directory
    test_dir = project_root / "tests" / "local"
    cmd.append(str(test_dir))

    # Add category filter if specified
    if category:
        # Map category names to pytest markers
        category_mapping = {
            "contracts": "contract",
            "backend": "settlement",
            "e2e": "e2e",  # End-to-end tests for complete user flows
            "health": "health",
        }
        marker = category_mapping.get(category, category)
        cmd.extend(["-m", marker])

    # Add verbose flag
    if verbose:
        cmd.append("-v")

    # Add coverage if requested
    if coverage:
        cmd.extend(["--cov=tests", "--cov-report=html", "--cov-report=term"])

    # Add other useful flags
    cmd.extend(["--tb=short", "--strict-markers", "--disable-warnings"])

    print(f"Running local tests: {' '.join(cmd)}")

    # Run tests
    try:
        result = subprocess.run(cmd, cwd=project_root, check=True)
        print("✅ Local tests completed successfully")
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"❌ Local tests failed with exit code {e.returncode}")
        return e.returncode


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run local tests")
    parser.add_argument("--category", help="Test category to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")

    args = parser.parse_args()

    exit_code = run_local_tests(
        category=args.category, verbose=args.verbose, coverage=args.coverage
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
