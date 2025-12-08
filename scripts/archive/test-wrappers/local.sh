#!/bin/bash
# Local Test Runner - Handles all local testing scenarios

set -e

# Load common utilities
source "$(dirname "$0")/common.sh"

# Parse arguments
COMMAND=""
NO_REPORTS=false
VERBOSE=""
COVERAGE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-reports)
            NO_REPORTS=true
            shift
            ;;
        --verbose)
            VERBOSE="--verbose"
            shift
            ;;
        --coverage)
            COVERAGE="--coverage"
            shift
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
    COMMAND="local"
fi

# Prepare test arguments
TEST_ARGS="$VERBOSE $COVERAGE"
if [ "$NO_REPORTS" = true ]; then
    TEST_ARGS="$TEST_ARGS --no-reports"
fi

# Execute based on command
case "$COMMAND" in
    "quick")
        print_header "QUICK VALIDATION"
        print_info "Running quick validation (~30 seconds)..."
        check_services
        python tests/scripts/run_local_tests.py --category health $TEST_ARGS
        ;;

    "local")
        print_header "FULL LOCAL TESTING"
        print_info "Running comprehensive local tests (~5 minutes)..."
        check_services
        deploy_contracts
        python tests/scripts/run_local_tests.py $TEST_ARGS
        ;;

    "contracts")
        print_header "SMART CONTRACT TESTING"
        print_info "Running smart contract tests (~2 minutes)..."
        check_services
        deploy_contracts
        python tests/scripts/run_local_tests.py --category contracts $TEST_ARGS
        ;;

    "backend")
        print_header "BACKEND SERVICE TESTING"
        print_info "Running backend service tests (~3 minutes)..."
        check_services
        python tests/scripts/run_local_tests.py --category backend $TEST_ARGS
        ;;


    "e2e")
        print_header "END-TO-END TESTING"
        print_info "Running end-to-end tests (~5 minutes)..."
        check_services
        deploy_contracts
        python tests/scripts/run_local_tests.py --category e2e $TEST_ARGS
        ;;

    "health")
        print_header "HEALTH CHECK"
        print_info "Running detailed health check (~30 seconds)..."
        check_services
        python tests/scripts/run_local_tests.py --category health $TEST_ARGS
        ;;

    "status")
        print_header "SYSTEM STATUS"
        print_info "Checking system status (~10 seconds)..."
        check_services
        show_status
        ;;

    "services")
        print_header "SERVICE STATUS"
        show_services
        ;;

    *)
        print_error "Unknown local command: $COMMAND"
        echo "Available commands: quick, local, contracts, backend, e2e, health, status, services"
        exit 1
        ;;
esac

print_success "Local test command '$COMMAND' completed successfully"
