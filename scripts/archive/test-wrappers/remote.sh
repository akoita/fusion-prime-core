#!/bin/bash
# Remote Testing Script for Fusion Prime
# Run testnet validation tests locally

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Show usage
show_usage() {
    echo -e "${BLUE}🧪 Fusion Prime - Remote Testing Script${NC}"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  health          Quick health check (~5s)"
    echo "  integration     Service integration tests (~10s)"
    echo "  blockchain      Blockchain connectivity tests (~5s)"
    echo "  workflow        Complete workflow simulation (~15s)"
    echo "  metrics         System metrics collection (~5s)"
    echo "  all             Run all tests (~20s)"
    echo "  testnet         Same as 'all'"
    echo ""
    echo "Options:"
    echo "  -v, --verbose   Show detailed output"
    echo "  -s, --capture   Show print statements"
    echo "  --html          Generate HTML report"
    echo "  --help          Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 health                 # Quick health check"
    echo "  $0 integration -v         # Integration tests with verbose output"
    echo "  $0 all --html             # All tests with HTML report"
    echo ""
}

# Check if in correct directory
check_environment() {
    if [ ! -f "$PROJECT_ROOT/tests/remote/testnet/test_system_integration.py" ]; then
        echo -e "${RED}❌ Error: Cannot find test files${NC}"
        echo "Make sure you're running this from the project root or scripts directory"
        exit 1
    fi
}

# Check Python and dependencies
check_dependencies() {
    echo -e "${BLUE}🔍 Checking dependencies...${NC}"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 not found${NC}"
        echo "Install Python 3.11+ to run tests"
        exit 1
    fi

    # Check pytest
    if ! python3 -c "import pytest" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  pytest not found, installing dependencies...${NC}"
        pip install -r "$PROJECT_ROOT/tests/requirements.txt"
    fi

    echo -e "${GREEN}✅ Dependencies OK${NC}"
    echo ""
}

# Load environment variables
load_env() {
    if [ -f "$PROJECT_ROOT/.env.test" ]; then
        echo -e "${BLUE}📋 Loading environment from .env.test${NC}"
        # Use Python to safely parse the .env file
        python3 -c "
import os
with open('$PROJECT_ROOT/.env.test', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            if value.startswith('\"') and value.endswith('\"'):
                value = value[1:-1]
            elif value.startswith(\"'\") and value.endswith(\"'\"):
                value = value[1:-1]
            os.environ[key] = value
            print(f'export {key}=\"{value}\"')
" | while read line; do
            eval "$line"
        done
    else
        echo -e "${YELLOW}⚠️  No .env.test file found, using defaults${NC}"
    fi

    # Set default service URLs if not set
    export SETTLEMENT_SERVICE_URL=${SETTLEMENT_SERVICE_URL:-"https://settlement-service-961424092563.us-central1.run.app"}
    export RISK_ENGINE_SERVICE_URL=${RISK_ENGINE_SERVICE_URL:-"https://risk-engine-service-961424092563.us-central1.run.app"}
    export COMPLIANCE_SERVICE_URL=${COMPLIANCE_SERVICE_URL:-"https://compliance-service-961424092563.us-central1.run.app"}
    export RELAYER_SERVICE_URL=${RELAYER_SERVICE_URL:-"https://event-relayer-961424092563.us-central1.run.app"}

    echo -e "${GREEN}✅ Environment loaded${NC}"
    echo ""
}

# Run tests
run_tests() {
    local test_filter=$1
    local pytest_args=$2

    cd "$PROJECT_ROOT/tests/remote/testnet"

    echo -e "${BLUE}🧪 Running tests: $test_filter${NC}"
    echo ""

    if [ -n "$test_filter" ]; then
        python3 -m pytest test_system_integration.py -k "$test_filter" $pytest_args
    else
        python3 -m pytest test_system_integration.py $pytest_args
    fi

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✅ Tests passed!${NC}"
    else
        echo ""
        echo -e "${RED}❌ Tests failed!${NC}"
    fi

    return $exit_code
}

# Main script
main() {
    local command=${1:-"help"}
    shift || true

    # Parse options
    local pytest_args="-v --tb=short"

    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--verbose)
                pytest_args="$pytest_args -v"
                shift
                ;;
            -s|--capture)
                pytest_args="$pytest_args -s"
                shift
                ;;
            --html)
                pytest_args="$pytest_args --html=test-report.html --self-contained-html"
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                show_usage
                exit 1
                ;;
        esac
    done

    # Execute command
    case $command in
        health)
            check_environment
            check_dependencies
            load_env
            run_tests "health" "$pytest_args"
            ;;
        integration)
            check_environment
            check_dependencies
            load_env
            run_tests "service" "$pytest_args"
            ;;
        blockchain)
            check_environment
            check_dependencies
            load_env
            run_tests "blockchain" "$pytest_args"
            ;;
        workflow)
            check_environment
            check_dependencies
            load_env
            run_tests "workflow" "$pytest_args"
            ;;
        metrics)
            check_environment
            check_dependencies
            load_env
            run_tests "metrics" "$pytest_args"
            ;;
        all|testnet)
            check_environment
            check_dependencies
            load_env
            run_tests "" "$pytest_args"
            ;;
        help|--help|-h)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown command: $command${NC}"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run main
main "$@"
