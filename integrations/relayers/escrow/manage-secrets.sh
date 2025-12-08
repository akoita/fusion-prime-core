#!/bin/bash

# Secret Manager helper script for relayer service
#
# Usage:
#   ./manage-secrets.sh create <secret-name> <config-file>
#   ./manage-secrets.sh update <secret-name> <config-file>
#   ./manage-secrets.sh show <secret-name>

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to create a secret
create_secret() {
    local secret_name=$1
    local config_file=$2

    if [ ! -f "$config_file" ]; then
        print_error "Configuration file not found: $config_file"
        exit 1
    fi

    print_status "Creating secret: $secret_name"
    print_status "Configuration file: $config_file"

    # Create the secret
    gcloud secrets create "$secret_name" \
        --data-file="$config_file" \
        --replication-policy="automatic"

    print_status "Secret created successfully!"

    # Grant Cloud Build access
    local project_number=$(gcloud projects describe fusion-prime --format='value(projectNumber)')
    gcloud secrets add-iam-policy-binding "$secret_name" \
        --member="serviceAccount:${project_number}@cloudbuild.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor"

    print_status "Cloud Build access granted!"
}

# Function to update a secret
update_secret() {
    local secret_name=$1
    local config_file=$2

    if [ ! -f "$config_file" ]; then
        print_error "Configuration file not found: $config_file"
        exit 1
    fi

    print_status "Updating secret: $secret_name"
    print_status "Configuration file: $config_file"

    # Add new version to the secret
    gcloud secrets versions add "$secret_name" \
        --data-file="$config_file"

    print_status "Secret updated successfully!"
}

# Function to show secret content
show_secret() {
    local secret_name=$1

    print_status "Showing secret: $secret_name"

    # Get the latest version
    gcloud secrets versions access latest --secret="$secret_name" | jq .
}

# Main script logic
case "$1" in
    create)
        if [ $# -ne 3 ]; then
            print_error "Usage: $0 create <secret-name> <config-file>"
            exit 1
        fi
        create_secret "$2" "$3"
        ;;
    update)
        if [ $# -ne 3 ]; then
            print_error "Usage: $0 update <secret-name> <config-file>"
            exit 1
        fi
        update_secret "$2" "$3"
        ;;
    show)
        if [ $# -ne 2 ]; then
            print_error "Usage: $0 show <secret-name>"
            exit 1
        fi
        show_secret "$2"
        ;;
    *)
        echo "Usage: $0 {create|update|show} <secret-name> [config-file]"
        echo ""
        echo "Commands:"
        echo "  create  - Create a new secret from a configuration file"
        echo "  update  - Update an existing secret with new configuration"
        echo "  show    - Display the current secret content"
        echo ""
        echo "Examples:"
        echo "  $0 create relayer-service-config-test config-test.json"
        echo "  $0 update relayer-service-config-test config-test.json"
        echo "  $0 show relayer-service-config-test"
        exit 1
        ;;
esac
