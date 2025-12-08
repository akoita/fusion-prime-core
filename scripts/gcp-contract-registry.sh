#!/bin/bash
# GCP Contract Registry Management Script
# Manages smart contract resources in GCP for remote environments

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

Manage smart contract resources in GCP for remote environments.

ACTIONS:
    upload              Upload contract artifacts to GCP Storage
    download            Download contract artifacts from GCP Storage
    list                List available contract deployments
    get-addresses       Get contract addresses from registry
    get-metadata        Get deployment metadata from registry

OPTIONS:
    --env ENV              Environment (dev, staging, production) - auto-detected if not specified
    --project PROJECT      GCP Project ID
    --bucket BUCKET        GCP Storage bucket name (default: {project}-contract-registry)
    --chain-id ID          Chain ID (default: 11155111)
    --dry-run              Show what would be done without executing
    --quiet                Suppress output except for machine-readable data
    -h, --help             Show this help message

EXAMPLES:
    # Upload contract artifacts to GCP (auto-detect environment)
    $0 upload --project fusion-prime-dev --chain-id 11155111

    # Upload to specific environment
    $0 upload --env staging --project fusion-prime-staging --chain-id 11155111

    # Download contract artifacts from GCP
    $0 download --project fusion-prime --chain-id 11155111

    # List available deployments
    $0 list --project fusion-prime

    # Get contract addresses
    $0 get-addresses --project fusion-prime --chain-id 11155111

    # Get deployment metadata
    $0 get-metadata --project fusion-prime --chain-id 11155111
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        upload|download|list|get-addresses|get-metadata)
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

# Validate required parameters
if [ -z "$GCP_PROJECT" ]; then
    print_error "GCP Project ID is required"
    print_info "Use --project flag or set GCP_PROJECT environment variable"
    exit 1
fi

# Set default bucket name
if [ -z "$BUCKET_NAME" ]; then
    BUCKET_NAME="${GCP_PROJECT}-contract-registry"
fi

# Auto-detect environment if not specified
if [ -z "$ENVIRONMENT" ]; then
    # Try to detect from GCP project name patterns
    if [[ "$GCP_PROJECT" == *"prod"* ]]; then
        ENVIRONMENT="production"
    elif [[ "$GCP_PROJECT" == *"staging"* ]]; then
        ENVIRONMENT="staging"
    elif [[ "$GCP_PROJECT" == *"dev"* ]]; then
        ENVIRONMENT="dev"
    else
        # Default to dev if cannot detect
        ENVIRONMENT="dev"
        print_warning "Could not auto-detect environment, defaulting to 'dev'"
    fi
    print_info "Auto-detected environment: $ENVIRONMENT"
fi

# Validate environment
case $ENVIRONMENT in
    dev|staging|production)
        ;;
    *)
        print_error "Invalid environment: $ENVIRONMENT"
        print_info "Valid environments: dev, staging, production"
        exit 1
        ;;
esac

print_info "GCP Contract Registry Management"
print_info "Action: $ACTION"
print_info "Environment: $ENVIRONMENT"
print_info "GCP Project: $GCP_PROJECT"
print_info "Bucket: $BUCKET_NAME"
print_info "Chain ID: $CHAIN_ID"

# Set up GCP paths
REGISTRY_PATH="gs://${BUCKET_NAME}/contracts"
ENV_PATH="${REGISTRY_PATH}/${ENVIRONMENT}"
CHAIN_PATH="${ENV_PATH}/${CHAIN_ID}"

# Function to upload contract artifacts
upload_contracts() {
    print_info "Uploading contract artifacts to GCP Storage..."

    # Check if deployment artifact exists
    local deployment_artifact=""
    if [ -d "${CONTRACTS_DIR}/broadcast/DeployMultichain.s.sol/${CHAIN_ID}" ]; then
        deployment_artifact=$(find "${CONTRACTS_DIR}/broadcast/DeployMultichain.s.sol/${CHAIN_ID}" -name "run-*.json" | sort -V | tail -1)
    fi

    if [ -z "$deployment_artifact" ]; then
        print_error "No deployment artifact found for chain ID $CHAIN_ID"
        print_info "Deploy contracts first: cd contracts && forge script script/DeployMultichain.s.sol:DeployMultichain --rpc-url <RPC_URL> --broadcast"
        exit 1
    fi

    print_info "Using deployment artifact: $deployment_artifact"

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would upload the following files:"
        print_info "  $deployment_artifact -> ${CHAIN_PATH}/deployment.json"
        print_info "  ${CONTRACTS_DIR}/out/EscrowFactory.sol/EscrowFactory.json -> ${CHAIN_PATH}/EscrowFactory.json"
        print_info "  ${CONTRACTS_DIR}/out/Escrow.sol/Escrow.json -> ${CHAIN_PATH}/Escrow.json"
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
    if [ -f "${CONTRACTS_DIR}/out/EscrowFactory.sol/EscrowFactory.json" ]; then
        gsutil cp "${CONTRACTS_DIR}/out/EscrowFactory.sol/EscrowFactory.json" "${CHAIN_PATH}/EscrowFactory.json"
    fi

    if [ -f "${CONTRACTS_DIR}/out/Escrow.sol/Escrow.json" ]; then
        gsutil cp "${CONTRACTS_DIR}/out/Escrow.sol/Escrow.json" "${CHAIN_PATH}/Escrow.json"
    fi

    # Create contract metadata file
    print_info "Creating contract metadata..."
    local metadata_file="/tmp/contract-metadata-${ENVIRONMENT}-${CHAIN_ID}.json"
    cat > "$metadata_file" << EOF
{
  "environment": "$ENVIRONMENT",
  "chain_id": "$CHAIN_ID",
  "deployment_time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "deployment_artifact": "deployment.json",
  "contracts": {
    "EscrowFactory": {
      "abi_file": "EscrowFactory.json",
      "address": "$(jq -r '.transactions[] | select(.contractName == "EscrowFactory") | .contractAddress' "$deployment_artifact" | head -1)"
    },
    "Escrow": {
      "abi_file": "Escrow.json",
      "address": "$(jq -r '.transactions[] | select(.contractName == "Escrow") | .contractAddress' "$deployment_artifact" | head -1)"
    }
  }
}
EOF

    gsutil cp "$metadata_file" "${CHAIN_PATH}/metadata.json"
    rm "$metadata_file"

    print_success "Contract artifacts uploaded successfully"
}

# Function to download contract artifacts
download_contracts() {
    print_info "Downloading contract artifacts from GCP Storage..."

    local download_dir="${CONTRACTS_DIR}/deployments/${ENVIRONMENT}/${CHAIN_ID}"
    mkdir -p "$download_dir"

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would download the following files:"
        print_info "  ${CHAIN_PATH}/deployment.json -> ${download_dir}/deployment.json"
        print_info "  ${CHAIN_PATH}/metadata.json -> ${download_dir}/metadata.json"
        print_info "  ${CHAIN_PATH}/EscrowFactory.json -> ${download_dir}/EscrowFactory.json"
        print_info "  ${CHAIN_PATH}/Escrow.json -> ${download_dir}/Escrow.json"
        return 0
    fi

    # Download files
    print_info "Downloading deployment artifact..."
    gsutil cp "${CHAIN_PATH}/deployment.json" "${download_dir}/deployment.json" || print_warning "Deployment artifact not found"

    print_info "Downloading metadata..."
    gsutil cp "${CHAIN_PATH}/metadata.json" "${download_dir}/metadata.json" || print_warning "Metadata not found"

    print_info "Downloading contract ABIs..."
    gsutil cp "${CHAIN_PATH}/EscrowFactory.json" "${download_dir}/EscrowFactory.json" || print_warning "EscrowFactory ABI not found"
    gsutil cp "${CHAIN_PATH}/Escrow.json" "${download_dir}/Escrow.json" || print_warning "Escrow ABI not found"

    print_success "Contract artifacts downloaded to ${download_dir}"
}

# Function to get contract addresses
get_addresses() {
    print_info "Getting contract addresses from registry..."

    # Download metadata to get contract addresses
    local metadata_file="/tmp/metadata-${ENVIRONMENT}-${CHAIN_ID}.json"
    gsutil cp "${CHAIN_PATH}/metadata.json" "$metadata_file" 2>/dev/null || {
        print_error "Contract metadata not found. Upload contracts first."
        exit 1
    }

    # Extract contract addresses
    local escrow_factory_address=$(jq -r '.contracts.EscrowFactory.address' "$metadata_file")
    local escrow_address=$(jq -r '.contracts.Escrow.address' "$metadata_file")

    if [ "$escrow_factory_address" = "null" ] || [ -z "$escrow_factory_address" ]; then
        print_error "EscrowFactory address not found in metadata"
        exit 1
    fi

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would output the following addresses:"
        print_info "  ESCROW_FACTORY_ADDRESS=$escrow_factory_address"
        if [ "$escrow_address" != "null" ] && [ -n "$escrow_address" ]; then
            print_info "  ESCROW_ADDRESS=$escrow_address"
        fi
        rm "$metadata_file"
        return 0
    fi

    # Output addresses in environment variable format
    echo "ESCROW_FACTORY_ADDRESS=$escrow_factory_address"
    if [ "$escrow_address" != "null" ] && [ -n "$escrow_address" ]; then
        echo "ESCROW_ADDRESS=$escrow_address"
    fi

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

# Function to list available deployments
list_deployments() {
    print_info "Listing available contract deployments..."

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would list deployments from ${REGISTRY_PATH}"
        return 0
    fi

    # List environments
    print_info "Available environments:"
    gsutil ls "${REGISTRY_PATH}/" 2>/dev/null | sed 's|gs://[^/]*/contracts/||g' | sed 's|/||g' || print_warning "No environments found"

    # List chain IDs for current environment
    print_info "Available chain IDs for $ENVIRONMENT:"
    gsutil ls "${ENV_PATH}/" 2>/dev/null | sed 's|gs://[^/]*/contracts/[^/]*/||g' | sed 's|/||g' || print_warning "No chain IDs found for $ENVIRONMENT"

    # Show current environment details
    if gsutil ls "${CHAIN_PATH}/metadata.json" >/dev/null 2>&1; then
        print_info "Current deployment details for $ENVIRONMENT (Chain ID: $CHAIN_ID):"
        gsutil cat "${CHAIN_PATH}/metadata.json" | jq '.' || print_warning "Failed to read metadata"
    else
        print_warning "No deployment found for $ENVIRONMENT (Chain ID: $CHAIN_ID)"
    fi
}

# Execute action
case $ACTION in
    upload)
        upload_contracts
        ;;
    download)
        download_contracts
        ;;
    list)
        list_deployments
        ;;
    get-addresses)
        get_addresses
        ;;
    get-metadata)
        get_metadata
        ;;
    *)
        print_error "Invalid action: $ACTION"
        show_usage
        exit 1
        ;;
esac

print_success "Operation completed successfully!"
