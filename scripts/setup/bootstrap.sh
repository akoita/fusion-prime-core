#!/usr/bin/env bash
set -euo pipefail

echo "Bootstrapping Fusion Prime development environment..."

# Install Foundry if not present
if ! command -v forge >/dev/null 2>&1; then
  echo "Installing Foundry toolchain..."
  curl -L https://foundry.paradigm.xyz | bash
  source "$HOME/.foundry/bin/foundryup" >/dev/null 2>&1 || true
  foundryup
fi

# Install pnpm for TypeScript tooling
if ! command -v pnpm >/dev/null 2>&1; then
  echo "Installing pnpm..."
  curl -fsSL https://get.pnpm.io/install.sh | sh -
fi

# Install Poetry for Python services
if ! command -v poetry >/dev/null 2>&1; then
  echo "Installing Poetry..."
  curl -sSL https://install.python-poetry.org | python3 -
fi

echo "Bootstrap complete. Configure gcloud and other credentials manually if not already set."

