#!/bin/bash
# Setup Cloud Scheduler for Escrow Event Relayer
# This script creates a Cloud Scheduler job that triggers the relayer every 5 minutes

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default values
DEFAULT_PROJECT="fusion-prime"
DEFAULT_REGION="us-central1"
DEFAULT_SCHEDULE="*/5 * * * *"  # Every 5 minutes
DEFAULT_JOB_NAME="relayer-scheduler"
DEFAULT_RELAYER_JOB="escrow-event-relayer"
DEFAULT_TIMEOUT="600s"

# Functions
print_usage() {
    cat <<EOF
${BLUE}Fusion Prime - Cloud Scheduler Setup${NC}

Sets up automated Cloud Scheduler to trigger the escrow event relayer.

Usage: $0 [OPTIONS]

Options:
  -p, --project PROJECT     GCP project ID (default: ${DEFAULT_PROJECT})
  -r, --region REGION       GCP region (default: ${DEFAULT_REGION})
  -s, --schedule SCHEDULE   Cron schedule (default: ${DEFAULT_SCHEDULE})
  -j, --job-name NAME       Scheduler job name (default: ${DEFAULT_JOB_NAME})
  -t, --timeout TIMEOUT     Job timeout (default: ${DEFAULT_TIMEOUT})
  -d, --delete              Delete the scheduler job
  -h, --help                Show this help message

Examples:
  # Create scheduler with defaults (every 5 minutes)
  $0

  # Create scheduler with custom schedule (every 10 minutes)
  $0 --schedule "*/10 * * * *"

  # Delete the scheduler
  $0 --delete

Cron Schedule Format:
  * * * * *
  │ │ │ │ │
  │ │ │ │ └─── Day of week (0-7, Sunday=0 or 7)
  │ │ │ └───── Month (1-12)
  │ │ └─────── Day of month (1-31)
  │ └───────── Hour (0-23)
  └─────────── Minute (0-59)

Common Examples:
  */5 * * * *    - Every 5 minutes
  */10 * * * *   - Every 10 minutes
  0 * * * *      - Every hour
  0 */2 * * *    - Every 2 hours
  0 0 * * *      - Daily at midnight
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

# Parse command line arguments
PROJECT="${DEFAULT_PROJECT}"
REGION="${DEFAULT_REGION}"
SCHEDULE="${DEFAULT_SCHEDULE}"
JOB_NAME="${DEFAULT_JOB_NAME}"
RELAYER_JOB="${DEFAULT_RELAYER_JOB}"
TIMEOUT="${DEFAULT_TIMEOUT}"
DELETE_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--project)
            PROJECT="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -s|--schedule)
            SCHEDULE="$2"
            shift 2
            ;;
        -j|--job-name)
            JOB_NAME="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -d|--delete)
            DELETE_MODE=true
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

# Get service account email
get_service_account() {
    local project=$1
    local default_sa="${project//-/}@${project}.iam.gserviceaccount.com"

    # Try to get the compute service account
    local compute_sa=$(gcloud iam service-accounts list \
        --project="${project}" \
        --filter="email:compute@developer.gserviceaccount.com" \
        --format="value(email)" 2>/dev/null || echo "")

    if [ -n "$compute_sa" ]; then
        echo "$compute_sa"
    else
        # Fall back to project number-compute format
        local project_number=$(gcloud projects describe "${project}" --format="value(projectNumber)")
        echo "${project_number}-compute@developer.gserviceaccount.com"
    fi
}

# Delete scheduler job
delete_scheduler() {
    log_info "Deleting Cloud Scheduler job: ${JOB_NAME}"

    if gcloud scheduler jobs describe "${JOB_NAME}" \
        --location="${REGION}" \
        --project="${PROJECT}" &>/dev/null; then

        gcloud scheduler jobs delete "${JOB_NAME}" \
            --location="${REGION}" \
            --project="${PROJECT}" \
            --quiet

        log_success "Cloud Scheduler job deleted"
    else
        log_warning "Cloud Scheduler job ${JOB_NAME} not found"
    fi
}

# Create or update scheduler job
create_scheduler() {
    log_info "Setting up Cloud Scheduler for Escrow Event Relayer"
    log_info "Project: ${PROJECT}"
    log_info "Region: ${REGION}"
    log_info "Schedule: ${SCHEDULE}"
    log_info "Job Name: ${JOB_NAME}"

    # Get service account
    SERVICE_ACCOUNT=$(get_service_account "${PROJECT}")
    log_info "Service Account: ${SERVICE_ACCOUNT}"

    # Construct the relayer job execution URL
    RELAYER_URL="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/${RELAYER_JOB}:run"

    # Check if scheduler job already exists
    if gcloud scheduler jobs describe "${JOB_NAME}" \
        --location="${REGION}" \
        --project="${PROJECT}" &>/dev/null; then

        log_warning "Scheduler job ${JOB_NAME} already exists"
        log_info "Updating existing job..."

        gcloud scheduler jobs update http "${JOB_NAME}" \
            --location="${REGION}" \
            --project="${PROJECT}" \
            --schedule="${SCHEDULE}" \
            --uri="${RELAYER_URL}" \
            --http-method=POST \
            --oauth-service-account-email="${SERVICE_ACCOUNT}" \
            --attempt-deadline="${TIMEOUT}"

        log_success "Cloud Scheduler job updated"
    else
        log_info "Creating new scheduler job..."

        gcloud scheduler jobs create http "${JOB_NAME}" \
            --location="${REGION}" \
            --project="${PROJECT}" \
            --schedule="${SCHEDULE}" \
            --uri="${RELAYER_URL}" \
            --http-method=POST \
            --oauth-service-account-email="${SERVICE_ACCOUNT}" \
            --attempt-deadline="${TIMEOUT}" \
            --description="Triggers escrow event relayer to process blockchain events"

        log_success "Cloud Scheduler job created"
    fi

    # Show scheduler details
    echo ""
    log_info "Scheduler Configuration:"
    gcloud scheduler jobs describe "${JOB_NAME}" \
        --location="${REGION}" \
        --project="${PROJECT}" \
        --format="yaml(name,schedule,state,timeZone,httpTarget.uri)"

    echo ""
    log_success "Cloud Scheduler setup complete!"
    log_info "The relayer will now run automatically: ${SCHEDULE}"
    log_info "Next execution: $(gcloud scheduler jobs describe ${JOB_NAME} --location=${REGION} --project=${PROJECT} --format='value(status.lastAttemptTime)')"
}

# Main execution
main() {
    if [ "$DELETE_MODE" = true ]; then
        delete_scheduler
    else
        create_scheduler
    fi
}

main
