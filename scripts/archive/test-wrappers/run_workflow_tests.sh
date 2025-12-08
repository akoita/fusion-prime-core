#!/bin/bash
# Run Workflow Tests Locally with Proper Environment Configuration

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Fusion Prime - Workflow Test Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Load environment from .env.local
if [ -f ".env.local" ]; then
    echo -e "${GREEN}✓${NC} Loading .env.local configuration"
    export $(cat .env.local | grep -v '^#' | xargs)
else
    echo -e "${RED}✗${NC} .env.local not found"
    exit 1
fi

# Verify critical variables
if [ -z "$ESCROW_FACTORY_ADDRESS" ]; then
    echo -e "${RED}✗${NC} ESCROW_FACTORY_ADDRESS not set in .env.local"
    echo -e "${YELLOW}ℹ${NC}  Deploy contracts first: cd contracts && forge script script/DeployMultichain.s.sol:DeployMultichain --rpc-url http://localhost:8545 --broadcast"
    exit 1
fi

if [ -z "$ESCROW_FACTORY_ABI_PATH" ]; then
    echo -e "${RED}✗${NC} ESCROW_FACTORY_ABI_PATH not set in .env.local"
    exit 1
fi

echo -e "${GREEN}✓${NC} Environment configured"
echo -e "  TEST_ENVIRONMENT: ${TEST_ENVIRONMENT}"
echo -e "  ETH_RPC_URL: ${ETH_RPC_URL}"
echo -e "  ESCROW_FACTORY_ADDRESS: ${ESCROW_FACTORY_ADDRESS}"
echo ""

# Check Docker Compose services
echo -e "${BLUE}Checking Docker Compose services...${NC}"
if ! docker compose ps | grep -q "fusion-prime-anvil.*Up.*healthy"; then
    echo -e "${YELLOW}⚠${NC}  Anvil not healthy. Starting services..."
    docker compose up -d
    sleep 20
fi

# Run tests
TEST_PATTERN=${1:-"tests/test_*_workflow.py"}
PYTEST_ARGS=${2:-"-v"}

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Running Workflow Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Use glob expansion for the test pattern
pytest $TEST_PATTERN $PYTEST_ARGS --tb=short

TEST_EXIT_CODE=$?

echo ""
echo -e "${BLUE}========================================${NC}"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
fi
echo -e "${BLUE}========================================${NC}"

exit $TEST_EXIT_CODE
