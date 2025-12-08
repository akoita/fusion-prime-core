#!/bin/bash
# Run Fusion Prime Tests Against Local Docker Compose Environment

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Fusion Prime - Local Test Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Load local environment configuration
if [ -f ".env.local" ]; then
    echo -e "${GREEN}✓${NC} Loading .env.local configuration"
    export $(cat .env.local | grep -v '^#' | xargs)
else
    echo -e "${YELLOW}⚠${NC}  .env.local not found, using defaults"
    export TEST_ENVIRONMENT=local
fi

# Check if Docker Compose services are running
echo -e "\n${BLUE}Checking Docker Compose services...${NC}"

if ! docker ps | grep -q "fusion-prime-anvil"; then
    echo -e "${RED}✗${NC} Anvil not running. Starting Docker Compose services..."
    docker-compose up -d
    echo -e "${GREEN}✓${NC} Waiting for services to be healthy (30s)..."
    sleep 30
else
    echo -e "${GREEN}✓${NC} Docker Compose services are running"
fi

# Check service health
echo -e "\n${BLUE}Checking service health...${NC}"

check_service() {
    local service_name=$1
    local url=$2

    if curl -sf "$url/health" > /dev/null 2>&1 || curl -sf "$url/health/" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $service_name is healthy"
        return 0
    else
        echo -e "${YELLOW}⚠${NC}  $service_name is not responding at $url"
        return 1
    fi
}

check_service "Settlement Service" "http://localhost:8000"
check_service "Risk Engine" "http://localhost:8001" || true
check_service "Compliance Service" "http://localhost:8002" || true

# Check Anvil
if curl -sf http://localhost:8545 -X POST -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Anvil blockchain is running"
else
    echo -e "${RED}✗${NC} Anvil blockchain is not responding"
    exit 1
fi

# Deploy contracts if not already deployed
if [ -z "$ESCROW_FACTORY_ADDRESS" ]; then
    echo -e "\n${BLUE}Deploying smart contracts...${NC}"
    cd contracts
    if [ -f "script/Deploy.s.sol" ]; then
        forge script script/Deploy.s.sol:DeployScript --rpc-url http://localhost:8545 --broadcast --unlocked || true
        echo -e "${YELLOW}⚠${NC}  Set ESCROW_FACTORY_ADDRESS in .env.local after deployment"
    fi
    cd ..
fi

# Run tests
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Running Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Parse command line arguments
TEST_PATH=${1:-"tests/"}
PYTEST_ARGS=${2:-"-v"}

# Run pytest
python -m pytest "$TEST_PATH" $PYTEST_ARGS \
    --tb=short \
    --color=yes \
    -W ignore::DeprecationWarning

TEST_EXIT_CODE=$?

# Summary
echo ""
echo -e "${BLUE}========================================${NC}"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
fi
echo -e "${BLUE}========================================${NC}"

exit $TEST_EXIT_CODE
