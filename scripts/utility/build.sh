#!/bin/bash
# Fusion Prime - Build Helper Script
# Simplifies building services with Cloud Build

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${GCP_PROJECT:-fusion-prime}
REGION=${GCP_REGION:-us-central1}
REPOSITORY=${ARTIFACT_REGISTRY_REPO:-services}
TAG=${BUILD_TAG:-latest}

# Functions
print_usage() {
    cat <<EOF
${BLUE}Fusion Prime Build Script${NC}

Usage: $0 [OPTIONS] <service>

Services:
  all              Build all services (settlement + relayer)
  settlement       Build settlement service only
  relayer          Build escrow event relayer only

Options:
  -t, --tag TAG         Image tag (default: latest)
  -p, --project ID      GCP project ID (default: fusion-prime)
  -r, --region REGION   Artifact Registry region (default: us-central1)
  -d, --dry-run         Show commands without executing
  -h, --help            Show this help message

Examples:
  # Build all services with default settings
  $0 all

  # Build settlement service with custom tag
  $0 --tag v1.0.0 settlement

  # Build for different project
  $0 --project my-project --tag dev relayer

  # Dry run to see what would be executed
  $0 --dry-run all

Environment Variables:
  GCP_PROJECT              GCP project ID
  GCP_REGION               Artifact Registry region
  ARTIFACT_REGISTRY_REPO   Repository name
  BUILD_TAG                Image tag
EOF
}

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

run_build() {
    local config=$1
    local service_name=$2

    log_info "Building ${service_name}..."
    log_info "Config: ${config}"
    log_info "Tag: ${TAG}"
    log_info "Project: ${PROJECT_ID}"

    # Get current git commit SHA (first 7 chars)
    local short_sha=""
    if git rev-parse --short HEAD >/dev/null 2>&1; then
        short_sha=$(git rev-parse --short HEAD)
        log_info "Git SHA: ${short_sha}"
    else
        short_sha="manual"
        log_warning "Not in a git repository, using 'manual' as SHA"
    fi

    if [ "${DRY_RUN}" = true ]; then
        log_warning "DRY RUN - Would execute:"
        echo "  gcloud builds submit \\"
        echo "    --config=${config} \\"
        echo "    --substitutions=_TAG=${TAG},_REGION=${REGION},_REPOSITORY=${REPOSITORY},_SHORT_SHA=${short_sha} \\"
        echo "    --project=${PROJECT_ID}"
    else
        gcloud builds submit \
            --config="${config}" \
            --substitutions="_TAG=${TAG},_REGION=${REGION},_REPOSITORY=${REPOSITORY},_SHORT_SHA=${short_sha}" \
            --project="${PROJECT_ID}" || {
            log_error "Build failed for ${service_name}"
            return 1
        }
        log_success "${service_name} build completed"
    fi
}

# Parse arguments
DRY_RUN=false
SERVICE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -p|--project)
            PROJECT_ID="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        all|settlement|relayer)
            SERVICE="$1"
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Validate service argument
if [ -z "${SERVICE}" ]; then
    log_error "No service specified"
    print_usage
    exit 1
fi

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# Execute builds
log_info "==================================="
log_info "Fusion Prime - Build Services"
log_info "==================================="
log_info "Project: ${PROJECT_ID}"
log_info "Region: ${REGION}"
log_info "Repository: ${REPOSITORY}"
log_info "Tag: ${TAG}"
log_info "Service: ${SERVICE}"
log_info "==================================="
echo

case "${SERVICE}" in
    all)
        run_build "cloudbuild.yaml" "All Services"
        ;;
    settlement)
        run_build "services/settlement/cloudbuild.yaml" "Settlement Service"
        ;;
    relayer)
        run_build "integrations/relayers/escrow/cloudbuild.yaml" "Escrow Event Relayer"
        ;;
    *)
        log_error "Invalid service: ${SERVICE}"
        print_usage
        exit 1
        ;;
esac

if [ "${DRY_RUN}" = false ]; then
    echo
    log_success "==================================="
    log_success "Build completed successfully!"
    log_success "==================================="
    echo
    log_info "View build history:"
    echo "  https://console.cloud.google.com/cloud-build/builds?project=${PROJECT_ID}"
    echo
    log_info "View images:"
    echo "  https://console.cloud.google.com/artifacts/docker/${PROJECT_ID}/${REGION}/${REPOSITORY}?project=${PROJECT_ID}"
fi
