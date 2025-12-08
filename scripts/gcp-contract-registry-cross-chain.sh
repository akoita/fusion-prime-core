#!/bin/bash
# GCP Contract Registry Management Script for Cross-Chain Contracts
# Manages cross-chain contract resources in GCP for remote environments

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONTRACTS_DIR="${PROJECT_ROOT}/contracts"

# Default values
ENVIRONMENT="dev"
GCP_PROJECT=""
BUCKET_NAME=""
CHAIN_ID="11155111"
DRY_RUN=false
QUIET=false
ACTION="upload"

# Function to print colored output
print_success() {
    if [ "$QUIET" = false ]; then
        echo -e "${GREEN}✓${NC} $1"
    fi
}

print_info() {
    if [ "$QUIET" = false ]; then
        echo -e "${BLUE}ℹ${NC} $1"
    fi
}

print_warning() {
    if [ "$QUIET" = false ]; then
        echo -e "${YELLOW}⚠${NC} $1"
    fi
}

print_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Manage cross-chain contract resources in GCP for remote environments.

ACTIONS:
    upload              Upload cross-chain contract artifacts to GCP Storage
    download            Download cross-chain contract artifacts from GCP Storage
    get-addresses      Get cross-chain contract addresses from registry
    get-metadata        Get deployment metadata from registry

OPTIONS:
    --env ENV              Environment (dev, staging, production) - auto-detected if not specified
    --project PROJECT      GCP Project ID
    --bucket BUCKET        GCP Storage bucket name (default: {project}-contract-registry)
    --chain-id ID          Chain ID (default: 11155111 for Sepolia)
    --dry-run              Show what would be done without executing
    --quiet                Suppress output except for machine-readable data
    -h, --help             Show this help message

EXAMPLES:
    # Upload cross-chain contracts to GCP (Sepolia)
    $0 upload --project fusion-prime --chain-id 11155111

    # Upload to Amoy
    $0 upload --project fusion-prime --chain-id 80002

    # Get contract addresses
    $0 get-addresses --project fusion-prime --chain-id 11155111
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        upload|download|get-addresses|get-metadata)
            ACTION="$1"
            shift
            ;;
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --project)
            GCP_PROJECT="$2"
            shift 2
            ;;
        --bucket)
            BUCKET_NAME="$2"
            shift 2
            ;;
        --chain-id)
            CHAIN_ID="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Auto-detect environment if not specified
if [ -z "$ENVIRONMENT" ]; then
    if git rev-parse --git-dir > /dev/null 2>&1; then
        BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
        case "$BRANCH" in
            dev|develop|development) ENVIRONMENT="dev" ;;
            staging|stage) ENVIRONMENT="staging" ;;
            main|master|production|prod) ENVIRONMENT="production" ;;
            *) ENVIRONMENT="dev" ;;
        esac
    else
        ENVIRONMENT="dev"
    fi
fi

# Set bucket name if not specified
if [ -z "$BUCKET_NAME" ]; then
    if [ -z "$GCP_PROJECT" ]; then
        print_error "Either --project or --bucket must be specified"
        exit 1
    fi
    BUCKET_NAME="${GCP_PROJECT}-contract-registry"
fi

# Set up paths
ENV_PATH="gs://${BUCKET_NAME}/contracts/${ENVIRONMENT}"
CHAIN_PATH="${ENV_PATH}/${CHAIN_ID}/cross-chain"

# Function to upload cross-chain contract artifacts
upload_contracts() {
    print_info "Uploading cross-chain contract artifacts to GCP Storage..."

    # Check if deployment artifact exists
    local deployment_artifact=""
    # Check cross-chain directory first (where script is located)
    if [ -d "${CONTRACTS_DIR}/cross-chain/broadcast/DeployCrossChain.s.sol/${CHAIN_ID}" ]; then
        deployment_artifact=$(find "${CONTRACTS_DIR}/cross-chain/broadcast/DeployCrossChain.s.sol/${CHAIN_ID}" -name "run-*.json" | sort -V | tail -1)
    elif [ -d "${CONTRACTS_DIR}/broadcast/DeployCrossChain.s.sol/${CHAIN_ID}" ]; then
        deployment_artifact=$(find "${CONTRACTS_DIR}/broadcast/DeployCrossChain.s.sol/${CHAIN_ID}" -name "run-*.json" | sort -V | tail -1)
    fi

    if [ -z "$deployment_artifact" ]; then
        print_error "No deployment artifact found for chain ID $CHAIN_ID"
        print_info "Deploy contracts first: cd contracts && forge script script/DeployCrossChain.s.sol:DeployCrossChain --rpc-url <RPC_URL> --broadcast"
        exit 1
    fi

    print_info "Using deployment artifact: $deployment_artifact"

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would upload the following files:"
        print_info "  $deployment_artifact -> ${CHAIN_PATH}/deployment.json"
        print_info "  BridgeManager.json -> ${CHAIN_PATH}/BridgeManager.json"
        print_info "  CrossChainVault.json -> ${CHAIN_PATH}/CrossChainVault.json"
        print_info "  AxelarAdapter.json -> ${CHAIN_PATH}/AxelarAdapter.json"
        print_info "  CCIPAdapter.json -> ${CHAIN_PATH}/CCIPAdapter.json"
        return 0
    fi

    # Create bucket if it doesn't exist
    print_info "Creating bucket if it doesn't exist..."
    gsutil mb -p "$GCP_PROJECT" "gs://${BUCKET_NAME}" 2>/dev/null || true

    # Upload deployment artifact
    print_info "Uploading deployment artifact..."
    gsutil cp "$deployment_artifact" "${CHAIN_PATH}/deployment.json"

    # Upload contract ABIs
    print_info "Uploading contract ABIs..."
    if [ -f "${CONTRACTS_DIR}/out/cross-chain/src/BridgeManager.sol/BridgeManager.json" ]; then
        gsutil cp "${CONTRACTS_DIR}/out/cross-chain/src/BridgeManager.sol/BridgeManager.json" "${CHAIN_PATH}/BridgeManager.json"
    fi

    if [ -f "${CONTRACTS_DIR}/out/cross-chain/src/CrossChainVault.sol/CrossChainVault.json" ]; then
        gsutil cp "${CONTRACTS_DIR}/out/cross-chain/src/CrossChainVault.sol/CrossChainVault.json" "${CHAIN_PATH}/CrossChainVault.json"
    fi

    if [ -f "${CONTRACTS_DIR}/out/cross-chain/src/adapters/AxelarAdapter.sol/AxelarAdapter.json" ]; then
        gsutil cp "${CONTRACTS_DIR}/out/cross-chain/src/adapters/AxelarAdapter.sol/AxelarAdapter.json" "${CHAIN_PATH}/AxelarAdapter.json"
    fi

    if [ -f "${CONTRACTS_DIR}/out/cross-chain/src/adapters/CCIPAdapter.sol/CCIPAdapter.json" ]; then
        gsutil cp "${CONTRACTS_DIR}/out/cross-chain/src/adapters/CCIPAdapter.sol/CCIPAdapter.json" "${CHAIN_PATH}/CCIPAdapter.json"
    fi

    # Extract contract addresses from deployment artifact
    local bridge_manager_address=$(jq -r '.transactions[] | select(.contractName == "BridgeManager") | .contractAddress' "$deployment_artifact" | head -1)
    local cross_chain_vault_address=$(jq -r '.transactions[] | select(.contractName == "CrossChainVault") | .contractAddress' "$deployment_artifact" | head -1)
    local axelar_adapter_address=$(jq -r '.transactions[] | select(.contractName == "AxelarAdapter") | .contractAddress' "$deployment_artifact" | head -1)
    local ccip_adapter_address=$(jq -r '.transactions[] | select(.contractName == "CCIPAdapter") | .contractAddress' "$deployment_artifact" | head -1)

    # Create contract metadata file
    print_info "Creating contract metadata..."
    local metadata_file="/tmp/cross-chain-metadata-${ENVIRONMENT}-${CHAIN_ID}.json"
    cat > "$metadata_file" << EOF
{
  "environment": "$ENVIRONMENT",
  "chain_id": "$CHAIN_ID",
  "deployment_time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "deployment_artifact": "deployment.json",
  "contracts": {
    "BridgeManager": {
      "abi_file": "BridgeManager.json",
      "address": "$bridge_manager_address"
    },
    "CrossChainVault": {
      "abi_file": "CrossChainVault.json",
      "address": "$cross_chain_vault_address"
    },
    "AxelarAdapter": {
      "abi_file": "AxelarAdapter.json",
      "address": "$axelar_adapter_address"
    },
    "CCIPAdapter": {
      "abi_file": "CCIPAdapter.json",
      "address": "$ccip_adapter_address"
    }
  }
}
EOF

    gsutil cp "$metadata_file" "${CHAIN_PATH}/metadata.json"
    rm "$metadata_file"

    print_success "Cross-chain contract artifacts uploaded successfully"
    print_info "BridgeManager: $bridge_manager_address"
    print_info "CrossChainVault: $cross_chain_vault_address"
}

# Function to get contract addresses
get_addresses() {
    print_info "Getting cross-chain contract addresses from registry..."

    # Download metadata to get contract addresses
    local metadata_file="/tmp/cross-chain-metadata-${ENVIRONMENT}-${CHAIN_ID}.json"
    gsutil cp "${CHAIN_PATH}/metadata.json" "$metadata_file" 2>/dev/null || {
        print_error "Contract metadata not found. Upload contracts first."
        exit 1
    }

    # Extract contract addresses
    local bridge_manager_address=$(jq -r '.contracts.BridgeManager.address' "$metadata_file")
    local cross_chain_vault_address=$(jq -r '.contracts.CrossChainVault.address' "$metadata_file")
    local axelar_adapter_address=$(jq -r '.contracts.AxelarAdapter.address' "$metadata_file")
    local ccip_adapter_address=$(jq -r '.contracts.CCIPAdapter.address' "$metadata_file")

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would output the following addresses:"
        print_info "  BRIDGE_MANAGER_ADDRESS=$bridge_manager_address"
        print_info "  CROSS_CHAIN_VAULT_ADDRESS=$cross_chain_vault_address"
        print_info "  AXELAR_ADAPTER_ADDRESS=$axelar_adapter_address"
        print_info "  CCIP_ADAPTER_ADDRESS=$ccip_adapter_address"
        rm "$metadata_file"
        return 0
    fi

    # Output addresses in environment variable format
    echo "BRIDGE_MANAGER_ADDRESS=$bridge_manager_address"
    echo "CROSS_CHAIN_VAULT_ADDRESS=$cross_chain_vault_address"
    echo "AXELAR_ADAPTER_ADDRESS=$axelar_adapter_address"
    echo "CCIP_ADAPTER_ADDRESS=$ccip_adapter_address"

    rm "$metadata_file"
}

# Function to get deployment metadata
get_metadata() {
    print_info "Getting deployment metadata from registry..."

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would output metadata from ${CHAIN_PATH}/metadata.json"
        return 0
    fi

    # Output metadata as JSON
    gsutil cat "${CHAIN_PATH}/metadata.json" 2>/dev/null || {
        print_error "Contract metadata not found. Upload contracts first."
        exit 1
    }
}

# Main execution
case "$ACTION" in
    upload)
        upload_contracts
        ;;
    get-addresses)
        get_addresses
        ;;
    get-metadata)
        get_metadata
        ;;
    *)
        print_error "Unknown action: $ACTION"
        show_usage
        exit 1
        ;;
esac
