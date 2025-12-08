"""
Pytest configuration for Cross-Chain Integration Service tests.
"""

import os
import sys
from pathlib import Path

# Add service directory to Python path for imports
service_dir = Path(__file__).parent.parent.absolute()
service_dir_str = str(service_dir)

# Ensure the service directory is at the front of sys.path
if service_dir_str not in sys.path:
    sys.path.insert(0, service_dir_str)
elif sys.path.index(service_dir_str) != 0:
    # Move to front if already in path
    sys.path.remove(service_dir_str)
    sys.path.insert(0, service_dir_str)

# Also set PYTHONPATH environment variable for subprocesses
os.environ["PYTHONPATH"] = service_dir_str + os.pathsep + os.environ.get("PYTHONPATH", "")
