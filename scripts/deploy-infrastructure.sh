#!/bin/bash
# Deploy Infrastructure with Environment Support
# Usage: ./scripts/deploy-infrastructure.sh <environment> [action]

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
TERRAFORM_DIR="${PROJECT_ROOT}/infra/terraform/project"

# Functions
print_usage() {
    cat <<EOF
${BLUE}Fusion Prime - Infrastructure Deployment${NC}

Usage: $0 [OPTIONS] <environment> [action]

Environments:
  dev         Development environment
  staging     Staging environment
  production  Production environment

Actions:
  plan        Plan infrastructure changes (default)
  apply       Apply infrastructure changes
  destroy     Destroy infrastructure (requires confirmation)
  init        Initialize Terraform

Options:
  -h, --help            Show this help message

Examples:
  # Plan infrastructure for development
  $0 dev plan

  # Apply infrastructure for staging
  $0 staging apply

  # Destroy production infrastructure (with confirmation)
  $0 production destroy

Environment Variables:
  TF_VAR_project_id     Override project ID
  TF_VAR_region         Override region
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

# Validate environment
validate_environment() {
    local env=$1

    case "$env" in
        dev|staging|production)
            return 0
            ;;
        *)
            log_error "Invalid environment: $env"
            log_error "Valid environments: dev, staging, production"
            exit 1
            ;;
    esac
}

# Get environment-specific configuration
get_environment_config() {
    local env=$1

    case "$env" in
        dev)
            export TF_VAR_environment="development"
            export TF_VAR_log_level="DEBUG"
            export TF_VAR_project_id="fusion-prime-dev"
            ;;
        staging)
            export TF_VAR_environment="staging"
            export TF_VAR_log_level="INFO"
            export TF_VAR_project_id="fusion-prime-staging"
            ;;
        production)
            export TF_VAR_environment="production"
            export TF_VAR_log_level="WARNING"
            export TF_VAR_project_id="fusion-prime-prod"
            ;;
    esac

    log_info "Environment: $env"
    log_info "Project ID: $TF_VAR_project_id"
    log_info "Environment: $TF_VAR_environment"
    log_info "Log Level: $TF_VAR_log_level"
}

# Initialize Terraform
terraform_init() {
    local env=$1

    log_info "Initializing Terraform for $env environment..."

    cd "$TERRAFORM_DIR"

    # Initialize with environment-specific backend
    terraform init \
        -backend-config="bucket=fusion-prime-terraform-state" \
        -backend-config="prefix=$env" \
        -backend-config="project=$TF_VAR_project_id"

    log_success "Terraform initialized for $env environment"
}

# Plan infrastructure changes
terraform_plan() {
    local env=$1

    log_info "Planning infrastructure changes for $env environment..."

    cd "$TERRAFORM_DIR"

    # Plan with environment-specific variables
    terraform plan \
        -var-file="terraform.$env.tfvars" \
        -out="terraform.$env.tfplan"

    log_success "Infrastructure plan created for $env environment"
    log_info "Plan file: terraform.$env.tfplan"
}

# Apply infrastructure changes
terraform_apply() {
    local env=$1

    log_info "Applying infrastructure changes for $env environment..."

    cd "$TERRAFORM_DIR"

    # Apply with environment-specific variables
    terraform apply \
        -var-file="terraform.$env.tfvars" \
        -auto-approve

    log_success "Infrastructure applied for $env environment"
}

# Destroy infrastructure
terraform_destroy() {
    local env=$1

    log_warning "⚠️  DESTROYING INFRASTRUCTURE FOR $env ENVIRONMENT"
    log_warning "This will permanently delete all resources!"

    if [ "$env" = "production" ]; then
        log_error "Production environment destruction requires explicit confirmation"
        read -p "Type 'DESTROY PRODUCTION' to confirm: " confirm
        if [ "$confirm" != "DESTROY PRODUCTION" ]; then
            log_error "Production destruction cancelled"
            exit 1
        fi
    else
        read -p "Are you sure you want to destroy $env infrastructure? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "Destruction cancelled"
            exit 1
        fi
    fi

    log_info "Destroying infrastructure for $env environment..."

    cd "$TERRAFORM_DIR"

    # Destroy with environment-specific variables
    terraform destroy \
        -var-file="terraform.$env.tfvars" \
        -auto-approve

    log_success "Infrastructure destroyed for $env environment"
}

# Main execution
main() {
    local environment="${1:-}"
    local action="${2:-plan}"

    if [ -z "$environment" ]; then
        log_error "Environment is required"
        print_usage
        exit 1
    fi

    # Validate environment
    validate_environment "$environment"

    # Get environment configuration
    get_environment_config "$environment"

    # Change to terraform directory
    cd "$TERRAFORM_DIR"

    # Execute action
    case "$action" in
        init)
            terraform_init "$environment"
            ;;
        plan)
            terraform_plan "$environment"
            ;;
        apply)
            terraform_apply "$environment"
            ;;
        destroy)
            terraform_destroy "$environment"
            ;;
        *)
            log_error "Invalid action: $action"
            log_error "Valid actions: init, plan, apply, destroy"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
