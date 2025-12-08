#!/bin/bash
# Fusion Prime Setup Script - Main entry point for all setup tasks

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${PURPLE}========================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}========================================${NC}"
    echo ""
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

show_help() {
    echo "Fusion Prime Setup Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  all         Complete setup (bootstrap + env + services)"
    echo "  bootstrap   Initial project bootstrap"
    echo "  env         Environment configuration"
    echo "  services    Start required services"
    echo "  pubsub      Initialize Pub/Sub emulator"
    echo "  relayer     Setup local relayer"
    echo "  help        Show this help message"
    echo ""
    echo "Options:"
    echo "  --force     Force reconfiguration"
    echo "  --help, -h  Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 all                    # Complete setup"
    echo "  $0 env --force           # Reconfigure environments"
    echo "  $0 services              # Start services only"
}

# Parse arguments
COMMAND=""
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            if [ -z "$COMMAND" ]; then
                COMMAND="$1"
            fi
            shift
            ;;
    esac
done

# Default command
if [ -z "$COMMAND" ]; then
    COMMAND="all"
fi

# Execute based on command
case "$COMMAND" in
    "all")
        print_header "COMPLETE SETUP"
        print_info "Running complete Fusion Prime setup..."

        # Bootstrap
        print_step "1. Bootstrapping project..."
        "$SCRIPT_DIR/bootstrap.sh"

        # Environment
        print_step "2. Configuring environments..."
        "$SCRIPT_DIR/setup-env.sh" $([ "$FORCE" = true ] && echo "--force")

        # Services
        print_step "3. Starting services..."
        "$SCRIPT_DIR/setup-relayer.sh"

        print_success "Complete setup finished!"
        ;;

    "bootstrap")
        print_header "PROJECT BOOTSTRAP"
        "$SCRIPT_DIR/bootstrap.sh"
        ;;

    "env")
        print_header "ENVIRONMENT CONFIGURATION"
        "$SCRIPT_DIR/setup-env.sh" $([ "$FORCE" = true ] && echo "--force")
        ;;

    "services")
        print_header "SERVICE SETUP"
        "$SCRIPT_DIR/setup-relayer.sh"
        ;;

    "pubsub")
        print_header "PUB/SUB INITIALIZATION"
        "$SCRIPT_DIR/init-pubsub.sh"
        ;;

    "relayer")
        print_header "RELAYER SETUP"
        "$SCRIPT_DIR/setup-relayer.sh"
        ;;

    "help"|"--help"|"-h")
        show_help
        exit 0
        ;;

    *)
        print_error "Unknown command: $COMMAND"
        echo ""
        show_help
        exit 1
        ;;
esac
