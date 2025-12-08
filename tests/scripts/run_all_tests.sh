#!/bin/bash
"""
Helper script to run all Fusion Prime tests with automatic configuration.

Usage:
    python tests/scripts/run_all_tests.sh                    # Run all tests
    python tests/scripts/run_all_tests.sh -v                 # Run with verbose output
    python tests/scripts/run_all_tests.sh -s                 # Run with detailed output
    python tests/scripts/run_all_tests.sh --workflows        # Run only workflow tests
    python tests/scripts/run_all_tests.sh --services         # Run only service tests
    python tests/scripts/run_all_tests.sh --health           # Run only health tests
"""

set -e

# Change to project root directory
cd "$(dirname "$0")/../.."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default environment
ENVIRONMENT=${TEST_ENVIRONMENT:-local}

echo -e "${BLUE}🚀 Running Fusion Prime Tests${NC}"
echo "=================================="
echo -e "Environment: ${GREEN}$ENVIRONMENT${NC}"
echo ""

# Check if local environment is running
if [ "$ENVIRONMENT" = "local" ]; then
    echo -e "${BLUE}🔍 Checking local environment...${NC}"

    # Check if Docker containers are running
    if ! docker compose ps | grep -q "Up"; then
        echo -e "${YELLOW}⚠️  Local environment not running. Starting it now...${NC}"
        ./scripts/setup/start_local_testing.sh
        echo ""
    else
        echo -e "${GREEN}✅ Local environment is running${NC}"
        echo ""
    fi
fi

# Set environment variable
export TEST_ENVIRONMENT=$ENVIRONMENT

# Parse arguments
PYTEST_ARGS=()
CATEGORY=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --workflows)
            CATEGORY="workflows"
            shift
            ;;
        --services)
            CATEGORY="services"
            shift
            ;;
        --health)
            CATEGORY="health"
            shift
            ;;
        --connectivity)
            CATEGORY="connectivity"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --workflows     Run only workflow tests (E2E tests)"
            echo "  --services      Run only service tests"
            echo "  --health        Run only health check tests"
            echo "  --connectivity  Run only connectivity tests"
            echo "  -h, --help      Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Run all tests"
            echo "  $0 --workflows        # Run only workflow tests"
            echo "  $0 -v                 # Run all tests with verbose output"
            echo "  $0 --workflows -s     # Run workflow tests with detailed output"
            exit 0
            ;;
        *)
            PYTEST_ARGS+=("$1")
            shift
            ;;
    esac
done

# Set test path based on category
if [ "$CATEGORY" = "workflows" ]; then
    TEST_PATH="tests/test_*_workflow.py"
    echo -e "${BLUE}🎯 Running workflow tests (E2E tests)${NC}"
elif [ "$CATEGORY" = "services" ]; then
    TEST_PATH="tests/test_*_service*.py"
    echo -e "${BLUE}🎯 Running service tests${NC}"
elif [ "$CATEGORY" = "health" ]; then
    TEST_PATH="tests/test_*_health.py"
    echo -e "${BLUE}🎯 Running health tests${NC}"
elif [ "$CATEGORY" = "connectivity" ]; then
    TEST_PATH="tests/test_*_connectivity.py"
    echo -e "${BLUE}🎯 Running connectivity tests${NC}"
else
    TEST_PATH="tests/"
    echo -e "${BLUE}🎯 Running ALL tests${NC}"
fi

echo ""

# Run tests
echo -e "${BLUE}🧪 Starting test execution...${NC}"
echo ""

if [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
    # Default arguments
    pytest $TEST_PATH -v
else
    # Custom arguments
    pytest $TEST_PATH "${PYTEST_ARGS[@]}"
fi

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All tests passed!${NC}"
else
    echo ""
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi
