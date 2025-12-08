#!/bin/bash
# Common functions for deployment scripts
# Shared utilities for build, deploy, and validation

set -euo pipefail

# ============================================================================
# COLORS
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_section() {
    echo ""
    echo -e "${CYAN}════════════════════════════════════════${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}════════════════════════════════════════${NC}"
}

# ============================================================================
# CONFIGURATION LOADING
# ============================================================================

# Set up paths - handle both direct execution and sourcing
if [ -n "${BASH_SOURCE[0]:-}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
else
    # Fallback when sourcing the script
    SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
fi
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_DIR="${PROJECT_ROOT}/scripts/config"
CONFIG_FILE="${CONFIG_DIR}/environments.yaml"

load_environment_config() {
    local env=$1

    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        return 1
    fi

    # Validate environment exists
    if ! yq ".environments.$env" "$CONFIG_FILE" | grep -q "name"; then
        log_error "Environment '$env' not found in configuration"
        echo "Available environments:"
        yq '.environments | keys | .[]' "$CONFIG_FILE"
        return 1
    fi

    # Load .env.dev file if it exists (for environment variable overrides)
    if [ -f "${PROJECT_ROOT}/.env.dev" ]; then
        log_info "Loading environment variables from .env.dev"
        set -a  # automatically export all variables
        source "${PROJECT_ROOT}/.env.dev"
        set +a  # stop automatically exporting
    fi

    # Export environment variables (strip quotes from yq output)
    # Environment variables from .env.dev will override YAML defaults
    export ENV_NAME=$(yq ".environments.$env.name" "$CONFIG_FILE" | sed 's/^"//;s/"$//')
    export ENV_DESC=$(yq ".environments.$env.description" "$CONFIG_FILE" | sed 's/^"//;s/"$//')
    export GCP_PROJECT=${GCP_PROJECT_ID:-$(yq ".environments.$env.gcp_project" "$CONFIG_FILE" | sed 's/^"//;s/"$//')}
    export GCP_REGION=${GCP_REGION:-$(yq ".environments.$env.region" "$CONFIG_FILE" | sed 's/^"//;s/"$//')}
    export BLOCKCHAIN_NETWORK=${BLOCKCHAIN_NETWORK:-$(yq ".environments.$env.blockchain.network" "$CONFIG_FILE" | sed 's/^"//;s/"$//')}
    export RPC_URL=${RPC_URL:-$(yq ".environments.$env.blockchain.rpc_url" "$CONFIG_FILE" | sed 's/^"//;s/"$//')}
    export CHAIN_ID=${CHAIN_ID:-$(yq ".environments.$env.blockchain.chain_id" "$CONFIG_FILE" | sed 's/^"//;s/"$//')}
    export IMAGE_REGISTRY="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/services"

    log_section "Environment Configuration"
    log_info "Environment: $ENV_NAME ($env)"
    log_info "GCP Project: $GCP_PROJECT"
    log_info "Region: $GCP_REGION"
    log_info "Blockchain: $BLOCKCHAIN_NETWORK (Chain ID: $CHAIN_ID)"
}

# ============================================================================
# SERVICE CONFIGURATION
# ============================================================================

get_service_config() {
    local service=$1
    local env=${ENVIRONMENT:-dev}

    # Convert service name to YAML key
    local yaml_key
    case "$service" in
        "risk-engine") yaml_key="risk_engine" ;;
        "relayer") yaml_key="relayer" ;;
        *) yaml_key="$service" ;;
    esac

    # Load service configuration
    export SVC_MEMORY=$(yq ".environments.$env.services.$yaml_key.memory" "$CONFIG_FILE" 2>/dev/null || echo "512Mi")
    export SVC_CPU=$(yq ".environments.$env.services.$yaml_key.cpu" "$CONFIG_FILE" 2>/dev/null || echo "1")
    export SVC_MIN_INSTANCES=$(yq ".environments.$env.services.$yaml_key.min_instances" "$CONFIG_FILE" 2>/dev/null || echo "0")
    export SVC_MAX_INSTANCES=$(yq ".environments.$env.services.$yaml_key.max_instances" "$CONFIG_FILE" 2>/dev/null || echo "10")
    export SVC_TIMEOUT=$(yq ".environments.$env.services.$yaml_key.timeout" "$CONFIG_FILE" 2>/dev/null || echo "300")
    export SVC_CONCURRENCY=$(yq ".environments.$env.services.$yaml_key.concurrency" "$CONFIG_FILE" 2>/dev/null || echo "80")
}

# ============================================================================
# SERVICE METADATA
# ============================================================================

get_service_directory() {
    local service=$1
    case "$service" in
        "settlement")
            echo "services/settlement"
            ;;
        "risk-engine")
            echo "services/risk-engine"
            ;;
        "compliance")
            echo "services/compliance"
            ;;
        "relayer")
            echo "services/relayer"
            ;;
        "contracts")
            echo "contracts"
            ;;
        *)
            log_error "Unknown service: $service"
            return 1
            ;;
    esac
}

get_service_image_name() {
    local service=$1
    case "$service" in
        "settlement")
            echo "settlement-service"
            ;;
        "risk-engine")
            echo "risk-engine"
            ;;
        "compliance")
            echo "compliance"
            ;;
        "relayer")
            echo "escrow-event-relayer"
            ;;
        *)
            log_error "Unknown service: $service"
            return 1
            ;;
    esac
}

get_service_cloud_run_name() {
    local service=$1
    case "$service" in
        "settlement")
            echo "settlement-service"
            ;;
        "risk-engine")
            echo "risk-engine"
            ;;
        "compliance")
            echo "compliance"
            ;;
        "relayer")
            echo "escrow-event-relayer"
            ;;
        *)
            log_error "Unknown service: $service"
            return 1
            ;;
    esac
}

get_service_port() {
    local service=$1
    case "$service" in
        "settlement"|"risk-engine"|"compliance")
            echo "8000"
            ;;
        "relayer")
            echo "8080"
            ;;
        *)
            echo "8000"
            ;;
    esac
}

# ============================================================================
# DEPENDENCY CHECKS
# ============================================================================

check_dependencies() {
    local missing=()

    # Check yq
    if ! command -v yq &> /dev/null; then
        missing+=("yq")
    fi

    # Check gcloud
    if ! command -v gcloud &> /dev/null; then
        missing+=("gcloud")
    fi

    # Check jq
    if ! command -v jq &> /dev/null; then
        missing+=("jq")
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing required dependencies: ${missing[*]}"
        echo ""
        echo "Installation instructions:"
        echo "  yq:     brew install yq  # macOS"
        echo "          apt install yq   # Ubuntu"
        echo "  gcloud: https://cloud.google.com/sdk/docs/install"
        echo "  jq:     brew install jq  # macOS"
        echo "          apt install jq   # Ubuntu"
        return 1
    fi
}

# ============================================================================
# IMAGE HELPERS
# ============================================================================

get_image_full_path() {
    local service=$1
    local tag=$2

    local image_name=$(get_service_image_name "$service")
    echo "${IMAGE_REGISTRY}/${image_name}:${tag}"
}

# ============================================================================
# VALIDATION HELPERS
# ============================================================================

validate_service() {
    local service=$1
    local valid_services=("settlement" "risk-engine" "compliance" "relayer" "contracts")

    for valid in "${valid_services[@]}"; do
        if [[ "$service" == "$valid" ]]; then
            return 0
        fi
    done

    log_error "Invalid service: $service"
    log_info "Valid services: ${valid_services[*]}"
    return 1
}

validate_environment() {
    local env=$1
    local valid_envs=("dev" "staging" "production" "local")

    for valid in "${valid_envs[@]}"; do
        if [[ "$env" == "$valid" ]]; then
            return 0
        fi
    done

    log_error "Invalid environment: $env"
    log_info "Valid environments: ${valid_envs[*]}"
    return 1
}

# Export functions for use in other scripts (compatible with all shells)
# Note: Functions are automatically available when script is sourced
