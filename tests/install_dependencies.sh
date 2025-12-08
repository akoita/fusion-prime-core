#!/bin/bash
# Install test dependencies

set -e

echo "Installing test dependencies..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Install dependencies
pip install -r tests/requirements.txt

echo "✅ Test dependencies installed successfully"
