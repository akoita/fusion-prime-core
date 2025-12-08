"""
Pytest configuration for Fusion Prime tests.
Automatically loads test environment variables.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load test environment before running any tests
from tests.load_test_env import load_test_environment

load_test_environment()
