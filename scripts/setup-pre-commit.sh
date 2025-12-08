#!/bin/bash
# Fusion Prime Pre-commit Setup Script
# ====================================
# This script sets up pre-commit hooks to match CI verification

set -e

echo "🚀 Setting up Fusion Prime pre-commit hooks..."

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "📦 Installing pre-commit..."
    pip install pre-commit>=3.6.0
else
    echo "✅ pre-commit is already installed"
fi

# Install the pre-commit hooks
echo "🔧 Installing pre-commit hooks..."
pre-commit install

# Install additional dependencies for hooks
echo "📦 Installing additional dependencies..."
pip install safety bandit types-requests types-PyYAML

# Run pre-commit on all files to ensure everything is working
echo "🧪 Running pre-commit on all files..."
pre-commit run --all-files || {
    echo "⚠️  Some pre-commit hooks failed. This is normal for the first run."
    echo "   Fix the issues and run 'pre-commit run --all-files' again."
}

echo "✅ Pre-commit setup complete!"
echo ""
echo "📋 Available commands:"
echo "  pre-commit run --all-files    # Run all hooks on all files"
echo "  pre-commit run <hook-id>      # Run specific hook"
echo "  pre-commit autoupdate          # Update hook versions"
echo "  pre-commit clean               # Clean hook cache"
echo ""
echo "🔍 Hook IDs available:"
echo "  - black (Python formatting)"
echo "  - isort (Import sorting)"
echo "  - flake8 (Python linting)"
echo "  - mypy (Type checking)"
echo "  - bandit (Security scanning)"
echo "  - python-safety-dependencies-check (Dependency security)"
echo "  - dprint (Solidity formatting)"
echo "  - foundry-fmt-check (Foundry format check)"
echo "  - foundry-build-check (Foundry build check)"
echo "  - check-yaml (YAML validation)"
echo "  - check-json (JSON validation)"
echo "  - hadolint (Docker linting)"
echo "  - shellcheck (Shell script linting)"
echo "  - markdownlint (Markdown linting)"
echo "  - eslint (JavaScript/TypeScript linting)"
echo "  - prettier (Code formatting)"
