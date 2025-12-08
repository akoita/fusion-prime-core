#!/bin/bash
# Debug script to find where deployment hangs

set -euo pipefail

echo "=== Step 1: Basic setup ==="
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/scripts" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_DIR="${PROJECT_ROOT}/scripts/config"
CONFIG_FILE="${CONFIG_DIR}/environments.yaml"

echo "SCRIPT_DIR: $SCRIPT_DIR"
echo "PROJECT_ROOT: $PROJECT_ROOT"
echo "CONFIG_FILE: $CONFIG_FILE"

echo "=== Step 2: Check config file ==="
if [ -f "$CONFIG_FILE" ]; then
    echo "Config file exists"
else
    echo "Config file missing"
    exit 1
fi

echo "=== Step 3: Test yq command ==="
if yq ".environments.dev" "$CONFIG_FILE" | grep -q "name"; then
    echo "YAML parsing works"
else
    echo "YAML parsing failed"
    exit 1
fi

echo "=== Step 4: Test .env.dev loading ==="
if [ -f "${PROJECT_ROOT}/.env.dev" ]; then
    echo "Loading .env.dev..."
    set -a
    source "${PROJECT_ROOT}/.env.dev"
    set +a
    echo "RPC_URL: $RPC_URL"
    echo "CHAIN_ID: $CHAIN_ID"
else
    echo ".env.dev not found"
fi

echo "=== Step 5: Test environment variable export ==="
export ENV_NAME=$(yq ".environments.dev.name" "$CONFIG_FILE" | sed 's/^"//;s/"$//')
export ENV_DESC=$(yq ".environments.dev.description" "$CONFIG_FILE" | sed 's/^"//;s/"$//')
export GCP_PROJECT=${GCP_PROJECT_ID:-$(yq ".environments.dev.gcp_project" "$CONFIG_FILE" | sed 's/^"//;s/"$//')}
export GCP_REGION=${GCP_REGION:-$(yq ".environments.dev.region" "$CONFIG_FILE" | sed 's/^"//;s/"$//')}
export BLOCKCHAIN_NETWORK=${BLOCKCHAIN_NETWORK:-$(yq ".environments.dev.blockchain.network" "$CONFIG_FILE" | sed 's/^"//;s/"$//')}
export RPC_URL=${RPC_URL:-$(yq ".environments.dev.blockchain.rpc_url" "$CONFIG_FILE" | sed 's/^"//;s/"$//')}
export CHAIN_ID=${CHAIN_ID:-$(yq ".environments.dev.blockchain.chain_id" "$CONFIG_FILE" | sed 's/^"//;s/"$//')}

echo "ENV_NAME: $ENV_NAME"
echo "ENV_DESC: $ENV_DESC"
echo "GCP_PROJECT: $GCP_PROJECT"
echo "GCP_REGION: $GCP_REGION"
echo "BLOCKCHAIN_NETWORK: $BLOCKCHAIN_NETWORK"
echo "RPC_URL: $RPC_URL"
echo "CHAIN_ID: $CHAIN_ID"

echo "=== Step 6: Test dependency checks ==="
if command -v yq &> /dev/null; then
    echo "yq found"
else
    echo "yq missing"
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

echo "=== All steps completed successfully ==="
