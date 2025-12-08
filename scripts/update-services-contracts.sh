#!/bin/bash
# Update Cloud Run Services with Contract Addresses
# Uses the contract registry to get addresses and updates Cloud Run services

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

# Default values
ENVIRONMENT="dev"
GCP_PROJECT=""
GCP_REGION="us-central1"
CHAIN_ID="11155111"
DRY_RUN=false
SERVICES=""

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Update Cloud Run services with contract addresses from the contract registry.

OPTIONS:
    --env ENV              Environment (dev, staging, production) - auto-detected if not specified
    --project PROJECT      GCP Project ID
    --region REGION        GCP Region (default: us-central1)
    --chain-id ID          Chain ID (default: 11155111)
    --services SERVICES    Comma-separated list of services to update (default: all)
    --dry-run              Show what would be done without executing
    -h, --help             Show this help message

EXAMPLES:
    # Update all services with contract addresses (auto-detect environment)
    $0 --project fusion-prime-dev

    # Update specific services
    $0 --project fusion-prime --services settlement-service,risk-engine

    # Update with specific environment
    $0 --env staging --project fusion-prime-staging

    # Dry run to see what would be updated
    $0 --project fusion-prime --dry-run
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --project)
            GCP_PROJECT="$2"
            shift 2
            ;;
        --region)
            GCP_REGION="$2"
            shift 2
            ;;
        --chain-id)
            CHAIN_ID="$2"
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

print_info "Updating Cloud Run Services with Contract Addresses"
print_info "Environment: $ENVIRONMENT"
print_info "GCP Project: $GCP_PROJECT"
print_info "Region: $GCP_REGION"
print_info "Chain ID: $CHAIN_ID"

# Get contract addresses from registry
print_info "Getting contract addresses from registry..."
contract_addresses=$("${SCRIPT_DIR}/gcp-contract-registry.sh" get-addresses --env "$ENVIRONMENT" --project "$GCP_PROJECT" --chain-id "$CHAIN_ID")

if [ -z "$contract_addresses" ]; then
    print_error "Failed to get contract addresses from registry"
    exit 1
fi

# Parse contract addresses
ESCROW_FACTORY_ADDRESS=$(echo "$contract_addresses" | grep "ESCROW_FACTORY_ADDRESS=" | cut -d'=' -f2)
ESCROW_ADDRESS=$(echo "$contract_addresses" | grep "ESCROW_ADDRESS=" | cut -d'=' -f2)

if [ -z "$ESCROW_FACTORY_ADDRESS" ]; then
    print_error "EscrowFactory address not found in registry"
    exit 1
fi

print_info "Contract addresses:"
print_info "  EscrowFactory: $ESCROW_FACTORY_ADDRESS"
if [ -n "$ESCROW_ADDRESS" ]; then
    print_info "  Escrow: $ESCROW_ADDRESS"
fi

# Determine services to update
if [ -z "$SERVICES" ]; then
    # Default services
    SERVICES="settlement-service,risk-engine,compliance,escrow-event-relayer"
fi

# Convert comma-separated list to array
IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"

# Function to update a single service
update_service() {
    local service_name="$1"

    print_info "Updating $service_name..."

    # Check if service exists
    if ! gcloud run services describe "$service_name" --region="$GCP_REGION" --project="$GCP_PROJECT" >/dev/null 2>&1; then
        print_warning "Service $service_name not found, skipping"
        return 0
    fi

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would update $service_name with:"
        print_info "  ESCROW_FACTORY_ADDRESS=$ESCROW_FACTORY_ADDRESS"
        if [ -n "$ESCROW_ADDRESS" ]; then
            print_info "  ESCROW_ADDRESS=$ESCROW_ADDRESS"
        fi
        return 0
    fi

    # Build environment variables
    local env_vars="ESCROW_FACTORY_ADDRESS=$ESCROW_FACTORY_ADDRESS"
    if [ -n "$ESCROW_ADDRESS" ]; then
        env_vars="$env_vars,ESCROW_ADDRESS=$ESCROW_ADDRESS"
    fi

    # Update service
    if gcloud run services update "$service_name" \
        --region="$GCP_REGION" \
        --set-env-vars="$env_vars" \
        --project="$GCP_PROJECT" \
        --quiet; then
        print_success "Updated $service_name"
    else
        print_warning "Failed to update $service_name"
    fi
}

# Update all services
print_info "Updating services: ${SERVICES}"
for service in "${SERVICE_ARRAY[@]}"; do
    update_service "$service"
done

print_success "Service update completed!"
print_info "Summary:"
print_info "  Environment: $ENVIRONMENT"
print_info "  Services Updated: ${#SERVICE_ARRAY[@]}"
print_info "  EscrowFactory: $ESCROW_FACTORY_ADDRESS"
if [ -n "$ESCROW_ADDRESS" ]; then
    print_info "  Escrow: $ESCROW_ADDRESS"
fi
