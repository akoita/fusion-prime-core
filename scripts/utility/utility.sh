#!/bin/bash
# Fusion Prime Utility Script - Main entry point for utility tasks

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
    echo "Fusion Prime Utility Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  build       Build project components"
    echo "  cleanup     Clean up local resources"
    echo "  verify      Verify deployment"
    echo "  reports     View test reports"
    echo "  help        Show this help message"
    echo ""
    echo "Options:"
    echo "  --force     Force operation"
    echo "  --help, -h  Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 build                    # Build project"
    echo "  $0 cleanup --force         # Force cleanup"
    echo "  $0 verify                  # Verify deployment"
    echo "  $0 reports                 # View reports"
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
    COMMAND="help"
fi

# Execute based on command
case "$COMMAND" in
    "build")
        print_header "BUILD PROJECT"
        "$SCRIPT_DIR/build.sh" $([ "$FORCE" = true ] && echo "--force")
        ;;

    "cleanup")
        print_header "CLEANUP RESOURCES"
        "$SCRIPT_DIR/cleanup.sh" $([ "$FORCE" = true ] && echo "--force")
        ;;

    "verify")
        print_header "VERIFY DEPLOYMENT"
        "$SCRIPT_DIR/verify.sh"
        ;;

    "reports")
        print_header "VIEW REPORTS"
        "$SCRIPT_DIR/reports.sh"
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
