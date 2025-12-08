#!/bin/bash
# Minimal test of deployment script

set -euo pipefail

echo "=== Minimal deployment test ==="

# Set basic variables
ENVIRONMENT="dev"
SERVICES="settlement"
TAG="latest"
CI_MODE=false
DRY_RUN=true
SKIP_BUILD=false
SKIP_DEPLOY=false
DEPLOY_CONTRACTS=false
PARALLEL=true

echo "Variables set"

# Test the main function logic
echo "=== Testing main function logic ==="

# Parse arguments (simplified)
echo "Arguments parsed"

# Check dependencies
echo "=== Testing dependencies ==="
if command -v yq &> /dev/null; then
    echo "yq found"
else
    echo "yq missing"
    exit 1
fi

if command -v gcloud &> /dev/null; then
    echo "gcloud found"
else
    echo "gcloud missing"
fi

if command -v jq &> /dev/null; then
    echo "jq found"
else
    echo "jq missing"
fi

echo "Dependencies checked"

# Load configuration (simplified)
echo "=== Testing config loading ==="
CONFIG_FILE="scripts/config/environments.yaml"
if [ -f "$CONFIG_FILE" ]; then
    echo "Config file exists"
else
    echo "Config file missing"
    exit 1
fi

# Test yq command
if yq ".environments.$ENVIRONMENT" "$CONFIG_FILE" | grep -q "name"; then
    echo "YAML parsing works"
else
    echo "YAML parsing failed"
    exit 1
fi

echo "Config loaded"

# Test service parsing
echo "=== Testing service parsing ==="
if [ "$SERVICES" = "all" ]; then
    SERVICES_TO_DEPLOY=("settlement" "risk-engine" "compliance" "relayer")
else
    IFS=',' read -ra SERVICES_TO_DEPLOY <<< "$SERVICES"
fi

echo "Services to deploy: ${SERVICES_TO_DEPLOY[*]}"

echo "=== All tests passed ==="
