#!/bin/bash
# Minimal deployment script to test

set -euo pipefail

echo "=== Minimal deployment script ==="

# Basic setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/scripts" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_DIR="${PROJECT_ROOT}/scripts/config"
CONFIG_FILE="${CONFIG_DIR}/environments.yaml"

echo "Basic setup done"

# Parse arguments (simplified)
ENVIRONMENT=""
SERVICES=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --services)
            SERVICES="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "Arguments parsed: ENVIRONMENT=$ENVIRONMENT, SERVICES=$SERVICES"

# Load environment
if [ -f "${PROJECT_ROOT}/.env.dev" ]; then
    echo "Loading .env.dev..."
    set -a
    source "${PROJECT_ROOT}/.env.dev"
    set +a
    echo "Environment loaded"
fi

echo "=== Script completed successfully ==="
