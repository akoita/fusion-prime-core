#!/bin/bash
# Fusion Prime Test Runner - Main Entry Point
# Delegates to the organized test scripts

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Show help
show_help() {
    echo "Fusion Prime Test Runner"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  quick       Quick validation (~30 seconds) - LOCAL"
    echo "  local       Full local testing (~5 minutes) + reports - LOCAL"
    echo "  contracts   Smart contract testing (~2 minutes) - LOCAL"
    echo "  backend     Backend service testing (~3 minutes) - LOCAL"
    echo "  e2e         End-to-end testing (~5 minutes) + reports - LOCAL"
    echo ""
    echo "Remote Testing:"
    echo "  testnet     Testnet validation (~10 minutes) - REMOTE"
    echo "  production  Production health checks (~5 minutes) - REMOTE"
    echo "  integration-remote Cross-environment testing (~15 minutes) - REMOTE"
    echo ""
    echo "Health & Status:"
    echo "  health      Detailed health check (~30 seconds) - LOCAL"
    echo "  status      System status check (~10 seconds) - LOCAL"
    echo "  services    Show service status and instructions - LOCAL"
    echo "  help        Show this help message"
    echo ""
    echo "Options:"
    echo "  --reports     Generate HTML and JSON reports (for other commands)"
    echo "  --no-reports  Disable automatic report generation"
    echo "  --help, -h    Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 quick                    # Quick validation"
    echo "  $0 local --verbose          # Full local testing + reports with verbose output"
    echo "  $0 local --no-reports       # Full local testing without reports"
    echo "  $0 contracts --coverage     # Contract testing with coverage"
    echo "  $0 e2e                      # End-to-end testing + reports"
    echo ""
    echo "For more information, see TESTING.md"
}

# Parse command line arguments
GENERATE_REPORTS=false
NO_REPORTS=false
COMMAND=""
VERBOSE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --reports)
            GENERATE_REPORTS=true
            shift
            ;;
        --no-reports)
            NO_REPORTS=true
            shift
            ;;
        --verbose)
            VERBOSE="--verbose"
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

# Default to help if no command provided
if [ -z "$COMMAND" ]; then
    COMMAND="help"
fi

# Prepare arguments for sub-scripts
SCRIPT_ARGS="$VERBOSE"
if [ "$NO_REPORTS" = true ]; then
    SCRIPT_ARGS="$SCRIPT_ARGS --no-reports"
fi

# Execute the appropriate command
case "$COMMAND" in
    "quick"|"local"|"contracts"|"backend"|"e2e"|"health"|"status"|"services")
        exec "$SCRIPT_DIR/test/local.sh" $COMMAND $SCRIPT_ARGS
        ;;
    "testnet"|"production"|"integration-remote")
        exec "$SCRIPT_DIR/test/remote.sh" $COMMAND $SCRIPT_ARGS
        ;;
    "help"|"--help"|"-h")
        show_help
        exit 0
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo ""
        show_help
        exit 1
        ;;
esac
