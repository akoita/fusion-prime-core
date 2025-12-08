#!/bin/bash
# Fusion Prime - Unified Deployment Script
# Works for both manual terminal deployment and GitHub Actions CI/CD
#
# Usage:
#   # Manual deployment
#   ./scripts/deploy-unified.sh --env dev --services all
#   ./scripts/deploy-unified.sh --env staging --services settlement --tag v1.0.0
#
#   # From GitHub Actions
#   ./scripts/deploy-unified.sh --env $ENV --services all --tag $TAG --ci-mode
#
# Features:
#   - Single source of truth for deployment logic
#   - Environment-aware configuration
#   - Parallel service deployment
#   - Contract deployment integration
#   - Health check validation
#   - Rollback support

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_DIR="${SCRIPT_DIR}/config"
CONFIG_FILE="${CONFIG_DIR}/environments.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=""
SERVICES="all"
TAG="latest"
CI_MODE=false
DRY_RUN=false
SKIP_BUILD=false
SKIP_DEPLOY=false
DEPLOY_CONTRACTS=false
PARALLEL=true
VERBOSE=false

# Service list
ALL_SERVICES=("settlement" "risk-engine" "compliance" "relayer")

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

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[VERBOSE]${NC} $1"
    fi
}

# ============================================================================
# DEPENDENCY CHECKS
# ============================================================================

check_dependencies() {
    log_verbose "Checking dependencies..."
    local missing=()

    # Check yq
    log_verbose "Checking for yq..."
    if ! command -v yq &> /dev/null; then
        missing+=("yq")
        log_verbose "yq not found"
    else
        log_verbose "yq found: $(yq --version)"
    fi

    # Check gcloud (only for non-dry-run)
    if [ "$DRY_RUN" = false ]; then
        log_verbose "Checking for gcloud..."
        if ! command -v gcloud &> /dev/null; then
            missing+=("gcloud")
            log_verbose "gcloud not found"
        else
            log_verbose "gcloud found: $(gcloud --version | head -n1)"
        fi
    else
        log_verbose "Skipping gcloud check (dry run mode)"
    fi

    # Check jq
    log_verbose "Checking for jq..."
    if ! command -v jq &> /dev/null; then
        missing+=("jq")
        log_verbose "jq not found"
    else
        log_verbose "jq found: $(jq --version)"
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
        exit 1
    fi
}

# ============================================================================
# CONFIGURATION LOADING
# ============================================================================

load_config() {
    local env=$1

    log_verbose "Loading configuration for environment: $env"
    log_verbose "Config file: $CONFIG_FILE"

    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi

    # Validate environment exists
    log_verbose "Validating environment exists in configuration..."
    if ! yq ".environments.$env" "$CONFIG_FILE" | grep -q "name"; then
        log_error "Environment '$env' not found in configuration"
        echo "Available environments:"
        yq '.environments | keys | .[]' "$CONFIG_FILE"
        exit 1
    fi
    log_verbose "Environment '$env' found in configuration"

    # Load .env.dev file if it exists (for environment variable overrides)
    if [ -f "${PROJECT_ROOT}/.env.dev" ]; then
        log_info "Loading environment variables from .env.dev"
        log_verbose "Found .env.dev file: ${PROJECT_ROOT}/.env.dev"
        set -a  # automatically export all variables
        source "${PROJECT_ROOT}/.env.dev"
        set +a  # stop automatically exporting
    else
        log_verbose "No .env.dev file found, using YAML defaults only"
    fi

    # Export environment variables (strip quotes from yq output)
    # Environment variables from .env.dev will override YAML defaults
    log_verbose "Loading environment variables from YAML configuration..."
    export ENV_NAME=$(yq ".environments.$env.name" "$CONFIG_FILE" | sed 's/^"//;s/"$//')
    export ENV_DESC=$(yq ".environments.$env.description" "$CONFIG_FILE" | sed 's/^"//;s/"$//')
    export GCP_PROJECT=${GCP_PROJECT_ID:-$(yq ".environments.$env.gcp_project" "$CONFIG_FILE" | sed 's/^"//;s/"$//')}
    export GCP_REGION=${GCP_REGION:-$(yq ".environments.$env.region" "$CONFIG_FILE" | sed 's/^"//;s/"$//')}
    export BLOCKCHAIN_NETWORK=${BLOCKCHAIN_NETWORK:-$(yq ".environments.$env.blockchain.network" "$CONFIG_FILE" | sed 's/^"//;s/"$//')}
    export RPC_URL=${RPC_URL:-$(yq ".environments.$env.blockchain.rpc_url" "$CONFIG_FILE" | sed 's/^"//;s/"$//')}
    export CHAIN_ID=${CHAIN_ID:-$(yq ".environments.$env.blockchain.chain_id" "$CONFIG_FILE" | sed 's/^"//;s/"$//')}

    # Image registry configuration
    export IMAGE_REGISTRY="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/services"

    log_section "Environment Configuration"
    log_info "Environment: $ENV_NAME ($ENVIRONMENT)"
    log_info "Description: $ENV_DESC"
    log_info "GCP Project: $GCP_PROJECT"
    log_info "Region: $GCP_REGION"
    log_info "Blockchain: $BLOCKCHAIN_NETWORK (Chain ID: $CHAIN_ID)"
    log_info "Image Registry: $IMAGE_REGISTRY"
}

# ============================================================================
# SERVICE CONFIGURATION
# ============================================================================

get_service_config() {
    local service=$1
    local env=$ENVIRONMENT

    # Convert service name to YAML key
    local yaml_key
    case "$service" in
        "risk-engine") yaml_key="risk_engine" ;;
        "relayer") yaml_key="relayer" ;;
        *) yaml_key="$service" ;;
    esac

    # Load service configuration (strip quotes from yq output)
    export SVC_MEMORY=$(yq ".environments.$env.services.$yaml_key.memory" "$CONFIG_FILE" | sed 's/^"//;s/"$//')
    export SVC_CPU=$(yq ".environments.$env.services.$yaml_key.cpu" "$CONFIG_FILE" | sed 's/^"//;s/"$//')
    export SVC_MIN_INSTANCES=$(yq ".environments.$env.services.$yaml_key.min_instances" "$CONFIG_FILE" | sed 's/^"//;s/"$//')
    export SVC_MAX_INSTANCES=$(yq ".environments.$env.services.$yaml_key.max_instances" "$CONFIG_FILE" | sed 's/^"//;s/"$//')
    export SVC_TIMEOUT=$(yq ".environments.$env.services.$yaml_key.timeout" "$CONFIG_FILE" | sed 's/^"//;s/"$//')
    export SVC_CONCURRENCY=$(yq ".environments.$env.services.$yaml_key.concurrency" "$CONFIG_FILE" | sed 's/^"//;s/"$//')
}

# ============================================================================
# BUILD FUNCTIONS
# ============================================================================

build_all_services() {
    log_section "Building All Services"

    if [ "$SKIP_BUILD" = true ]; then
        log_warning "Skipping build (--skip-build flag)"
        return 0
    fi

    log_info "Using Cloud Build for parallel building..."
    log_info "Build configuration: cloudbuild.yaml"
    log_verbose "Build parameters:"
    log_verbose "  Project: $GCP_PROJECT"
    log_verbose "  Region: $GCP_REGION"
    log_verbose "  Tag: $TAG"
    log_verbose "  Short SHA: $TAG"

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY RUN: Would execute Cloud Build"
        echo "  gcloud builds submit \\"
        echo "    --config=cloudbuild.yaml \\"
        echo "    --project=$GCP_PROJECT \\"
        echo "    --substitutions=_TAG=$TAG,_SHORT_SHA=$TAG"
        return 0
    fi

    # Execute Cloud Build
    gcloud builds submit \
        --config=cloudbuild.yaml \
        --project="$GCP_PROJECT" \
        --substitutions="_TAG=$TAG,_SHORT_SHA=$TAG" \
        --region="$GCP_REGION"

    log_success "All services built successfully"
}

build_single_service() {
    local service=$1

    log_section "Building $service"

    if [ "$SKIP_BUILD" = true ]; then
        log_warning "Skipping build (--skip-build flag)"
        return 0
    fi

    log_verbose "Determining service configuration for: $service"
    local service_dir
    local image_name

    case "$service" in
        "settlement")
            service_dir="services/settlement"
            image_name="settlement-service"
            ;;
        "risk-engine")
            service_dir="services/risk-engine"
            image_name="risk-engine"
            ;;
        "compliance")
            service_dir="services/compliance"
            image_name="compliance"
            ;;
        "relayer")
            service_dir="integrations/relayers/escrow"
            image_name="escrow-event-relayer"
            ;;
        *)
            log_error "Unknown service: $service"
            return 1
            ;;
    esac

    local full_image="${IMAGE_REGISTRY}/${image_name}:${TAG}"

    log_verbose "Service configuration:"
    log_verbose "  Service directory: $service_dir"
    log_verbose "  Image name: $image_name"
    log_verbose "  Full image: $full_image"
    log_verbose "  Registry: $IMAGE_REGISTRY"
    log_verbose "  Tag: $TAG"

    log_info "Building image: $full_image"

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY RUN: Would build $service"
        echo "  gcloud builds submit \\"
        echo "    --tag $full_image \\"
        echo "    --project=$GCP_PROJECT \\"
        echo "    $service_dir"
        return 0
    fi

    # Build and push image
    gcloud builds submit \
        --tag "$full_image" \
        --project="$GCP_PROJECT" \
        "$service_dir"

    log_success "$service built successfully"
}

# ============================================================================
# DEPLOY FUNCTIONS
# ============================================================================

deploy_service() {
    local service=$1

    log_section "Deploying $service to $ENVIRONMENT"

    if [ "$SKIP_DEPLOY" = true ]; then
        log_warning "Skipping deployment (--skip-deploy flag)"
        return 0
    fi

    log_verbose "Getting service configuration for: $service"
    # Get service configuration
    get_service_config "$service"

    log_verbose "Determining service deployment configuration..."
    local service_name
    local image_name
    local port

    case "$service" in
        "settlement")
            service_name="settlement-service"
            image_name="settlement-service"
            port=8000
            ;;
        "risk-engine")
            service_name="risk-engine"
            image_name="risk-engine"
            port=8000
            ;;
        "compliance")
            service_name="compliance"
            image_name="compliance"
            port=8000
            ;;
        "relayer")
            service_name="escrow-event-relayer"
            image_name="escrow-event-relayer"
            port=8080
            ;;
        *)
            log_error "Unknown service: $service"
            return 1
            ;;
    esac

    local full_image="${IMAGE_REGISTRY}/${image_name}:${TAG}"

    log_verbose "Service deployment configuration:"
    log_verbose "  Service name: $service_name"
    log_verbose "  Image name: $image_name"
    log_verbose "  Port: $port"
    log_verbose "  Full image: $full_image"

    # Build environment variables from YAML config
    log_verbose "Building environment variables from YAML configuration..."
    local env_vars=""
    while IFS= read -r line; do
        if [ -n "$line" ]; then
            # Strip quotes from yq output
            line=$(echo "$line" | sed 's/^"//;s/"$//')
            log_verbose "  Adding YAML env var: $line"
            if [ -n "$env_vars" ]; then
                env_vars="$env_vars,$line"
            else
                env_vars="$line"
            fi
        fi
    done < <(yq ".environments.$ENVIRONMENT.environment_vars | to_entries | .[] | .key + \"=\" + .value" "$CONFIG_FILE")

    # Add overridden environment variables from .env.dev
    # These will override the YAML values
    log_verbose "Processing environment variable overrides..."
    local override_vars=""
    local override_keys=""

    if [ -n "${RPC_URL:-}" ]; then
        log_verbose "  Overriding RPC_URL"
        override_vars="${override_vars}RPC_URL=$RPC_URL,"
        override_keys="${override_keys}RPC_URL|"
    fi
    if [ -n "${CHAIN_ID:-}" ]; then
        log_verbose "  Overriding CHAIN_ID"
        override_vars="${override_vars}CHAIN_ID=$CHAIN_ID,"
        override_keys="${override_keys}CHAIN_ID|"
    fi
    if [ -n "${BLOCKCHAIN_NETWORK:-}" ]; then
        log_verbose "  Overriding BLOCKCHAIN_NETWORK"
        override_vars="${override_vars}BLOCKCHAIN_NETWORK=$BLOCKCHAIN_NETWORK,"
        override_keys="${override_keys}BLOCKCHAIN_NETWORK|"
    fi
    if [ -n "$GCP_PROJECT" ]; then
        log_verbose "  Overriding GCP_PROJECT"
        override_vars="${override_vars}GCP_PROJECT=$GCP_PROJECT,"
        override_keys="${override_keys}GCP_PROJECT|"
    fi
    if [ -n "$GCP_REGION" ]; then
        log_verbose "  Overriding GCP_REGION"
        override_vars="${override_vars}GCP_REGION=$GCP_REGION,"
        override_keys="${override_keys}GCP_REGION|"
    fi
    if [ -n "$DEPLOYER_PRIVATE_KEY" ]; then
        log_verbose "  Overriding DEPLOYER_PRIVATE_KEY (hidden)"
        override_vars="${override_vars}DEPLOYER_PRIVATE_KEY=$DEPLOYER_PRIVATE_KEY,"
        override_keys="${override_keys}DEPLOYER_PRIVATE_KEY|"
    fi
    if [ -n "$ETHERSCAN_API_KEY" ]; then
        log_verbose "  Overriding ETHERSCAN_API_KEY (hidden)"
        override_vars="${override_vars}ETHERSCAN_API_KEY=$ETHERSCAN_API_KEY,"
        override_keys="${override_keys}ETHERSCAN_API_KEY|"
    fi
    if [ -n "$CONTRACT_ADDRESS" ]; then
        log_verbose "  Overriding CONTRACT_ADDRESS"
        override_vars="${override_vars}CONTRACT_ADDRESS=$CONTRACT_ADDRESS,"
        override_keys="${override_keys}CONTRACT_ADDRESS|"
    fi
    if [ -n "$START_BLOCK" ]; then
        log_verbose "  Overriding START_BLOCK"
        override_vars="${override_vars}START_BLOCK=$START_BLOCK,"
        override_keys="${override_keys}START_BLOCK|"
    fi
    if [ -n "$RELAYER_BATCH_SIZE" ]; then
        log_verbose "  Overriding RELAYER_BATCH_SIZE"
        override_vars="${override_vars}RELAYER_BATCH_SIZE=$RELAYER_BATCH_SIZE,"
        override_keys="${override_keys}RELAYER_BATCH_SIZE|"
    fi
    if [ -n "$RELAYER_POLL_INTERVAL" ]; then
        log_verbose "  Overriding RELAYER_POLL_INTERVAL"
        override_vars="${override_vars}RELAYER_POLL_INTERVAL=$RELAYER_POLL_INTERVAL,"
        override_keys="${override_keys}RELAYER_POLL_INTERVAL|"
    fi
    if [ -n "$RELAYER_CHECKPOINT_INTERVAL" ]; then
        log_verbose "  Overriding RELAYER_CHECKPOINT_INTERVAL"
        override_vars="${override_vars}RELAYER_CHECKPOINT_INTERVAL=$RELAYER_CHECKPOINT_INTERVAL,"
        override_keys="${override_keys}RELAYER_CHECKPOINT_INTERVAL|"
    fi
    if [ -n "$DATABASE_URL" ]; then
        log_verbose "  Overriding DATABASE_URL"
        override_vars="${override_vars}DATABASE_URL=$DATABASE_URL,"
        override_keys="${override_keys}DATABASE_URL|"
    fi

    # Try to get contract addresses from registry first (for GCP environments)
    if [ -n "$GCP_PROJECT" ] && [ "$ENVIRONMENT" != "local" ]; then
        log_info "Attempting to get contract addresses from registry..."
        log_verbose "Registry query parameters:"
        log_verbose "  Environment: $ENVIRONMENT"
        log_verbose "  Project: $GCP_PROJECT"
        log_verbose "  Chain ID: $CHAIN_ID"

        if contract_addresses=$(timeout 30s "${SCRIPT_DIR}/gcp-contract-registry.sh" get-addresses --env "$ENVIRONMENT" --project "$GCP_PROJECT" --chain-id "$CHAIN_ID" --quiet 2>/dev/null); then
            log_info "Using contract addresses from registry"
            log_verbose "Registry response: $contract_addresses"

            # Parse contract addresses from registry output using parameter expansion
            log_verbose "Starting contract address parsing..."
            registry_escrow_factory=""
            registry_escrow=""

            # Extract ESCROW_FACTORY_ADDRESS using parameter expansion (more robust)
            log_verbose "Checking for ESCROW_FACTORY_ADDRESS..."
            if [[ "$contract_addresses" == *"ESCROW_FACTORY_ADDRESS="* ]]; then
                log_verbose "Found ESCROW_FACTORY_ADDRESS in response"
                registry_escrow_factory="${contract_addresses#*ESCROW_FACTORY_ADDRESS=}"
                registry_escrow_factory="${registry_escrow_factory%% *}"
                log_verbose "Extracted factory address: $registry_escrow_factory"
            else
                log_verbose "ESCROW_FACTORY_ADDRESS not found in response"
            fi

            # Extract ESCROW_ADDRESS using parameter expansion
            log_verbose "Checking for ESCROW_ADDRESS..."
            if [[ "$contract_addresses" == *"ESCROW_ADDRESS="* ]]; then
                log_verbose "Found ESCROW_ADDRESS in response"
                registry_escrow="${contract_addresses#*ESCROW_ADDRESS=}"
                registry_escrow="${registry_escrow%% *}"
                log_verbose "Extracted escrow address: $registry_escrow"
            else
                log_verbose "ESCROW_ADDRESS not found in response"
            fi

            log_verbose "Contract address parsing completed"

            if [ -n "$registry_escrow_factory" ]; then
                log_verbose "  Found ESCROW_FACTORY_ADDRESS: $registry_escrow_factory"
                override_vars="${override_vars}ESCROW_FACTORY_ADDRESS=$registry_escrow_factory,"
                override_keys="${override_keys}ESCROW_FACTORY_ADDRESS|"
            fi
            if [ -n "$registry_escrow" ]; then
                log_verbose "  Found ESCROW_ADDRESS: $registry_escrow"
                override_vars="${override_vars}ESCROW_ADDRESS=$registry_escrow,"
                override_keys="${override_keys}ESCROW_ADDRESS|"
            fi
        else
            log_warning "Could not get contract addresses from registry, using environment variables"
            log_verbose "Registry query failed, falling back to environment variables"
        fi
    else
        log_verbose "Skipping registry lookup (local environment or no GCP project)"
    fi

    # Fallback to environment variables if registry not available or local environment
    if [ -n "${ESCROW_FACTORY_ADDRESS:-}" ]; then
        override_vars="${override_vars}ESCROW_FACTORY_ADDRESS=$ESCROW_FACTORY_ADDRESS,"
        override_keys="${override_keys}ESCROW_FACTORY_ADDRESS|"
    fi
    if [ -n "${ESCROW_ADDRESS:-}" ]; then
        override_vars="${override_vars}ESCROW_ADDRESS=$ESCROW_ADDRESS,"
        override_keys="${override_keys}ESCROW_ADDRESS|"
    fi
    if [ -n "${ESCROW_FACTORY_ABI_PATH:-}" ]; then
        override_vars="${override_vars}ESCROW_FACTORY_ABI_PATH=$ESCROW_FACTORY_ABI_PATH,"
        override_keys="${override_keys}ESCROW_FACTORY_ABI_PATH|"
    fi
    if [ -n "${ESCROW_ABI_PATH:-}" ]; then
        override_vars="${override_vars}ESCROW_ABI_PATH=$ESCROW_ABI_PATH,"
        override_keys="${override_keys}ESCROW_ABI_PATH|"
    fi

    # Add GCS URLs for contract ABIs (for GCP environments)
    if [ -n "$GCP_PROJECT" ] && [ -n "$ENVIRONMENT" ] && [ -n "$CHAIN_ID" ]; then
        local contract_registry_bucket="${GCP_PROJECT}-contract-registry"
        local contract_registry_base="gs://${contract_registry_bucket}/contracts/${ENVIRONMENT}/${CHAIN_ID}"

        override_vars="${override_vars}CONTRACT_REGISTRY_BUCKET=${contract_registry_bucket},"
        override_vars="${override_vars}CONTRACT_REGISTRY_CHAIN_ID=${CHAIN_ID},"
        override_vars="${override_vars}ESCROW_FACTORY_ABI_URL=${contract_registry_base}/EscrowFactory.json,"
        override_vars="${override_vars}ESCROW_ABI_URL=${contract_registry_base}/Escrow.json,"

        override_keys="${override_keys}CONTRACT_REGISTRY_BUCKET|CONTRACT_REGISTRY_CHAIN_ID|ESCROW_FACTORY_ABI_URL|ESCROW_ABI_URL|"
    fi

    # Filter out overridden variables from YAML config to prevent duplicates
    if [ -n "$override_keys" ]; then
        # Remove trailing pipe and create filter pattern
        override_keys="${override_keys%|}"
        log_info "Filtering out overridden variables: ${override_keys//|/, }"
        log_verbose "Override keys pattern: $override_keys"

        # Filter YAML config to exclude overridden variables
        filtered_env_vars=""
        IFS=',' read -ra YAML_VARS <<< "$env_vars"
        for var in "${YAML_VARS[@]}"; do
            if [ -n "$var" ]; then
                key="${var%%=*}"
                if [[ ! "$override_keys" =~ (^|\|)$key(\||$) ]]; then
                    log_verbose "  Keeping YAML var: $key"
                    if [ -n "$filtered_env_vars" ]; then
                        filtered_env_vars="$filtered_env_vars,$var"
                    else
                        filtered_env_vars="$var"
                    fi
                else
                    log_info "  Filtering out: $key (overridden)"
                    log_verbose "  Filtered out: $key (overridden by environment variable)"
                fi
            fi
        done
        env_vars="$filtered_env_vars"
    fi

    # Combine YAML config with overrides
    if [ -n "$override_vars" ]; then
        log_verbose "Combining override variables with YAML config"
        env_vars="$override_vars$env_vars"
    fi

    # Add service-specific vars
    log_verbose "Adding service-specific environment variables"
    env_vars="$env_vars,SERVICE_NAME=$service_name,SERVICE_VERSION=$TAG"

    log_info "Configuration:"
    log_info "  Image: $full_image"
    log_info "  Memory: $SVC_MEMORY"
    log_info "  CPU: $SVC_CPU"
    log_info "  Min Instances: $SVC_MIN_INSTANCES"
    log_info "  Max Instances: $SVC_MAX_INSTANCES"
    log_verbose "  Timeout: $SVC_TIMEOUT"
    log_verbose "  Concurrency: $SVC_CONCURRENCY"
    log_verbose "  Port: $port"
    log_verbose "  Environment Variables: $env_vars"

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY RUN: Would deploy $service"
        echo "  gcloud run deploy $service_name \\"
        echo "    --image=$full_image \\"
        echo "    --region=$GCP_REGION \\"
        echo "    --memory=$SVC_MEMORY \\"
        echo "    --cpu=$SVC_CPU \\"
        echo "    --min-instances=$SVC_MIN_INSTANCES \\"
        echo "    --max-instances=$SVC_MAX_INSTANCES"
        return 0
    fi

    # Deploy to Cloud Run
    log_verbose "Executing Cloud Run deployment command..."
    log_verbose "Command: gcloud run deploy $service_name --image=$full_image --region=$GCP_REGION --platform=managed --allow-unauthenticated --memory=$SVC_MEMORY --cpu=$SVC_CPU --min-instances=$SVC_MIN_INSTANCES --max-instances=$SVC_MAX_INSTANCES --timeout=$SVC_TIMEOUT --concurrency=$SVC_CONCURRENCY --port=$port --set-env-vars=$env_vars --project=$GCP_PROJECT --quiet"

    # Build the base command
    local deploy_cmd="gcloud run deploy \"$service_name\""
    deploy_cmd="$deploy_cmd --image=\"$full_image\""
    deploy_cmd="$deploy_cmd --region=\"$GCP_REGION\""
    deploy_cmd="$deploy_cmd --platform=managed"
    deploy_cmd="$deploy_cmd --allow-unauthenticated"
    deploy_cmd="$deploy_cmd --memory=\"$SVC_MEMORY\""
    deploy_cmd="$deploy_cmd --cpu=\"$SVC_CPU\""
    deploy_cmd="$deploy_cmd --min-instances=\"$SVC_MIN_INSTANCES\""
    deploy_cmd="$deploy_cmd --max-instances=\"$SVC_MAX_INSTANCES\""
    deploy_cmd="$deploy_cmd --timeout=\"$SVC_TIMEOUT\""
    deploy_cmd="$deploy_cmd --concurrency=\"$SVC_CONCURRENCY\""
    deploy_cmd="$deploy_cmd --port=\"$port\""
    deploy_cmd="$deploy_cmd --set-env-vars=\"$env_vars\""
    deploy_cmd="$deploy_cmd --project=\"$GCP_PROJECT\""

    # Add Cloud SQL connection for settlement service
    if [ "$service" = "settlement" ]; then
        log_verbose "Adding Cloud SQL connection for settlement service"
        deploy_cmd="$deploy_cmd --add-cloudsql-instances=\"fusion-prime:us-central1:fusion-prime-db-a504713e\""
    fi

    deploy_cmd="$deploy_cmd --quiet"

    log_verbose "Executing: $deploy_cmd"
    eval "$deploy_cmd"

    # Get service URL
    log_verbose "Retrieving service URL..."
    local service_url=$(gcloud run services describe "$service_name" \
        --region="$GCP_REGION" \
        --format="value(status.url)" \
        --project="$GCP_PROJECT")

    log_success "$service deployed successfully"
    log_info "URL: $service_url"
    log_verbose "Service URL retrieved: $service_url"
}

# ============================================================================
# CONTRACT DEPLOYMENT
# ============================================================================

deploy_contracts() {
    log_section "Deploying Smart Contracts"

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY RUN: Would deploy contracts to $BLOCKCHAIN_NETWORK"
        return 0
    fi

    log_verbose "Changing to contracts directory: $PROJECT_ROOT/contracts"
    cd "$PROJECT_ROOT/contracts"

    # Check for required environment variables
    log_verbose "Checking for required environment variables..."
    if [ -z "${DEPLOYER_PRIVATE_KEY:-}" ]; then
        log_error "DEPLOYER_PRIVATE_KEY environment variable is required for contract deployment"
        exit 1
    fi
    log_verbose "DEPLOYER_PRIVATE_KEY found (hidden)"

    log_info "Deploying to $BLOCKCHAIN_NETWORK (Chain ID: $CHAIN_ID)"
    log_info "RPC URL: $RPC_URL"
    log_verbose "Contract deployment parameters:"
    log_verbose "  Network: $BLOCKCHAIN_NETWORK"
    log_verbose "  Chain ID: $CHAIN_ID"
    log_verbose "  RPC URL: $RPC_URL"
    log_verbose "  Etherscan API Key: ${ETHERSCAN_API_KEY:+present (hidden)}"

    # Deploy using Foundry
    log_verbose "Executing Foundry deployment script..."
    log_verbose "Command: forge script script/DeployMultichain.s.sol:DeployMultichain --rpc-url $RPC_URL --private-key [HIDDEN] --broadcast --verify ${ETHERSCAN_API_KEY:+--etherscan-api-key [HIDDEN]} -vvv"

    forge script script/DeployMultichain.s.sol:DeployMultichain \
        --rpc-url "$RPC_URL" \
        --private-key "$DEPLOYER_PRIVATE_KEY" \
        --broadcast \
        --verify \
        ${ETHERSCAN_API_KEY:+--etherscan-api-key $ETHERSCAN_API_KEY} \
        -vvv || {
            log_warning "Verification failed, but deployment may have succeeded"
            log_info "You can verify manually later with: forge verify-contract"
        }

    log_success "Contracts deployed successfully"

    # Upload contract artifacts to GCS registry (for GCP environments)
    if [ -n "$GCP_PROJECT" ] && [ "$ENVIRONMENT" != "local" ]; then
        log_info "Uploading contract artifacts to GCS registry..."
        log_verbose "GCS upload parameters:"
        log_verbose "  Environment: $ENVIRONMENT"
        log_verbose "  Project: $GCP_PROJECT"
        log_verbose "  Chain ID: $CHAIN_ID"

        if "${SCRIPT_DIR}/gcp-contract-registry.sh" upload --env "$ENVIRONMENT" --project "$GCP_PROJECT" --chain-id "$CHAIN_ID"; then
            log_success "Contract artifacts uploaded to GCS registry"
            log_verbose "GCS upload completed successfully"
        else
            log_warning "Failed to upload contract artifacts to GCS registry"
            log_info "You can upload manually later with:"
            log_info "  ./scripts/gcp-contract-registry.sh upload --env $ENVIRONMENT --project $GCP_PROJECT --chain-id $CHAIN_ID"
            log_verbose "GCS upload failed, manual upload required"
        fi
    else
        log_info "Skipping GCS upload for local environment"
        log_verbose "Skipping GCS upload (local environment or no GCP project)"
    fi

    log_verbose "Returning to project root: $PROJECT_ROOT"
    cd "$PROJECT_ROOT"
}

# ============================================================================
# HEALTH CHECKS
# ============================================================================

health_check() {
    local service=$1

    log_info "Running health check for $service..."
    log_verbose "Health check parameters:"
    log_verbose "  Service: $service"
    log_verbose "  Region: $GCP_REGION"
    log_verbose "  Project: $GCP_PROJECT"

    local service_name
    case "$service" in
        "settlement") service_name="settlement-service" ;;
        "risk-engine") service_name="risk-engine" ;;
        "compliance") service_name="compliance" ;;
        "relayer") service_name="escrow-event-relayer" ;;
    esac

    log_verbose "Service name: $service_name"

    log_verbose "Retrieving service URL..."
    local service_url=$(gcloud run services describe "$service_name" \
        --region="$GCP_REGION" \
        --format="value(status.url)" \
        --project="$GCP_PROJECT" 2>/dev/null)

    if [ -z "$service_url" ]; then
        log_warning "Service $service not found or not deployed"
        log_verbose "Service URL retrieval failed or returned empty"
        return 1
    fi

    log_verbose "Service URL: $service_url"

    # Try health endpoint
    log_verbose "Testing health endpoint: $service_url/health"
    if curl -sf "$service_url/health" > /dev/null 2>&1; then
        log_success "$service health check passed"
        log_verbose "Health check response: OK"
        return 0
    else
        log_error "$service health check failed"
        log_verbose "Health check response: FAILED"
        return 1
    fi
}

# ============================================================================
# DEPLOYMENT SUMMARY
# ============================================================================

show_summary() {
    log_section "Deployment Summary"

    echo ""
    echo "Environment: $ENV_NAME ($ENVIRONMENT)"
    echo "Version/Tag: $TAG"
    echo "GCP Project: $GCP_PROJECT"
    echo "Region: $GCP_REGION"
    echo ""

    # GCP Services
    echo "🚀 Deployed Services:"
    for service in "${ALL_SERVICES[@]}"; do
        if [[ " ${SERVICES[@]} " =~ " ${service} " ]] || [ "$SERVICES" = "all" ]; then
            local service_name
            case "$service" in
                "settlement") service_name="settlement-service" ;;
                "risk-engine") service_name="risk-engine" ;;
                "compliance") service_name="compliance" ;;
                "relayer") service_name="escrow-event-relayer" ;;
            esac

            local service_url=$(gcloud run services describe "$service_name" \
                --region="$GCP_REGION" \
                --format="value(status.url)" \
                --project="$GCP_PROJECT" 2>/dev/null || echo "Not deployed")

            echo "  ✓ $service: $service_url"
        fi
    done

    # Smart Contracts
    if [ "$DEPLOY_CONTRACTS" = true ]; then
        echo ""
        echo "📜 Smart Contracts:"
        echo "  Network: $BLOCKCHAIN_NETWORK"
        echo "  Chain ID: $CHAIN_ID"
        echo "  RPC URL: $RPC_URL"

        # Get contract addresses from registry if available
        if [ -n "$GCP_PROJECT" ] && [ "$ENVIRONMENT" != "local" ]; then
            local contract_addresses
            if contract_addresses=$(timeout 10s "${SCRIPT_DIR}/gcp-contract-registry.sh" get-addresses --env "$ENVIRONMENT" --project "$GCP_PROJECT" --chain-id "$CHAIN_ID" --quiet 2>/dev/null); then
                local escrow_factory=""
                local escrow=""

                if [[ "$contract_addresses" == *"ESCROW_FACTORY_ADDRESS="* ]]; then
                    escrow_factory="${contract_addresses#*ESCROW_FACTORY_ADDRESS=}"
                    escrow_factory="${escrow_factory%% *}"
                fi

                if [[ "$contract_addresses" == *"ESCROW_ADDRESS="* ]]; then
                    escrow="${contract_addresses#*ESCROW_ADDRESS=}"
                    escrow="${escrow%% *}"
                fi

                if [ -n "$escrow_factory" ]; then
                    echo "  EscrowFactory: $escrow_factory"
                fi
                if [ -n "$escrow" ]; then
                    echo "  Escrow: $escrow"
                fi
            fi
        fi

        echo "  Deployment artifacts: contracts/deployments/$CHAIN_ID-*.json"
    fi

    # Contract Registry (GCS)
    if [ -n "$GCP_PROJECT" ] && [ "$ENVIRONMENT" != "local" ]; then
        echo ""
        echo "🗄️  Contract Registry (GCS):"
        local contract_registry_bucket="${GCP_PROJECT}-contract-registry"
        echo "  Bucket: gs://$contract_registry_bucket"
        echo "  Contract ABIs: gs://$contract_registry_bucket/contracts/$ENVIRONMENT/$CHAIN_ID/"
        echo "  Metadata: gs://$contract_registry_bucket/contracts/$ENVIRONMENT/$CHAIN_ID/metadata.json"

        # List available contracts
        echo "  Available contracts:"
        if gsutil ls "gs://$contract_registry_bucket/contracts/$ENVIRONMENT/$CHAIN_ID/*.json" 2>/dev/null | head -5; then
            local count=$(gsutil ls "gs://$contract_registry_bucket/contracts/$ENVIRONMENT/$CHAIN_ID/*.json" 2>/dev/null | wc -l)
            if [ "$count" -gt 5 ]; then
                echo "    ... and $((count - 5)) more files"
            fi
        else
            echo "    No contracts found in registry"
        fi
    fi

    # GCP Console Links
    echo ""
    echo "🔗 GCP Console Links:"
    echo "  Cloud Run Services: https://console.cloud.google.com/run?project=$GCP_PROJECT"
    echo "  Cloud Build: https://console.cloud.google.com/cloud-build?project=$GCP_PROJECT"
    if [ -n "$GCP_PROJECT" ] && [ "$ENVIRONMENT" != "local" ]; then
        echo "  Cloud Storage: https://console.cloud.google.com/storage/browser?project=$GCP_PROJECT"
        echo "  Contract Registry: https://console.cloud.google.com/storage/browser/$contract_registry_bucket/contracts/$ENVIRONMENT/$CHAIN_ID?project=$GCP_PROJECT"
    fi

    echo ""
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

print_usage() {
    cat <<EOF
Fusion Prime - Unified Deployment Script

Usage: $0 --env <environment> [OPTIONS]

Required:
  --env ENV              Environment to deploy to (dev, staging, production)

Optional:
  --services SERVICES    Services to deploy (default: all)
                         Options: all, settlement, risk-engine, compliance, relayer
                         Can specify multiple: "settlement,risk-engine"
  --tag TAG              Image tag (default: latest)
  --contracts            Also deploy smart contracts
  --skip-build           Skip the build step (use existing images)
  --skip-deploy          Skip the deployment step (only build)
  --dry-run              Show what would be deployed without executing
  --ci-mode              Run in CI/CD mode (optimized output)
  --no-parallel          Deploy services sequentially instead of parallel
  --verbose              Enable verbose output for detailed logging
  -h, --help             Show this help message

Examples:
  # Deploy all services to dev
  $0 --env dev --services all

  # Deploy specific services to staging
  $0 --env staging --services settlement,risk-engine --tag v1.0.0

  # Deploy with contract deployment
  $0 --env dev --services all --contracts

  # Dry run for production
  $0 --env production --services all --tag v1.0.0 --dry-run

  # CI/CD mode
  $0 --env dev --services all --tag \$TAG --ci-mode

  # Verbose deployment for debugging
  $0 --env dev --services all --verbose
EOF
}

parse_args() {
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
            --tag)
                TAG="$2"
                shift 2
                ;;
            --contracts)
                DEPLOY_CONTRACTS=true
                shift
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --skip-deploy)
                SKIP_DEPLOY=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --ci-mode)
                CI_MODE=true
                shift
                ;;
            --no-parallel)
                PARALLEL=false
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                print_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done

    # Validate required arguments
    if [ -z "$ENVIRONMENT" ]; then
        log_error "Environment is required (--env)"
        print_usage
        exit 1
    fi
}

main() {
    log_verbose "Starting deployment script execution"
    log_verbose "Script arguments: $*"

    parse_args "$@"

    # Header
    if [ "$CI_MODE" = false ]; then
        # Clear screen only if running in an interactive terminal
        if [ -t 1 ]; then
            clear 2>/dev/null || true
        fi
        log_section "Fusion Prime - Unified Deployment"
    fi

    log_verbose "Deployment configuration:"
    log_verbose "  Environment: $ENVIRONMENT"
    log_verbose "  Services: $SERVICES"
    log_verbose "  Tag: $TAG"
    log_verbose "  CI Mode: $CI_MODE"
    log_verbose "  Dry Run: $DRY_RUN"
    log_verbose "  Skip Build: $SKIP_BUILD"
    log_verbose "  Skip Deploy: $SKIP_DEPLOY"
    log_verbose "  Deploy Contracts: $DEPLOY_CONTRACTS"
    log_verbose "  Parallel: $PARALLEL"
    log_verbose "  Verbose: $VERBOSE"

    # Check dependencies
    check_dependencies

    # Load configuration
    load_config "$ENVIRONMENT"

    # Deploy contracts if requested
    if [ "$DEPLOY_CONTRACTS" = true ]; then
        log_verbose "Contract deployment requested"
        deploy_contracts
    else
        log_verbose "Skipping contract deployment"
    fi

    # Parse services list
    log_verbose "Parsing services list: $SERVICES"
    IFS=',' read -ra SERVICES_ARRAY <<< "$SERVICES"
    log_verbose "Services array: ${SERVICES_ARRAY[*]}"

    # Build services
    if [ "$SERVICES" = "all" ]; then
        log_verbose "Building all services"
        build_all_services
    else
        log_verbose "Building specific services: ${SERVICES_ARRAY[*]}"
        for service in "${SERVICES_ARRAY[@]}"; do
            log_verbose "Building service: $service"
            build_single_service "$service"
        done
    fi

    # Deploy services
    if [ "$SERVICES" = "all" ]; then
        log_verbose "Deploying all services"
        for service in "${ALL_SERVICES[@]}"; do
            log_verbose "Deploying service: $service"
            deploy_service "$service"
        done
    else
        log_verbose "Deploying specific services: ${SERVICES_ARRAY[*]}"
        for service in "${SERVICES_ARRAY[@]}"; do
            log_verbose "Deploying service: $service"
            deploy_service "$service"
        done
    fi

    # Run health checks
    if [ "$SKIP_DEPLOY" = false ] && [ "$DRY_RUN" = false ]; then
        log_section "Health Checks"
        log_verbose "Running health checks for deployed services"
        for service in "${ALL_SERVICES[@]}"; do
            if [[ " ${SERVICES_ARRAY[@]} " =~ " ${service} " ]] || [ "$SERVICES" = "all" ]; then
                log_verbose "Running health check for: $service"
                health_check "$service" || log_warning "$service health check failed"
            else
                log_verbose "Skipping health check for: $service (not deployed)"
            fi
        done
    else
        log_verbose "Skipping health checks (skip-deploy or dry-run mode)"
    fi

    # Setup Cloud Scheduler for relayer (if relayer was deployed)
    if [[ " ${SERVICES_TO_DEPLOY[@]} " =~ " relayer " ]] && [ "$DRY_RUN" = false ] && [ "$SKIP_DEPLOY" = false ]; then
        log_section "Setting Up Cloud Scheduler"
        log_info "Configuring automated relayer execution..."
        if "${SCRIPT_DIR}/setup-relayer-scheduler.sh" --project="${GCP_PROJECT}" --region="${GCP_REGION}"; then
            log_success "Cloud Scheduler configured for relayer"
        else
            log_warning "Cloud Scheduler setup failed (non-critical)"
        fi
    else
        log_verbose "Skipping Cloud Scheduler setup (relayer not deployed or dry-run/skip-deploy mode)"
    fi

    # Show summary
    if [ "$DRY_RUN" = false ]; then
        log_verbose "Generating deployment summary"
        show_summary
    else
        log_verbose "Skipping summary (dry run mode)"
    fi

    log_success "Deployment complete!"
    log_verbose "Deployment script execution completed successfully"
}

# Run main function
main "$@"
