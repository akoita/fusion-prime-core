"""
Pytest configuration for testnet tests.
Loads environment variables from .env.test file.
"""

import os
from pathlib import Path

# Load environment variables from .env.test
try:
    from dotenv import load_dotenv

    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent.parent

    # Load .env.test file
    env_file = project_root / ".env.test"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ Loaded environment from {env_file}")
    else:
        print(f"⚠️ Environment file not found: {env_file}")

except ImportError:
    print("⚠️ python-dotenv not available, environment variables may not be loaded")
except Exception as e:
    print(f"⚠️ Error loading environment: {e}")
